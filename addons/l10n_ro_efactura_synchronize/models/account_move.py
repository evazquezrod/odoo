import base64
import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


HOLDING_DAYS = 3  # Arbitrary


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ro_edi_state = fields.Selection(
        selection_add=[
            ('invoice_not_indexed', "Not indexed"),
        ],
        ondelete={
            'invoice_not_indexed': 'set invoice_sending',
        },
    )

    @api.depends('l10n_ro_edi_state')
    def _compute_show_reset_to_draft_button(self):
        """ Prevent user to reset move to draft when there's an
            active sending document or a successful response has been received """
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_ro_edi_state in ('invoice_sending', 'invoice_not_indexed', 'invoice_sent'):
                move.show_reset_to_draft_button = False

    @api.model
    def _l10n_ro_edi_fetch_invoices(self):
        """ Synchronize bills/invoices from SPV """
        result = self.env['l10n_ro_edi.document']._request_ciusro_synchronize_invoices(
            company=self.env.company,
            session=requests.Session(),
        )
        if 'error' in result:
            raise UserError(result['error'])

        if result['sent_invoices_accepted_messages']:
            self._l10n_ro_edi_process_invoice_accepted_messages(result['sent_invoices_accepted_messages'])

        if result['sent_invoices_refused_messages']:
            self._l10n_ro_edi_process_invoice_refused_messages(result['sent_invoices_refused_messages'])

        if result['received_bills_messages']:
            self._l10n_ro_edi_process_bill_messages(result['received_bills_messages'])

        # Non-indexed moves that were not processed after some time have probably been refused by the SPV. Since
        # there is no way to recover the index for refused invoices, we simply refuse them manually without proper reason.
        domain = (
            Domain('company_id', '=', self.env.company.id)
            & Domain('l10n_ro_edi_index', '=', False)
            & Domain('l10n_ro_edi_state', '=', 'invoice_not_indexed')
        )
        non_indexed_invoices = self.env['account.move'].search(domain)

        document_ids_to_delete = []
        for invoice in non_indexed_invoices:
            # At that point, only one sent document should exists on an invoice
            sent_document = invoice.l10n_ro_edi_document_ids

            if (fields.Datetime.today() - sent_document.create_date).days > HOLDING_DAYS:
                document_ids_to_delete += invoice.l10n_ro_edi_document_ids.ids

                error_message = _(
                    "The invoice has probably been refused by the SPV. We were unable to recover the reason of the refusal because "
                    "the invoice had not received its index. Duplicate the invoice and attempt to send it again."
                )
                invoice._l10n_ro_edi_create_document_invoice_sending_failed(message=error_message)

        self.env['l10n_ro_edi.document'].sudo().browse(document_ids_to_delete).unlink()

        if self._can_commit():
            self._cr.commit()

    @api.model
    def _l10n_ro_edi_process_invoice_accepted_messages(self, sent_invoices_accepted_messages):
        ''' Process the validation messages of invoices sent
            It will also attempt to recover the original invoices, that are missing their index,
            by matching the name returned by the server and the one in the database.
            note: There is an edge case where 2 messages have the same invoice name but different indexes in
            their data; this could be due to a resequencing of the invoice and/or re-sending of an invoice. In
            that case coupled with name matching where none of the two invoices received an index, all signatures
            are added to the invoice; the user will have to manually update/select the correct one.
            For example: 2 invoices in the database
                - 11 already sent and should have gotten index AA, but did not receive it
                - 12 not sent
            Resequence them: 11->12 and 12->11
            Send new 11 that has not yet been sent, it should have gotten index AB but did not receive it.
            => In the messages, 2 invoices with name 11 and both index AA and AB.
        '''
        invoice_names = {message['answer']['invoice']['name'] for message in sent_invoices_accepted_messages if 'error' not in message}
        invoice_indexes = [message['id_solicitare'] for message in sent_invoices_accepted_messages]
        domain = (
            Domain('company_id', '=', self.env.company.id)
            & Domain('move_type', 'in', self.get_sale_types())
            & (
                (
                    Domain('l10n_ro_edi_index', 'in', invoice_indexes)
                    & Domain('l10n_ro_edi_state', '=', 'invoice_sending')
                )
                | (
                    Domain('name', 'in', list(invoice_names))
                    & Domain('l10n_ro_edi_index', '=', False)
                    & Domain('l10n_ro_edi_state', '=', 'invoice_not_indexed')
                )
            )
        )
        invoices = self.env['account.move'].search(domain)

        document_ids_to_delete = []
        index_to_move = {move.l10n_ro_edi_index: move for move in invoices}
        name_to_move = {move.name: move for move in invoices}
        for message in sent_invoices_accepted_messages:
            invoice = index_to_move.get(message['id_solicitare'])

            if not invoice:
                # The move related to the message does not have an index
                if 'error' in message or not name_to_move.get(message['answer']['invoice']['name']):
                    continue

                # An invoice with the same name has been found
                invoice = name_to_move.get(message['answer']['invoice']['name'])

                # Update the index of invoices succesfully sent but without SPV indexes due to server
                # time-out for unknown reasons during the upload
                invoice.l10n_ro_edi_index = message['id_solicitare']
                invoice.l10n_ro_edi_state = 'invoice_sending'

            if 'error' in message:
                document_ids_to_delete += invoice.invoice._l10n_ro_edi_get_sending_and_failed_documents().ids
                error_message = _(
                    "Error when trying to download the E-Factura data from the SPV: %s",
                    message['error']
                )
                invoice._l10n_ro_edi_create_document_invoice_sending_failed(error_message)
                continue

            # Only delete invoice_sent documents and not all because one invoice can contain several signature due to
            # the edge case where 2 messages have the same invoice name but different indexes in their data; this could
            # be due to a resequencing of the invoice and/or re-sending of an invoice. In that case coupled with name
            # matching where none of the two invoices received an index, all signatures are added to the invoice; the
            # user will have to manually update/select the correct one.
            document_ids_to_delete += invoice.invoice._l10n_ro_edi_get_sending_and_failed_documents().ids

            invoice.message_post(body=_("This invoice has been accepted by the SPV."))
            invoice._l10n_ro_edi_create_document_invoice_sent({
                'key_loading': message['id'],
                'key_signature': message['answer']['signature']['key_signature'],
                'key_certificate': message['answer']['signature']['key_certificate'],
                'attachment_raw': message['answer']['signature']['attachment_raw'],
            })

        self.env['l10n_ro_edi.document'].sudo().browse(document_ids_to_delete).unlink()

    @api.model
    def _l10n_ro_edi_process_invoice_refused_messages(self, sent_invoices_refused_messages):
        ''' Process the refusal messages of invoices sent
            For refused invoices, it is impossible to recover the original invoice from the message content like
            in `_l10n_ro_edi_process_invoice_accepted_messages` since the message only contains the index and
            error message (as relevant information).
        '''
        refused_invoice_indexes = [message['id_solicitare'] for message in sent_invoices_refused_messages]
        domain = (
            Domain('company_id', '=', self.env.company.id)
            & Domain('move_type', 'in', self.get_sale_types())
            & Domain('l10n_ro_edi_index', 'in', refused_invoice_indexes)
            & Domain('l10n_ro_edi_state', '=', 'invoice_sending')
        )
        invoices = self.env['account.move'].search(domain)
        index_to_move = {move.l10n_ro_edi_index: move for move in invoices}

        document_ids_to_delete = []
        for message in sent_invoices_refused_messages:
            invoice = index_to_move.get(message['id_solicitare'])
            if not invoice:
                continue

            if 'error' in message:
                document_ids_to_delete += invoice.invoice._l10n_ro_edi_get_sending_and_failed_documents().ids
                error_message = _(
                    "Error when trying to download the E-Factura data from the SPV: %s",
                    message['error']
                )
                invoice._l10n_ro_edi_create_document_invoice_sending_failed(error_message)
                continue

            document_ids_to_delete += invoice.l10n_ro_edi_document_ids.ids

            error_message = message['answer']['invoice']['error'].replace('\t', '')
            invoice._l10n_ro_edi_create_document_invoice_sending_failed(error_message)

        self.env['l10n_ro_edi.document'].sudo().browse(document_ids_to_delete).unlink()

    @api.model
    def _l10n_ro_edi_process_bill_messages(self, received_bills_messages):
        ''' Create bill received on the SPV, it it does not already exists.
        '''
        # Search potential similar bills: similar bills either:
        # - have an index that is present in the message data or,
        # - the same amount and seller VAT, and optionally the same bill date
        domain = (
            Domain('company_id', '=', self.env.company.id)
            & Domain('move_type', 'in', self.get_purchase_types())
            & (
                (
                    Domain('l10n_ro_edi_index', '=', False)
                    & Domain('l10n_ro_edi_state', '=', False)
                    & Domain.OR([
                        Domain('amount_total', '=', message['answer']['invoice']['amount_total'])
                        & Domain('commercial_partner_id.vat', '=', message['answer']['invoice']['seller_vat'])
                        & Domain('invoice_date', 'in', [message['answer']['invoice']['date'], False])
                        for message in received_bills_messages
                        if 'error' not in message
                    ])
                )
                | (
                    Domain('l10n_ro_edi_index', 'in', [message['id_solicitare'] for message in received_bills_messages])
                    & Domain('l10n_ro_edi_state', '=', 'invoice_validated')
                )
            )
        )
        similar_bills = self.env['account.move'].search(domain)

        indexed_similar_bills = similar_bills.filtered('l10n_ro_edi_index').mapped('l10n_ro_edi_index')
        non_indexed_similar_bills_dict = {
            (bill.commercial_partner_id.vat, bill.amount_total, bill.invoice_date): bill
            for bill in similar_bills
            if not bill.l10n_ro_edi_index
        }

        for message in received_bills_messages:
            if 'error' in message:
                continue

            if message['id_solicitare'] in indexed_similar_bills:
                # A bill with the same SPV index was already imported, skip it as we don't want it twice.
                continue

            # Create new bills if they don't already exist, else update their content
            bill = non_indexed_similar_bills_dict.get(
                (message['answer']['invoice']['seller_vat'], float(message['answer']['invoice']['amount_total']), message['answer']['invoice']['date'])
            )
            if not bill:
                bill = non_indexed_similar_bills_dict.get(
                (message['answer']['invoice']['seller_vat'], float(message['answer']['invoice']['amount_total']), False)
            )
            if not bill:
                bill = self.env['account.move'].create({
                'company_id': self.env.company.id,
                'move_type': 'in_invoice',
                'journal_id': self.env.company.l10n_ro_edi_anaf_imported_inv_journal_id.id,
            })

            bill.l10n_ro_edi_index = message['id_solicitare']

            self.env['l10n_ro_edi.document'].sudo().create({
                'invoice_id': bill.id,
                'state': 'invoice_validated',
                'key_download': message['id'],
                'key_signature': message['answer']['signature']['key_signature'],
                'key_certificate': message['answer']['signature']['key_certificate'],
                'attachment': base64.b64encode(message['answer']['signature']['attachment_raw']),
            })
            xml_attachment_id = self.env['ir.attachment'].sudo().create({
                'name': f"ciusro_{message['answer']['invoice']['name'].replace('/', '_')}.xml",
                'raw': message['answer']['invoice']['attachment_raw'],
                'res_model': 'account.move',
                'res_id': bill.id,
            }).id
            files_data = self._to_files_data(self.env['ir.attachment'].browse(xml_attachment_id))
            bill._extend_with_attachments(files_data)
            bill.message_post(body=_("Synchronized with SPV from message %s", message['id']))

    def action_l10n_ro_edi_fetch_invoices(self):
        self._l10n_ro_edi_fetch_invoices()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

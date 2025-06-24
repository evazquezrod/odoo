import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.l10n_ro_edi.tests.common import (
    TestUBLRO,
)
from odoo.addons.l10n_ro_efactura_synchronize.models.account_move import HOLDING_DAYS


def _patch_request_ciusro_download_answer(company, key_download, session):
    answer_data = {
        '3029027561': {
            'signature': {
                'attachment_raw': b'Y291Y291',
                'key_signature': 'KEY_SIG_1',
                'key_certificate': 'KEY_CERT_1',
            },
            'invoice': {
                'name': 'INV/2017/00001',
            },
        },
        '3029027562': {
            'signature': {
                'attachment_raw': b'Y291Y291',
                'key_signature': 'KEY_SIG_2',
                'key_certificate': 'KEY_CERT_2',
            },
            'invoice': {
                'name': 'INV/2017/00002',
            },
        },
        '3030159318': {
            'signature': {
                'attachment_raw': b'Y291Y291',
                'key_signature': 'KEY_SIG_3',
                'key_certificate': 'KEY_CERT_3',
            },
            'invoice': {
                'error': 'There has been an error',
            },
        },
        '3030439533': {
            'signature': {
                'attachment_raw': b'Y291Y291',
                'key_signature': 'KEY_SIG_4',
                'key_certificate': 'KEY_CERT_4',
            },
            'invoice': {
                'name': 'INV/2025/00006',
                'amount_total': '1785.0',
                'seller_vat': '8001011234567',
                'date': datetime.date(2017, 1, 1),
                'attachment_raw': file_open("l10n_ro_edi/tests/test_files/from_odoo/ciusro_in_invoice.xml").read(),
            },
        },
    }
    return answer_data.get(key_download, {})


def _patch_request_ciusro_synchronize_invoices(company, session, nb_days=1):
    sent_invoices_accepted_messages = [
        {
            'data_creare': '202503271639',
            'cif': company.vat,
            'id_solicitare': '5019882651',
            'detalii': f"Factura cu id_incarcare=5019882651 emisa de cif_emitent={company.vat} pentru cif_beneficiar=RO1234567897",
            'tip': 'FACTURA TRIMISA',
            'id': '3029027561',
            'answer': _patch_request_ciusro_download_answer(company, '3029027561', None),
        },
        {
            'data_creare': '202503271639',
            'cif': company.vat,
            'id_solicitare': '5019882652',
            'detalii': f"Factura cu id_incarcare=5019882652 emisa de cif_emitent={company.vat} pentru cif_beneficiar=RO1234567897",
            'tip': 'FACTURA TRIMISA',
            'id': '3029027562',
            'answer': _patch_request_ciusro_download_answer(company, '3029027562', None),
        },
        {
            'data_creare': '202503271639',
            'cif': company.vat,
            'id_solicitare': '5019882653',
            'detalii': f"Factura cu id_incarcare=5019882653 emisa de cif_emitent={company.vat} pentru cif_beneficiar=RO1234567897",
            'tip': 'FACTURA TRIMISA',
            'id': '3029027562',
            'answer': _patch_request_ciusro_download_answer(company, '3029027562', None),
        },
    ]
    sent_invoices_refused_messages = [
        {
            'data_creare': '202504081504',
            'cif': company.vat,
            'id_solicitare': '5020592384',
            'detalii': 'Erori de validare identificate la factura transmisa cu id_incarcare=5020592384',
            'tip': 'ERORI FACTURA',
            'id': '3030159318',
            'answer': _patch_request_ciusro_download_answer(company, '3030159318', None),
        },
    ]
    received_bills_messages = [
        {
            'data_creare': '202504011105',
            'cif': company.vat,
            'id_solicitare': '5020704741',
            'detalii': f"Factura cu id_incarcare=5020704741 emisa de cif_emitent={company.vat} pentru cif_beneficiar=RO1234567897",
            'tip': 'FACTURA PRIMITA',
            'id': '3030439533',
            'answer': _patch_request_ciusro_download_answer(company, '3030439533', None),
        }
    ]
    return {
        'sent_invoices_accepted_messages': sent_invoices_accepted_messages,
        'sent_invoices_refused_messages': sent_invoices_refused_messages,
        'received_bills_messages': received_bills_messages,
    }


@patch('odoo.addons.l10n_ro_efactura_synchronize.models.account_move._request_ciusro_synchronize_invoices', new=_patch_request_ciusro_synchronize_invoices)
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLROSynchronize(TestUBLRO):
    def test_ciusro_synchronize_invoices_bill_found(self):
        """ Tests that if a bill with the same index is found, do nothing.
        """
        bill = self.create_move('in_invoice', send=False, l10n_ro_edi_index='5020704741', l10n_ro_edi_state='invoice_validated')

        document_count = len(bill.l10n_ro_edi_document_ids)
        message_count = len(bill.message_ids)

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        self.assertEqual(len(bill.l10n_ro_edi_document_ids), document_count)
        self.assertEqual(len(bill.message_ids), message_count)

    def test_ciusro_synchronize_invoices_bill_update_index(self):
        """ Tests that if a bill with the same partner VAT, amount match and date is found,
            we update the index and validate the invoice.
        """
        # Need a bill without index and for which the partner VAT and amount match the data returned
        bill = self.create_move('in_invoice', send=False)
        self.partner_a.vat = '8001011234567'

        self.assertEqual(bill.l10n_ro_edi_index, False)
        self.assertEqual(bill.l10n_ro_edi_state, False)

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        self.assertEqual(bill.l10n_ro_edi_index, '5020704741')
        self.assertEqual(bill.l10n_ro_edi_state, 'invoice_validated')

    def test_ciusro_synchronize_invoices_bill_creation(self):
        """ Tests that if no similar bills are found, we create one and fill it up with the XML content.
        """
        bills = self.env['account.move'].search([
            ('move_type', 'in', self.env['account.move'].get_purchase_types()),
            ('company_id', '=', self.env.company.id),
        ])
        self.assertEqual(len(bills), 0)

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        bills = self.env['account.move'].search([
            ('move_type', 'in', self.env['account.move'].get_purchase_types()),
            ('company_id', '=', self.env.company.id),
        ])
        self.assertEqual(len(bills), 1)
        self.assertEqual(bills.state, 'draft')
        self.assertEqual(bills.amount_total, 1785.0)
        self.assertEqual(bills.commercial_partner_id.vat, '8001011234567')
        self.assertEqual(bills.l10n_ro_edi_index, '5020704741')
        self.assertEqual(bills.l10n_ro_edi_state, 'invoice_validated')

    ####################################################
    # Testing of the invoice synchronization with SPV
    ####################################################

    def test_ciusro_synchronize_invoices_validation(self):
        ''' Test that a sent invoice status is validated.
        '''
        # Create an invoice that will match the success response returned by the server
        invoice = self.create_move('out_invoice', l10n_ro_edi_index='5019882651', send=False)
        self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sent',
        })
        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_sent')

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_validated')
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)

    def test_ciusro_synchronize_invoices_validation_without_index(self):
        ''' Test that a sent invoice status is validated although the invoice did not receive its index.
            The name of the invoice needs to match the name returned by SPV for the matching to work as intended.
        '''
        invoice = self.create_move('out_invoice', l10n_ro_edi_index='5019882651', send=False)
        self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sent',
        })
        invoice.name = 'INV/2017/00001'
        # Reset the invoice and remove its index to trigger the matching by name to the success response
        invoice.l10n_ro_edi_index = False
        invoice.l10n_ro_edi_state = 'invoice_not_indexed'

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        self.assertEqual(invoice.l10n_ro_edi_index, '5019882651')
        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_validated')
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)

    def test_ciusro_synchronize_invoices_index_not_in_messages(self):
        ''' Test that a sent invoice status not present in the messages returned by SPV is not updated.
        '''
        invoice = self.create_move('out_invoice', l10n_ro_edi_index='INDEX', send=False)
        self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sent',
        })
        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_sent')

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_sent')

    def test_ciusro_synchronize_invoices_refusal(self):
        ''' Test that a sent invoice status is refused.
        '''
        # Create an invoice to match the failure response returned by the server
        invoice = self.create_move('out_invoice', l10n_ro_edi_index='5020592384', send=False)
        self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sent',
        })
        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_sent')

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_refused')
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)

    def test_ciusro_synchronize_invoices_refusal_held_non_indexed(self):
        ''' Test that non-indexed invoices that have been held for too long get refused.
        '''
        invoice = self.create_move('out_invoice', send=False)
        self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sent',
        })
        invoice.name = 'INV/2017/00003'  # Skip 00001 and 00002 to avoid the validation due to similar invoice name
        invoice.l10n_ro_edi_state = 'invoice_not_indexed'

        self.assertEqual(invoice.l10n_ro_edi_index, False)

        with freeze_time(invoice.create_date + relativedelta(days=HOLDING_DAYS + 1)):
            self.env['account.move']._l10n_ro_edi_fetch_invoices()
        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_not_indexed')

        with freeze_time(invoice.create_date + relativedelta(days=HOLDING_DAYS + 2)):
            self.env['account.move']._l10n_ro_edi_fetch_invoices()
        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_refused')
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)

    def test_ciusro_synchronize_invoices_not_indexed_with_duplicate_name(self):
        """ Test the edge case where 2 messages have the same invoice name but different indexes in
            their data. This scenario coupled with name matching where none of the two invoices received an index,
            we want all signatures added to the named invoices.
        """
        invoice = self.create_move('out_invoice', send=False)
        invoice.name = 'INV/2017/00002'
        self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sent',
        })
        invoice.l10n_ro_edi_state = 'invoice_not_indexed'

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_validated')
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 2)

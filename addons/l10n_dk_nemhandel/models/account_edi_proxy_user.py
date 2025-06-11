import logging

from odoo import api, fields, models, modules, tools, _
from odoo.exceptions import UserError
from odoo.tools import split_every

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.l10n_dk_nemhandel.tools.demo_utils import handle_demo

_logger = logging.getLogger(__name__)
BATCH_SIZE = 50


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    nemhandel_verification_code = fields.Char(string='Nemhandel SMS verification code')
    proxy_type = fields.Selection(selection_add=[('nemhandel', 'Nemhandel')], ondelete={'nemhandel': 'cascade'})

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        urls['nemhandel'] = {
            'prod': 'http://127.0.0.1:8079',
            'test': 'http://127.0.0.1:8079',
            'demo': 'demo',
        }
        return urls

    def _call_nemhandel_proxy(self, endpoint, params=None):
        self.ensure_one()
        if self.proxy_type != 'nemhandel':
            raise UserError(_('EDI user should be of type Nemhandel'))

        errors = {
            'code_incorrect': _('The verification code is not correct'),
            'code_expired': _('This verification code has expired. Please request a new one.'),
            'too_many_attempts': _('Too many attempts to request an SMS code. Please try again later.'),
        }

        params = params or {}
        try:
            response = self._make_request(
                f"{self._get_server_url()}{endpoint}",
                params=params,
            )
        except AccountEdiProxyError as e:
            if (
                e.code == 'no_such_user'
                and not self.active
                and not self.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'nemhandel')
            ):
                self.company_id.l10n_dk_nemhandel_proxy_state = 'not_registered'

                # commit the above changes before raising below
                if not tools.config['test_enable'] and not modules.module.current_test:
                    self.env.cr.commit()
                raise UserError(_('We could not find a user with this information on our server. Please check your information.'))
            raise UserError(e.message)

        if 'error' in response:
            error_code = response['error'].get('code')
            error_message = response['error'].get('subject') or response['error'].get('data', {}).get('message')
            raise UserError(errors.get(error_code) or error_message or _('Connection error, please try again later.'))
        return response

    @handle_demo
    def _check_company_on_nemhandel(self, company, edi_identification):
        if (
            (participant_info := company.partner_id._get_nemhandel_participant_info(edi_identification)) is not None
            and company.partner_id._check_nemhandel_participant_exists(participant_info, edi_identification)
        ):
            error_msg = _(
                "A participant with these details has already been registered on the network. "
                "If you have previously registered to an alternative Nemhandel service, please deregister"
            )

            if isinstance(participant_info, str):
                error_msg += _("The Nemhandel service that is used is likely to be %s.", participant_info)
            raise UserError(error_msg)

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_nemhandel_get_new_documents(self):
        edi_users = self.search([('proxy_type', '=', 'nemhandel'), ('company_id.l10n_dk_nemhandel_proxy_state', '=', 'receiver')])
        edi_users._nemhandel_get_new_documents()

    def _cron_nemhandel_get_message_status(self):
        edi_users = self.search([('proxy_type', '=', 'nemhandel'), ('company_id.l10n_dk_nemhandel_proxy_state', '=', 'receiver')])
        edi_users._nemhandel_get_message_status()

    def _cron_nemhandel_webhook_keepalive(self):
        edi_users = self.search([('proxy_type', '=', 'nemhandel'), ('company_id.l10n_dk_nemhandel_proxy_state', 'in', ['receiver'])])
        edi_users._nemhandel_reset_webhook()

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _get_proxy_identification(self, company, proxy_type):
        if proxy_type != 'nemhandel':
            return super()._get_proxy_identification(company, proxy_type)
        if not company.nemhandel_identifier_type or not company.nemhandel_identifier_value:
            raise UserError(_("Please fill in the Identifier Type and Value."))
        return f'{company.nemhandel_identifier_type}:{company.nemhandel_identifier_value}'

    def _nemhandel_import_invoice(self, attachment, nemhandel_state, uuid):
        """Save new documents in an accounting journal, when one is specified on the company.

        :param attachment: the new document
        :param nemhandel_state: the state of the received Nemhandel document
        :param uuid: the UUID of the Nemhandel document
        :return: `True` if the document was saved, `False` if it was not
        """
        self.ensure_one()
        journal = self.company_id.nemhandel_purchase_journal_id
        if not journal:
            return False

        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'move_type': 'in_invoice',
            'nemhandel_move_state': nemhandel_state,
            'nemhandel_message_uuid': uuid,
        })
        if 'is_in_extractable_state' in move._fields:
            move.is_in_extractable_state = False

        move._extend_with_attachments(attachment, new=True)
        move._message_log(
            body=_(
                "Nemhandel document (UUID: %(uuid)s) has been received successfully.",
                uuid=uuid,
            ),
            attachment_ids=attachment.ids,
        )
        attachment.write({'res_model': 'account.move', 'res_id': move.id})
        return True

    def _nemhandel_get_new_documents(self):
        params = {
            'domain': {
                'direction': 'incoming',
                'errors': False,
            }
        }
        for edi_user in self:
            params['domain']['receiver_identifier'] = edi_user.edi_identification
            try:
                # request all messages that haven't been acknowledged
                messages = edi_user._call_nemhandel_proxy(
                    "/api/nemhandel/1/get_all_documents",
                    params=params,
                )
            except AccountEdiProxyError as e:
                _logger.error(
                    'Error while receiving the document from Nemhandel Proxy: %s', e.message)
                continue

            message_uuids = [
                message['uuid']
                for message in messages.get('messages', [])
            ]
            if not message_uuids:
                continue

            for uuids in split_every(BATCH_SIZE, message_uuids):
                proxy_acks = []
                # retrieve attachments for filtered messages
                all_messages = edi_user._call_nemhandel_proxy(
                    "/api/nemhandel/1/get_document",
                    params={'message_uuids': uuids},
                )

                for uuid, content in all_messages.items():
                    enc_key = content['enc_key']
                    document_content = content['document']
                    filename = content['filename'] or 'attachment' # default to attachment, which should not usually happen
                    decoded_document = edi_user._decrypt_data(document_content, enc_key)
                    attachment = self.env['ir.attachment'].create({
                        'name': f'{filename}.xml',
                        'raw': decoded_document,
                        'type': 'binary',
                        'mimetype': 'application/xml',
                    })
                    if edi_user._nemhandel_import_invoice(attachment, content["state"], uuid):
                        # Only acknowledge when we saved the document somewhere
                        proxy_acks.append(uuid)

                if not tools.config['test_enable']:
                    self.env.cr.commit()
                if proxy_acks:
                    edi_user._call_nemhandel_proxy(
                        "/api/nemhandel/1/ack",
                        params={'message_uuids': proxy_acks},
                    )

    def _nemhandel_get_message_status(self):
        for edi_user in self:
            edi_user_moves = self.env['account.move'].search([
                ('nemhandel_move_state', '=', 'processing'),
                ('company_id', '=', edi_user.company_id.id),
            ])
            if not edi_user_moves:
                continue

            message_uuids = {move.nemhandel_message_uuid: move for move in edi_user_moves}
            for uuids in split_every(BATCH_SIZE, message_uuids.keys()):
                messages_to_process = edi_user._call_nemhandel_proxy(
                    "/api/nemhandel/1/get_document",
                    params={'message_uuids': uuids},
                )

                for uuid, content in messages_to_process.items():
                    if uuid == 'error':
                        # this rare edge case can happen if the participant is not active on the proxy side
                        # in this case we can't get information about the invoices
                        edi_user_moves.nemhandel_move_state = 'error'
                        log_message = _("Nemhandel error: %s", content['message'])
                        edi_user_moves._message_log_batch(bodies={move.id: log_message for move in edi_user_moves})
                        break

                    move = message_uuids[uuid]
                    if content.get('error'):
                        # "Nemhandel request not ready" error:
                        # thrown when the IAP is still processing the message
                        if content['error'].get('code') == 702:
                            continue

                        move.nemhandel_move_state = 'error'
                        move._message_log(body=_("Nemhandel error: %s", content['error'].get('data', {}).get('message') or content['error']['message']))
                        continue

                    move.nemhandel_move_state = content['state']
                    move._message_log(body=_('Nemhandel status update: %s', content['state']))

                edi_user._call_nemhandel_proxy(
                    "/api/nemhandel/1/ack",
                    params={'message_uuids': uuids},
                )

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _get_nemhandel_company_details(self):
        self.ensure_one()
        return {
            'nemhandel_company_name': self.company_id.display_name,
            'nemhandel_company_cvr': self.company_id.vat[2:] if self.company_id.vat[:2].isalpha() else self.company_id.vat,
            'nemhandel_country_code': self.company_id.country_id.code,
            'nemhandel_phone_number': self.company_id.nemhandel_phone_number,
            'nemhandel_contact_email': self.company_id.nemhandel_contact_email,
            'nemhandel_webhook_endpoint': self.company_id._get_nemhandel_webhook_endpoint(),
            'nemhandel_webhook_token': self._generate_nemhandel_webhook_token(),
        }

    def _nemhandel_register_as_receiver(self):
        self.ensure_one()

        company = self.company_id
        edi_identification = self._get_proxy_identification(company, 'nemhandel')

        if company.l10n_dk_nemhandel_proxy_state != 'in_verification':
            # a participant can only try registering as a receiver if they are not registered
            nemhandel_state_translated = dict(company._fields['l10n_dk_nemhandel_proxy_state'].selection)[company.l10n_dk_nemhandel_proxy_state]
            raise UserError(_('Cannot register a user with a %s application', nemhandel_state_translated))

        self._check_company_on_nemhandel(company, edi_identification)

        self._call_nemhandel_proxy(endpoint='/api/nemhandel/1/register_participant')
        company.l10n_dk_nemhandel_proxy_state = 'receiver'

    def _nemhandel_deregister_participant(self):
        self.ensure_one()

        if self.company_id.l10n_dk_nemhandel_proxy_state == 'receiver':
            # fetch all documents and message statuses before unlinking the edi user
            # so that the invoices are acknowledged
            self._cron_nemhandel_get_message_status()
            self._cron_nemhandel_get_new_documents()
            if not tools.config['test_enable'] and not modules.module.current_test:
                self.env.cr.commit()

        if self.company_id.l10n_dk_nemhandel_proxy_state != 'not_registered':
            try:
                self._call_nemhandel_proxy(endpoint='/api/nemhandel/1/cancel_nemhandel_registration')
            except AccountEdiProxyError:
                pass

        self.company_id.l10n_dk_nemhandel_proxy_state = 'not_registered'
        self.unlink()

    def _generate_nemhandel_webhook_token(self):
        self.ensure_one()
        expiration = 30 * 24  # in 30 days
        msg = [self.id, self.company_id._get_nemhandel_webhook_endpoint()]
        payload = tools.hash_sign(self.sudo().env, 'account_nemhandel_webhook', msg, expiration_hours=expiration)
        return payload

    @api.model
    def _get_nemhandel_user_from_token(self, token: str, url: str):
        try:
            if not (payload := tools.verify_hash_signed(self.sudo().env, 'account_nemhandel_webhook', token)):
                return None
        except ValueError:
            return None
        else:
            user_id, endpoint = payload
            if not url.startswith(endpoint):
                return None
            return self.browse(user_id).exists()

    def _peppol_reset_webhook(self):
        for edi_user in self:
            edi_user._call_nemhandel_proxy(
                '/api/nemhandel/1/set_webhook',
                params={
                    'webhook_url': edi_user.company_id._get_nemhandel_webhook_endpoint(),
                    'token': edi_user._generate_nemhandel_webhook_token()
                }
            )

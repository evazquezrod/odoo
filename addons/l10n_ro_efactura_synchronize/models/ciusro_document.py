import json
from datetime import datetime

from lxml import etree

from odoo import _, api, models
from odoo.addons.l10n_ro_efactura.models.ciusro_document import (
    make_efactura_request,
)


NS_DOWNLOAD = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}


class L10nRoEdiDocument(models.Model):
    _inherit = 'l10n_ro_edi.document'

    @api.model
    def _request_ciusro_synchronize_invoices(self, company, session, nb_days=1):
        def _process_invoice_data(invoice_data, is_error=False):
            del invoice_data['key_signature']
            del invoice_data['key_certificate']
            if is_error:
                return invoice_data

            root = etree.fromstring(invoice_data['attachment_raw'])
            extracted_data = {
                'name': root.findtext('.//cbc:ID', namespaces=NS_DOWNLOAD),
                'amount_total': root.findtext('.//cbc:TaxInclusiveAmount', namespaces=NS_DOWNLOAD),
                'buyer_vat': root.findtext('.//cac:AccountingSupplierParty//cbc:CompanyID', namespaces=NS_DOWNLOAD),
                'seller_vat': root.findtext('.//cac:AccountingCustomerParty//cbc:CompanyID', namespaces=NS_DOWNLOAD),
                'date': datetime.strptime(root.findtext('.//cbc:IssueDate', namespaces=NS_DOWNLOAD), '%Y-%m-%d').date(),
                'attachment_raw': invoice_data['attachment_raw'],
            }
            
            return extracted_data

        def _process_signature_data(signature_data):
            del signature_data['error']
            return signature_data

        result = make_efactura_request(
            session=session,
            company=company,
            endpoint='listaMesajeFactura',
            method='GET',
            params={'zile': nb_days, 'cif': company.vat.replace('RO', '')},
        )
        if 'error' in result:
            return {'error': result['error']}

        try:
            msg_content = json.loads(result['content'])
        except ValueError:
            return {'error': _("The SPV data could not be parsed.")}

        if eroare := msg_content.get('eroare'):
            return {'error': eroare}

        received_bills_messages = []
        sent_invoices_accepted_messages = []
        sent_invoices_refused_messages = []
        for message in msg_content.get('mesaje'):

            # We need to call `_request_ciusro_download_answer` twice, once to recover
            # the original invoice data or error message using status='nok' and the
            # second one to get the signature using status=None
            invoice_data = self.env['l10n_ro_edi.document']._request_ciusro_download_answer(
                key_download=message['id'],
                company=company,
                session=session,
                status='nok'
            )
            signature_data = self.env['l10n_ro_edi.document']._request_ciusro_download_answer(
                key_download=message['id'],
                company=company,
                session=session,
            )

            signature_data = _process_signature_data(signature_data)

            if message['tip'] == 'FACTURA TRIMISA':
                message['answer'] = {
                    'signature': signature_data,
                    'invoice': _process_invoice_data(invoice_data),
                }
                sent_invoices_accepted_messages.append(message)

            elif message['tip'] == 'ERORI FACTURA':
                message['answer'] = {
                    'signature': signature_data,
                    'invoice': _process_invoice_data(invoice_data, is_error=True),
                }
                sent_invoices_refused_messages.append(message)

            elif message['tip'] == 'FACTURA PRIMITA':                
                message['answer'] = {
                    'signature': signature_data,
                    'invoice': _process_invoice_data(invoice_data),
                }
                received_bills_messages.append(message)

        return {
            'sent_invoices_accepted_messages': sent_invoices_accepted_messages,
            'sent_invoices_refused_messages': sent_invoices_refused_messages,
            'received_bills_messages': received_bills_messages
        }

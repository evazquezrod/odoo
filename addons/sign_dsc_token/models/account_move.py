
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_sign_with_dsc_token(self):
        """Action to sign the documents using DSC USB Token attached on an IoT Box."""

        return {
            'type': 'ir.actions.client',
            'tag': 'action_sign_invoices_with_dsc_token',
            'params': {
                'pin': "12345678",
                'pdf_base64_content': "jkadhfiahgfahgga",
            }
        }

from markupsafe import Markup

from odoo import api, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def _default_company_details(self):
        if not self.env.company.country_code == 'SA':
            return super()._default_company_details()

        additional_company_details = ""

        if self.env.company.vat:
            additional_company_details += self.env.company.vat + Markup('<br/>')
        if self.env.company.l10n_sa_edi_additional_identification_scheme:
            additional_company_details += self.env.company.l10n_sa_edi_additional_identification_scheme + ": "
        if self.env.company.l10n_sa_edi_additional_identification_number:
            additional_company_details += self.env.company.l10n_sa_edi_additional_identification_number

        return super()._default_company_details() + Markup('<br/><br/>%s') % additional_company_details

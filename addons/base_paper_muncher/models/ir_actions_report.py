from odoo import models, fields, api
from odoo.base_paper_muncher.engine import rendered


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def prepare_paper_muncher_args(self):
        ...

    def run_paper_muncher(self):
        with rendered(
            
        ) as pdf_stream, error_stream:

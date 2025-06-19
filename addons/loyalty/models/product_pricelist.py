from odoo import _, models
from odoo.exceptions import ValidationError


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    def action_archive(self):
        loyalty_programs = self.env['loyalty.program'].search([
            ('pricelist_ids', 'in', self.ids)
        ], limit=1)
        if loyalty_programs:
            raise ValidationError(_(
                "This pricelist may not be archived. "
                "It is being used for an active promotion program."
            ))
        return super().action_archive()

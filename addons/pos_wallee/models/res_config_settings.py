from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_pos_wallee = fields.Boolean(string="Wallee Payment Terminal",
        help="The transactions are processed by Wallee. Set your Walllee credentials on the related payment method.")

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ResLang(models.Model):
    _name = 'res.lang'
    _inherit = ['res.lang', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        # TODO: `flag_image_url` is available in the POS data, but it not used in the frontend.
        return ['id', 'name', 'code', 'display_name']

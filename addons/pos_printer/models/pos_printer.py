from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class PosPrinter(models.Model):
    _inherit = 'pos.printer'

    printer_type = fields.Selection(selection_add=[('esc_pos_printer', 'Use a POS Printer')])
    nw_printer_ip = fields.Char(string='Network Printer IP Address', help="Local IP address of a receipt printer.", default="0.0.0.0")
    device_ip = fields.Char(string='Device IP Address', help="Public IP address of a device printer.", default="0.0.0.0")

    @api.constrains('nw_printer_ip')
    def _constrains_nw_printer_ip(self):
        for record in self:
            if record.printer_type == 'esc_pos_printer' and not record.nw_printer_ip:
                raise ValidationError(_("Printer IP Address cannot be empty."))

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['nw_printer_ip', 'device_ip']
        return params

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_network_printer = fields.Boolean(
        string='Use Network Printer',
        help="If checked, the POS will use a network printer for printing receipts.")
    pos_nw_printer_ip = fields.Char(compute='_compute_pos_nw_printer_ip', store=True, readonly=False)
    pos_device_ip = fields.Char(compute='_compute_pos_nw_printer_ip', store=True, readonly=False)

    @api.depends('pos_nw_printer_ip', 'pos_network_printer')
    def _compute_pos_iface_cashdrawer(self):
        """We are just adding depends on this compute."""
        super()._compute_pos_iface_cashdrawer()

    def _is_cashdrawer_displayed(self, res_config):
        return super()._is_cashdrawer_displayed(res_config) or (res_config.pos_network_printer and bool(res_config.pos_nw_printer_ip))

    @api.depends('pos_network_printer', 'pos_config_id')
    def _compute_pos_nw_printer_ip(self):
        for res_config in self:
            if not res_config.pos_network_printer:
                res_config.pos_nw_printer_ip = ''
                res_config.pos_device_ip = ''
            else:
                res_config.pos_nw_printer_ip = res_config.pos_config_id.nw_printer_ip
                res_config.pos_device_ip = res_config.pos_config_id.device_ip

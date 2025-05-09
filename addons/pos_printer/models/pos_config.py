from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    nw_printer_ip = fields.Char(string='Network Printer IP', help="IP address of a receipt printer.")
    device_ip = fields.Char(string='Device IP', help="Local IP address of a receipt printer.")
    network_printer = fields.Boolean(
        string='Use Network Printer',
        help="If checked, the POS will use a network printer for printing receipts.")

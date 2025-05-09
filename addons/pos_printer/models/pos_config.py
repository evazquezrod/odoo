# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    printer_ip = fields.Char(string='Printer IP', help="Local IP address of a receipt printer.")

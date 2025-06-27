# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrDepartureMixin(models.AbstractModel):
    _inherit = ['hr.departure.mixin']

    do_unassign_equipment = fields.Boolean("Free Equiments", default=True, help="Unassign Employee from Equipments")

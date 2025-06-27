# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrDepartureMixin(models.AbstractModel):
    _inherit = ['hr.departure.mixin']

    do_unassign_company_car = fields.Boolean("Release Company Car", default=lambda self: self.env.user.has_group('fleet.fleet_group_user'))

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrDepartureWizard(models.TransientModel):
    _name = 'hr.departure.wizard'
    _inherit = ["hr.departure.mixin"]
    _description = 'Departure Wizard'

    def _get_departure_values(self):
        res = []
        default_vals = {
            'departure_reason_id': self.departure_reason_id.id,
            'departure_description': self.departure_description,
            'departure_date': self.departure_date,
            'action_at': self.action_at,
            'action_other_date': self.action_other_date,
            'apply_date': self.apply_date,
        }
        for field in self._get_action_fields():
            default_vals[field] = self[field]
        for employee in self:
            res.append({
                **default_vals,
                'employee_id': employee.id,
            })
        return res

    def action_register_departure(self):
        self._check_departure_validity()
        departures = self.env['hr.employee.departure'].create(self._get_departure_values())
        if self.apply_immediately:
            departures.action_register()

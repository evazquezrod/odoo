# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployeeDeparture(models.Model):
    _name = "hr.employee.departure"
    _inherit = ["hr.departure.mixin"]
    _description = "Employee Departure"

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        compute="_compute_employee_id", inverse="_inverse_employee_id",
        context={'active_test': False}, store=True, readonly=False,
        domain=lambda self: self._get_domain_employee_ids(),
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')], default="draft", required=True)

    @api.depends('employee_ids')
    def _compute_employee_id(self):
        for departure in self:
            departure.employee_id = False
            if len(departure.employee_ids) == 1:
                departure.employee_id = departure.employee_ids

    def _inverse_employee_id(self):
        for departure in self:
            departure.employee_ids = departure.employee_id

    @api.depends('action_at', 'departure_date', 'action_other_date')
    def _compute_apply_immediately(self):
        super()._compute_apply_immediately()
        for departure in self:
            if departure.state in ['done', 'cancel']:
                departure.apply_immediately = False

    def create(self, vals_list):
        res = super().create(vals_list)
        for departure in res:
            departure.employee_id.write({
                'departure_id': departure.id,
            })
        return res

    def action_register(self):
        self._check_departure_validity()
        for departure in self:
            employee = self.employee_id
            active_version = employee.version_id

            if departure.apply_date > fields.Date.today():
                raise ValidationError(self.env._("The apply date isn't reached yet."))

            if self.do_archive_employee and self.employee_id.active:
                employee.action_archive()

            if self.do_set_date_end and active_version.contract_date_start:
                active_version.write({'contract_date_end': self.departure_date})

        self.state = 'done'

    def action_schedule(self):
        self.state = 'scheduled'

    def action_cancel(self):
        self.state = 'cancelled'
        self.employee_id.version_id.departure_id = False

    def action_draft(self):
        self.state = 'draft'

    def _cron_apply_departure(self):
        departures = self.search([
            ('state', '=', 'scheduled'),
            ('apply_date', '<=', fields.Date.today()),
        ])
        for departure in departures:
            departure.action_register()

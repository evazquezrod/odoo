# Part of Odoo. See LICENSE file for full copyright and licensing details.
from calendar import monthrange

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

from odoo.addons.hr_holidays.models.hr_leave_accrual_plan_level import _get_selection_days


def get_lvl_start_date(start_date, level):
    return start_date + level.get_start_timedelta()


class HrLeaveAccrualPlan(models.Model):
    _name = 'hr.leave.accrual.plan'
    _description = "Accrual Plan"

    active = fields.Boolean(default=True)
    name = fields.Char('Name', required=True)
    time_off_type_id = fields.Many2one('hr.leave.type', string="Time Off Type",
        check_company=True, index='btree_not_null',
        help="""Specify if this accrual plan can only be used with this Time Off Type.
                Leave empty if this accrual plan can be used with any Time Off Type.""")
    employees_count = fields.Integer("Employees", compute='_compute_employee_count')
    level_ids = fields.One2many('hr.leave.accrual.level', 'accrual_plan_id', copy=True, string="Milestone")
    allocation_ids = fields.One2many('hr.leave.allocation', 'accrual_plan_id')
    company_id = fields.Many2one('res.company', string='Company',
        compute="_compute_company_id", store="True", readonly=False)
    transition_mode = fields.Selection([
        ('immediately', 'Immediately'),
        ('end_of_accrual', "After this accrual's period")],
        string="Milestone Transition", default="immediately", required=True,
        help="""Specify what occurs if a level transition takes place in the middle of a pay period.\n
                'Immediately' will switch the employee to the new accrual level on the exact date during the ongoing pay period.\n
                'After this accrual's period' will keep the employee on the same accrual level until the ongoing pay period is complete.
                After it is complete, the new level will take effect when the next pay period begins.""")
    show_transition_mode = fields.Boolean(compute='_compute_show_transition_mode')
    is_based_on_worked_time = fields.Boolean("Based on worked time", compute="_compute_is_based_on_worked_time", store=True, readonly=False,
        help="If checked, the accrual period will be calculated according to the work days, not calendar days.")
    accrued_gain_time = fields.Selection([
        ("start", "At the start of the accrual period"),
        ("end", "At the end of the accrual period")],
        default="end", required=True)
    carryover_date = fields.Selection([
        ("year_start", "At the start of the year"),
        ("allocation", "At the allocation date"),
        ("other", "Other")],
        default="year_start", required=True, string="Carry-Over Time")
    carryover_day = fields.Selection(
        _get_selection_days, compute='_compute_carryover_day', store=True, readonly=False, default='1')
    carryover_month = fields.Selection([
        ("1", "January"),
        ("2", "February"),
        ("3", "March"),
        ("4", "April"),
        ("5", "May"),
        ("6", "June"),
        ("7", "July"),
        ("8", "August"),
        ("9", "September"),
        ("10", "October"),
        ("11", "November"),
        ("12", "December")
    ], default=lambda self: str((fields.Date.today()).month))
    added_value_type = fields.Selection([('day', 'Days'), ('hour', 'Hours')], compute='_compute_added_value_type', store=True)

    @api.depends('level_ids')
    def _compute_show_transition_mode(self):
        for plan in self:
            plan.show_transition_mode = len(plan.level_ids) > 1

    level_count = fields.Integer('Levels', compute='_compute_level_count')

    @api.depends('level_ids')
    def _compute_level_count(self):
        level_read_group = self.env['hr.leave.accrual.level']._read_group(
            [('accrual_plan_id', 'in', self.ids)],
            groupby=['accrual_plan_id'],
            aggregates=['__count'],
        )
        mapped_count = {accrual_plan.id: count for accrual_plan, count in level_read_group}
        for plan in self:
            plan.level_count = mapped_count.get(plan.id, 0)

    @api.depends('allocation_ids')
    def _compute_employee_count(self):
        allocations_read_group = self.env['hr.leave.allocation']._read_group(
            [('accrual_plan_id', 'in', self.ids)],
            ['accrual_plan_id'],
            ['employee_id:count_distinct'],
        )
        allocations_dict = {accrual_plan.id: count for accrual_plan, count in allocations_read_group}
        for plan in self:
            plan.employees_count = allocations_dict.get(plan.id, 0)

    @api.depends('time_off_type_id.company_id')
    def _compute_company_id(self):
        for accrual_plan in self:
            if accrual_plan.time_off_type_id:
                accrual_plan.company_id = accrual_plan.time_off_type_id.company_id
            else:
                accrual_plan.company_id = self.env.company

    @api.depends("accrued_gain_time")
    def _compute_is_based_on_worked_time(self):
        for plan in self:
            if plan.accrued_gain_time == "start":
                plan.is_based_on_worked_time = False

    @api.depends("level_ids")
    def _compute_added_value_type(self):
        for plan in self:
            if plan.level_ids:
                plan.added_value_type = plan.level_ids[0].added_value_type

    @api.depends("carryover_month")
    def _compute_carryover_day(self):
        for plan in self:
            # 2020 is a leap year, so monthrange(2020, february) will return [2, 29]
            plan.carryover_day = str(min(monthrange(2020, int(plan.carryover_month))[1], int(plan.carryover_day)))

    def action_open_accrual_plan_employees(self):
        self.ensure_one()

        return {
            'name': _("Accrual Plan's Employees"),
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,list,form',
            'res_model': 'hr.employee',
            'domain': [('id', 'in', self.allocation_ids.employee_id.ids)],
        }

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", plan.name)) for plan, vals in zip(self, vals_list)]

    @api.ondelete(at_uninstall=False)
    def _prevent_used_plan_unlink(self):
        domain = [
            ('allocation_type', '=', 'accrual'),
            ('accrual_plan_id', 'in', self.ids),
            ('state', 'not in', ('cancel', 'refuse')),
        ]
        if self.env['hr.leave.allocation'].search_count(domain):
            raise ValidationError(_(
                "Some of the accrual plans you're trying to delete are linked to an existing allocation. Delete or cancel them first."
            ))

    def get_lvls_intervals(self, start_date, sorted_levels=False):
        """
        Returns a list containing intervals extrema of each level.
        The start of the level x is the end date of the previous level.
        For instance, if there is 2 levels, this function will return a list of 2 dates :
        the start of the first level, and the start of the second level
        """
        self.ensure_one()
        if not self.level_ids:
            return False
        if not sorted_levels:
            sorted_levels = self.level_ids.sorted('sequence')

        intervals = [get_lvl_start_date(start_date, sorted_levels[0])]
        if len(sorted_levels) == 1:
            return intervals

        if self.transition_mode == 'immediately':
            for i in range(1, len(sorted_levels)):
                intervals.append(get_lvl_start_date(start_date, sorted_levels[i]))
            return intervals

        for i in range(1, len(sorted_levels)):
            expected_lvl_start = get_lvl_start_date(start_date, sorted_levels[i])
            current_lvl = sorted_levels[i]
            lvl_start = current_lvl._get_next_date(expected_lvl_start + relativedelta(days=-1))
            intervals.append(lvl_start)
        return intervals

    def get_lvl_last_date(self, start_date, level_idx, lvls_intervals=False, sorted_levels=False):
        self.ensure_one()
        if not lvls_intervals:
            lvls_intervals = self.get_lvls_intervals(start_date, sorted_levels)
        if level_idx == len(lvls_intervals) - 1:
            return False
        return lvls_intervals[level_idx + 1]

    def _get_current_accrual_plan_level_id(self, start_date, date, lvls_intervals=False):
        """
        Returns a tuple of tuples (lvl, idx) containing the levels we are currently in depending on "date" arg
        It can return up to 2 tuples (when we are at level transition). For example: [(level3, idx), (level4, idx)])
        Arg "lvls_intervals" is there for performance only
        Arg "start_date" is the date the plan start
        """
        self.ensure_one()
        if not self.level_ids:
            return False

        sorted_levels = self.level_ids.sorted('sequence')
        current_level = False
        current_lvl_start = False
        current_level_idx = False
        if not lvls_intervals:
            lvls_intervals = self.get_lvls_intervals(start_date, sorted_levels)
        for idx, lvl_start in enumerate(lvls_intervals):
            if date >= lvl_start:
                current_level = sorted_levels[idx]
                current_level_idx = idx
                current_lvl_start = lvl_start

        if not current_level:
            return False

        if current_level_idx > 0 and date == current_lvl_start:
            return (
                (sorted_levels[current_level_idx - 1], current_level_idx - 1),
                (sorted_levels[current_level_idx], current_level_idx)
            )

        return ((sorted_levels[current_level_idx], current_level_idx),)

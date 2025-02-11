# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Expense(models.Model):
    _inherit = "hr.expense"

    @api.depends('sale_order_id')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        if not self.env.context.get('project_id'):
            expenses_to_recompute = self.env['hr.expense']
            prefetch_ids = set()
            for expense in self:
                if not self.sale_order_id:
                    continue
                expenses_to_recompute += expense
                prefetch_ids.update(list(expense.analytic_distribution.keys()))

            if expenses_to_recompute:
                analytic_account_model = self.env['account.analytic.account'].with_prefetch(prefetch_ids)
                for expense in expenses_to_recompute:
                    project_analytic_distribution = expense.sale_order_id.project_id._get_analytic_distribution()
                    project_analytic_distribution_accounts = self.env['account.analytic.account'].browse(list(project_analytic_distribution.keys()))

                    analytic_accounts = analytic_account_model.browse(list(expense.analytic_distribution.keys()))
                    if expense.analytic_distribution:
                        expense.analytic_distribution = {
                            **expense.analytic_distribution,
                            **project_analytic_distribution
                        }
                    else:
                        expense.analytic_distribution = expense.sale_order_id.project_id._get_analytic_distribution()

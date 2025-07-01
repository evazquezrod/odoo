# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models
from odoo.tools.translate import _


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    linked_project_ids = fields.One2many('project.project', inverse_name='lead_id', help="Projects linked to this lead.")
    linked_project_count = fields.Integer(compute='_compute_linked_project_count', help="Number of projects linked to this lead.")

    @api.depends('linked_project_ids')
    def _compute_linked_project_count(self):
        for lead in self:
            lead.linked_project_count = len(lead.linked_project_ids)

    def open_linked_projects(self):
        self.ensure_one()

        action = {
            'type': 'ir.actions.act_window',
            'name': _('Lead Projects'),
            'res_model': 'project.project',
            'view_mode': 'kanban,form',
            'context': dict(self._context, default_company_id=self.company_id.id),
            'domain': [('id', 'in', self.linked_project_ids.ids)],
            'help': """
                <div class="container mt64">
                    <h1>No Projects found.</h1>
                    <p class="lead">Create a new one from scratch.</p>
                </div>
            """,
        }
        if self.linked_project_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.linked_project_ids.id,
            })
        return action

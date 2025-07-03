# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models
from odoo.tools.translate import _


class ProjectProject(models.Model):
    _inherit = "project.project"

    lead_id = fields.Many2one("crm.lead", help="The lead associated with this project.")

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        updates = {}
        if "allow_billable" in fields_list:
            updates["allow_billable"] = self.env.context.get("default_allow_billable", False)
        if "default_lead_id" in self.env.context:
            lead_id = self.env.context.get("default_lead_id")
            lead = self.env["crm.lead"].browse(lead_id)
            partner_id = lead.partner_id.id if lead else False
            name = lead.name if lead else ''
            updates.update({
                "name": _("Project for Lead: %(lead_name)s", lead_name=name),
                "partner_id": partner_id,
            })
        defaults.update(updates)
        return defaults

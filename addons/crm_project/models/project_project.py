# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        allow_billable = self.env.context.get("default_billable", False)
        partner_id = self.env.context.get("default_partner_id", False)
        defaults.update({"allow_billable": allow_billable,
                         "partner_id": partner_id})
        return defaults

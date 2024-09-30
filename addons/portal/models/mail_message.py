# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request
from odoo.tools import format_datetime, groupby


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _compute_is_current_user_or_guest_author(self):
        super()._compute_is_current_user_or_guest_author()
        for message in self:
            if (
                message.model
                and message.res_id
                and isinstance(message.env[message.model], message.env.registry["portal.mixin"])
            ):
                portal_partner, portal_thread = message.env[
                    message.model
                ]._get_portal_data_from_context()
                if (
                    portal_partner
                    and portal_thread
                    and message.model == portal_thread._name
                    and message.res_id == portal_thread.id
                    and message.author_id == portal_partner
                ):
                    message.is_current_user_or_guest_author = True

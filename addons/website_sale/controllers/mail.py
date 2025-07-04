# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlencode

from odoo import http
from odoo.http import request
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.portal.controllers.mail import MailController


class WebsiteSaleMailController(MailController):

    @add_guest_to_context
    def mail_thread_message_redirect(self, message_id, **kwargs):
        message = request.env["mail.message"].search([('id', '=', message_id)])
        if (
            message.model == "product.template" and
            message.message_type == "comment" and
            not request.env.user._is_internal()
        ):
            url_params = {}
            if highlight_message_id := kwargs.get("highlight_message_id"):
                url_params["highlight_message_id"] = highlight_message_id
            url = f"/shop/{message.res_id}?{urlencode(url_params)}"
            return request.redirect(url)
        return super().mail_thread_message_redirect(message_id, **kwargs)

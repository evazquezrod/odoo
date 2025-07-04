from odoo import _


def get_anonymous_express_partner_name(order):
    context = {'lang': order._get_lang()}  # noqa: F841
    return _("Anonymous express checkout partner for order %s", order.name)

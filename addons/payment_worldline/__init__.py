# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from odoo import api, SUPERUSER_ID
from odoo.addons.payment import setup_provider, reset_payment_provider


def post_init_hook(cr, registry):
    setup_provider(cr, registry, 'worldline')
    _migrate_ogone_to_worldline(cr)


def uninstall_hook(cr, registry):
    reset_payment_provider(cr, registry, 'worldline')


def _migrate_ogone_to_worldline(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    worldline_provider = env['payment.provider'].search([('code', '=', 'worldline')])
    ogone_provider = env['payment.provider'].search([('code', '=', 'ogone')], limit=1)
    if ogone_provider:
        ogone_tokens = env['payment.token'].search([
            ('provider_id', '=', ogone_provider.id)
        ])
        if ogone_tokens:
            ogone_tokens.write({'provider_id': worldline_provider.id})
        ogone_provider.write({'state': 'disabled'})
    env['account.payment.method'].search([('code', '=', 'ogone')]).unlink()

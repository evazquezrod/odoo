# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'G.C.C. - Arabic/English Invoice',
    'version': '1.0.1',
    'category': 'Accounting/Localizations',
    'description': """
Arabic/English for GCC
""",
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'depends': ['account'],
    'post_init_hook': '_l10n_gcc_invoice_post_init',
    'data': [
        'views/report_invoice.xml',
        'views/res_config_settings_views.xml',
    ],
}

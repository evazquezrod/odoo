# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "IoT DSC USB Token Invoker",
    'category': 'Sales/Sales',
    'summary': "IoT",
    'version': '1.0',
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sign_dsc_token/static/src/**/*.js',
        ],
    },
    'application': False,
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

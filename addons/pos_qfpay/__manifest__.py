# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS QFPay',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'author': 'Odoo S.A.',
    'summary': 'Integrate your POS with the QFPay terminal',
    'data': [
        'views/pos_payment_method_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'depends': ['point_of_sale', 'payment'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_qfpay/static/**/*',
        ],
    },
    'license': 'LGPL-3',
}

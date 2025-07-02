{
    'name': "POS Wallee",
    'category': 'Sales/Point of Sale',
    'summary': "Integrate your POS with a Wallee Payment Terminal",
    'version': '1.0',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_payment_method_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_wallee/static/**/*',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}

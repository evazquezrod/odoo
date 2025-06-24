{
    'author': 'Odoo',
    'name': "Romania - Synchronize E-Factura",
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': "Additional module to synchronize bills with the SPV",
    'countries': ['ro'],
    'depends': ['l10n_ro_efactura'],
    'data': [
        'data/ir_cron.xml',
        'views/account_move_views.xml',
        'views/res_config_settings.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

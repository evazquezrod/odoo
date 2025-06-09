# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Product Availability',
    'category': 'Website/Website',
    'summary': 'Manage product inventory & availability',
    'description': """
Manage the inventory of your products and display their availability status in your eCommerce store.
In case of stockout, you can decide to block further sales or to keep selling.
A default behavior can be selected in the Website settings.
Then it can be made specific at the product level.
    """,
    'depends': [
        'website_sale',
        'sale_stock',
        'stock_delivery',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',

        'views/product_template_views.xml',
        'views/return_reason_views.xml',  # used in res_config_settings_views.xml file
        'views/res_config_settings_views.xml',
        'views/sale_portal_templates.xml',
        'views/website_sale_stock_templates.xml',
        'views/stock_picking_views.xml',
        'views/website_pages_views.xml',
        'data/template_email.xml',
        'data/ir_cron_data.xml',
    ],
    'demo': [
        'data/return_reason_demo.xml',
        'data/website_sale_stock_demo.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            ('before', 'website_sale/static/src/js/website_sale.js', 'website_sale_stock/static/src/js/variant_mixin.js'),
            'website_sale_stock/static/src/js/combo_configurator_dialog/*',
            'website_sale_stock/static/src/interactions/*',
            'website_sale_stock/static/src/js/models/*',
            'website_sale_stock/static/src/js/product/*',
            'website_sale_stock/static/src/js/product_card/*',
            'website_sale_stock/static/src/js/product_configurator_dialog/*',
            'website_sale_stock/static/src/js/website_sale.js',
            'website_sale_stock/static/src/js/website_sale_reorder.js',
            'website_sale_stock/static/src/xml/**/*',
            'website_sale_stock/static/src/js/return_order_dialog/*',

        ],
        'web.assets_tests': [
            'website_sale_stock/static/tests/tours/*',
            'website_sale_stock/static/src/js/tours/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

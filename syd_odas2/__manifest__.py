# -*- coding: utf-8 -*-
{
    "name": "AS2 Integration thru OdAS2 Gateway",
    "version": "13.0.2.1.1",
    "category": "API",
    "author": "SayDigital",
    "website": "https://www.saydigital.it",
    "summary": "AS2 Integration thru OdAS2 Gateway",
    "support": "info@rapsodoo.com",
    "description": """ AS2 Integration
""",
    "depends": [
        'web',
        'sale',
        'sale_management',
        'purchase',
        'stock',
        'syd_product_milor',
        'syd_inventory_extended',
        'stock_barcode'
    ],
    "data": [
        # security
        'security/security.xml',
        'security/ir.model.access.csv',

        # data
        'data/action_data.xml',

        # views
        'views/product_product_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_picking_views.xml',
        'views/odas2_views.xml',
        'views/odas2_message_queue_views.xml',
        'views/menu_views.xml',
        'views/res_config_settings_views.xml',

        'wizard/import_wizard_views.xml',

        # cron
        'data/ir_cron_data.xml',
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}

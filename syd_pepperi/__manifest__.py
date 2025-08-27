# -*- coding: utf-8 -*-
{
    "name": "Pepperi Integration",
    "version": "13.0.0.6",
    "category": "API",
    "author": "SayDigital",
    "website": "https://www.saydigital.it",
    "summary": "Pepperi Integration",
    "support": "info@saydigital.it",
    "description": """ Pepperi Integration
""",
    "depends": ['web', 'product', 'sale', 'sale_management', 'contacts', 'stock', 'utm','common_connector_library',"syd_product_milor","syd_partner_milor","syd_commercial_return"],
    "data": [
        # security
        'security/ir.model.access.csv',
        'security/security.xml',
        # action
        'data/action_data.xml',

        # views
        'views/pepperi_account_views.xml',
        'views/product_product_views.xml',
        'views/product_pricelist_views.xml',
        'views/partner_views.xml',
        'views/sale_order_views.xml',
        'wizard/wizard_sale_order_import_views.xml',

        # cron
        'data/ir_cron_data.xml',
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}

# -*- coding: utf-8 -*-

{
    "name": "Thron Integration",
    "version": "0.0.5",
    "category": "API",
    "author": "SayDigital",
    "website": "https://www.saydigital.it",
    "summary": """
        Thron Integration
    """,
    "support": "info@saydigital.it",
    "description": """
        Thron Integration
    """,
    'depends': [
        'sale',
        'syd_product_milor',
        'common_connector_library',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/thron_account_views.xml',
        'views/product_views.xml',

        'data/data.xml',
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}

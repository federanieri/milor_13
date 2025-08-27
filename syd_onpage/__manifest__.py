# -*- coding: utf-8 -*-

{
    "name": "OnPage Integration",
    "version": "0.9.12",
    "category": "API",
    "author": "Rapsodoo Italia",
    "website": "https://www.rapsodoo.com",
    "summary": """
        OnPage Integration
    """,
    "description": """
        OnPage Integration
    """,
    'depends': [
        'sale',
        'product',
        'syd_product_milor',
        'syd_custom',
        'common_connector_library',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/onpage_account_views.xml',
        'views/product_views.xml',
        'views/brands.xml',
        'views/categories.xml',
        'views/collections.xml',
        'data/data.xml',
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}

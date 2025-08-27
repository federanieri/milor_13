# -*- coding: utf-8 -*-

{
    'name': "Variant Grid On Website",
    'version': '1.0.2',
    "author": "SayDigital",
    "website": "https://www.saydigital.it",
    'summary': """Varaint Grid On Website""",
    'description': """
        This module will add a variant grid feature on website.
    """,
    'category' : 'Website',
    'depends': [
        'website_sale',
        'sale_product_matrix',
        'product_matrix',
    ],
    'data':[
        'views/website_sale_templates.xml',
        'views/assets.xml',
    ],
    'license': 'LGPL-3',
    'installable' : True,
    'application' : False,
}

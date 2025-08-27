# -*- coding: utf-8 -*-
{
    'name': "Website B2B Addons",
    'version': '1.0',
    "author": "SayDigital",
    "website": "https://www.saydigital.it",
    'summary': """Website B2B Addons""",
    'description': """
        This module will some features related to b2b.
        - Sale order clone . If the customer goes on a previous sales order it will be possibile to
          add all the product (and their quantity) of the sales order directly in the cart
        - This will allow user to  add new products remaining on the cart searching the product through a search input.
    """,
    'category' : 'Website',

    'depends': [
        'website_sale',
        'sale_management',
    ],

    # always loaded
    'data': [
        'views/templates.xml',
    ],

    'license': 'LGPL-3',
    'installable' : True,
    'application' : False,
}
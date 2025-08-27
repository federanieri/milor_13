# -*- coding: utf-8 -*-
{
    'name': "SYD b2b custom",
    'version': '1.7.5',
    "author": "SayDigital",
    "website": "https://www.saydigital.it",
    'summary': """SYD b2b custom""",
    'description': """
        This module will some features related to b2b custom.
    """,
    'category' : 'Website',

    'depends': [
        'website_sale',
        'common_connector_library',
        'syd_product_milor',
        'syd_product_description_detail',
        'website_sale_stock',
        'website_calendar' ,
        'bi_website_shop_product_filter'
    ],

    'data':[
         'views/website_sale_templates.xml',
         
    ],
    'license': 'LGPL-3',
    'installable' : True,
    'application' : False,
}
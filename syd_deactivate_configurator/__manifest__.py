# -*- coding: utf-8 -*-
{
    'name': "Deactivate Configurator",
    'version': '1.5',
    "author": "SayDigital",
    "website": "https://www.saydigital.it",
    'summary': """Deactivate Configurator""",
    'description': """
        This module will deactivate configurator on backend.
    """,
    'category' : 'Sale',

    'depends': [
        'sale_product_configurator',
    ],

    'data':[
        'security/security.xml',
        'views.xml',
         
    ],

    'installable' : True,
    'application' : False,
    'license': 'LGPL-3',
}
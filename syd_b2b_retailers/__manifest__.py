# -*- coding: utf-8 -*-
{
    'name': "SYD b2b retailers",
    'version': '13.0.1.1',
    "author": "SayDigital",
    "website": "https://www.saydigital.it",
    'summary': """SYD b2b retailers""",
    'description': """
        This module will some features related to b2b retailers.
    """,
    'category' : 'Website',

    'depends': [
        'website_sale',
        'common_connector_library',
    ],

    # always loaded
    'data': [

        'security/security.xml',

        'views/website_views.xml',
        'views/partner_views.xml',
        'views/brand_templates.xml',

        'data/data.xml'
    ],

    'license': 'LGPL-3',
    'installable' : True,
    'application' : False,
}
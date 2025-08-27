# -*- coding: utf-8 -*-

{
    'name': "Stl viewer on eCommerce",
    'version': '1.0',
    "author": "SayDigital",
    "website": "https://www.saydigital.it",
    'summary': """Stl viewer on eCommerce""",
    'description': """
        Stl viewer on eCommerce.
    """,
    'category' : 'Website',
    'depends': [
        'website_sale',
        
        'syd_website_stl_viewer',
    ],
    'data':[
        'views/website_sale_templates.xml',
         'views/views.xml',
    ],
    'license': 'LGPL-3',
    'installable' : True,
    'application' : False,
}

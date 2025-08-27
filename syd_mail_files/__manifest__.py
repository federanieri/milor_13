# -*- coding: utf-8 -*-
{
    'name': "Import Data from Mail",

    'summary': """
        Import Data From files attached in the incoming mails.""",

    'description': """
        Import Data From files attached in the incoming mails.
    """,

    'author': "Rapsodoo Italia",
    "website": "https://www.rapsodoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '13.0.0.0.3',

    # any module necessary for this one to work correctly
    'depends': ['base','mail','syd_custom'],

    # always loaded
    'data': [
        'data/mail_template.xml'
    ],
    'license': 'LGPL-3',
    'installable':True,
    'application':False
}

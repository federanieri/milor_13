# -*- coding: utf-8 -*-
{
    'name': "EAN Management",
    'version': '0.1.0.1',
    'summary': """
        Manage your EAN codes
        """,

    'description': """
        Module to manage EAN codes in the Inventory Application
    """,

    'author': "Rapsodoo Iberia",
    'website': "http://www.rapsodoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',

    # any module necessary for this one to work correctly
    'depends': ['base','stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/assign_ean_view.xml',
         'data/data.xml'
    ],
    # only loaded in demonstration mode

    'license': 'LGPL-3',

    'installable':True,
    'application':False,
    'auto_install':True
}

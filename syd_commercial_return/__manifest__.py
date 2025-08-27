# -*- coding: utf-8 -*-
{
    'name': "Commercial Return Orders Management",
    'version': '13.0.3.3.2',
    'summary': """This module allow your customer to create return RMA order and management of RMA.""",
    'description': """

    """,
    'author': "Rapsodoo Italia",
    'website': "http://www.saydigital.it",
    'category' : 'Website',
    'sequence': 55,
    'depends': [
                'uom',
                'stock',
                'delivery',
                'portal',
                'website_sale',
                'sale',
                'sale_stock',
                'syd_inventory_extended'
                ],
    'data':[
        'security/ir.model.access.csv',
        'data/rma_sequence.xml',
        'data/reasons_default.xml',
        'views/website_portal_sale_templates_sheet.xml',
        'views/return_rma_view.xml',
        'views/reasons.xml',
        'views/sale_order.xml',
        'views/res_config_settings_view.xml',
         'report/return_report.xml',
         'report/report_so.xml',
    ],
    'license': 'LGPL-3',
    'installable' : True,
    'application' : False,
    'auto_install':True
}


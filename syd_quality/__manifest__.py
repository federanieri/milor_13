
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Syd Quality',
    'version': '1.0',
    'category': 'Quality',
    'sequence': 50,
    'summary': 'Basic Feature for Quality',
    'depends': ['stock','stock_picking_batch'],
    'description': """
Quality Base
===============

""",
    'data': [
       
        'security/ir.model.access.csv',
        
        'views/quality_views.xml',
    ],
    'demo': [],
    'application': False,
    'license': 'LGPL-3',
}

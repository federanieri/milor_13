# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'syd portal product proposal custom milor',
    'summary': 'portal product proposal',
    'sequence': 100,
    'website': 'https://www.odoo.com',
    'version': '2.9',
    'author': 'Tiny Erp Pvt. Ltd.',
    'description': """
portal product proposal
=======================
* Able to manage a proposal of a list of product to a customer.
    """,
    'category': 'Custom Development',
    'depends': ['syd_product_proposal','syd_product_milor','sale','stock','purchase','syd_custom'],
    'data': [
        'views/proposal_sale_order_portal_template.xml',
       # 'views/views.xml',
        'report/proposal_report.xml',
        'report/reports.xml',
        'report/sale_order_report.xml',
    ],
    'demo': [],
    'qweb': [],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}

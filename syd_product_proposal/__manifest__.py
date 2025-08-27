# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'syd portal product proposal',
    'summary': 'portal product proposal',
    'sequence': 100,
    'website': 'https://www.rapsodoo.com',
    'version': '3.1.3',
    'author': 'Rapsodoo Italia',
    'description': """
portal product proposal
=======================
* Able to manage a proposal of a list of product to a customer.
    """,
    'category': 'Custom Development',
    'depends': ['sale', 'web', 'website', 'website_sale', 'portal', 'common_connector_library'],
    'data': [
        'security/ir.model.access.csv',
        'security/product_proposal_security.xml',
        'report/proposal_report.xml',
        'data/data.xml',
        'data/ir_sequence_data.xml',
        'data/mail_template.xml',
        'wizard/wizard.xml',
        'views/proposal_sale_order_views.xml',
        'views/proposal_sale_order_portal_template.xml',
        'views/res_config_settings_view.xml'
    ],
    'demo': [],
    'qweb': [],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}

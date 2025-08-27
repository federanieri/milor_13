# -*- encoding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    'name': 'NA Service PO',
    'license': "LGPL-3",
    'author': "Nexapp srl",
    'website': 'https://nexapp.it/',
    'category': 'Nexapp',
    'version': '13.0.1.0',
    'depends': [
        'purchase',
        'syd_custom',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_order_view.xml',
        'views/res_company_view.xml',
        'wizard/confirm_purchase_order_view.xml'
    ],
    'installable': True,
}

# -*- encoding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    'name': 'Nexapp x Milor Logistics',
    'license': "LGPL-3",
    'author': "Nexapp srl",
    'website': 'https://nexapp.it/',
    'category': 'Nexapp',
    'version': '13.0.1.0',
    'depends': [
        'na_api_sync_logistics',
        'stock',
    ],
    'data': [
        'views/stock_picking_view.xml'
    ],
    'installable': True,
}

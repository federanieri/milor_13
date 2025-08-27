# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': "Inventory Zone",
    'version': '1.0',
    'depends': [
        'stock_barcode',
        'stock',
    ],
    'author': "Nexapp S.r.l.",
    'category': 'Inventory/Inventory',
    "summary": "Inventory zone integrated with barcode",
    "website": "https://www.webeasytech.com/",
    "license": "LGPL-3",
    "maintainers": ["Nadia Dotti"],
    'data': [
        'views/stock_inventory_views.xml',
        'views/stock_move_line_views.xml',
    ],
}

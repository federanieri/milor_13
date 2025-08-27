# -*- encoding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    'name': 'Nexapp API Sync Logistics',
    'license': "LGPL-3",
    'author': "Nexapp srl",
    'website': 'https://nexapp.it/',
    'category': 'Nexapp',
    'version': '13.0.1.0',
    'depends': [
        'na_api_sync',
        'stock',
    ],
    'data': [
        'data/ir_cron_data.xml',
        'views/na_api_sync_env_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
}

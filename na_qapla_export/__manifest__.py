# -- coding: utf-8 --
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'NexApp Qapla export via FTP',
    'version': '13.0.1',
    'category': 'NexApp',
    'summary': 'NexApp Qapla export via FTP',
    'author': 'NexApp s.r.l.',
    'website': 'www.nexapp.it',
    'license': 'LGPL-3',
    "depends": [
        'delivery',
        'stock',
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/delivery_carrier_views.xml',
        'views/qapla_export_views.xml',
        'views/qapla_logger_views.xml',
        'views/res_config_settings.xml',
    ],
    'installable': True,
    'application': True,
}

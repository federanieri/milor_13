# -- coding: utf-8 --
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'NexApp Ring Size Conversion',
    'version': '13.0.1',
    'category': 'NexApp',
    'summary': 'Tabella di conversione delle taglie degli anelli',
    'author': 'NexApp s.r.l.',
    'website': 'www.nexapp.it',
    'license': 'AGPL-3',
    "depends": [
        'base',
        'product',
    ],
    "data": [
        # 'security/ir.model.access.csv',
        'views/res_config_settings_view.xml',
        'views/ring_size_conversion_view.xml',
        'data/size_conversions.xml',
    ],
    'installable': True,
}

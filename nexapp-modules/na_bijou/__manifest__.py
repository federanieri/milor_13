# -- coding: utf-8 --
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'NexApp Bijou',
    'version': '13.0.1',
    'category': 'NexApp',
    'summary': 'Gestisci ordini Bijou',
    'author': 'NexApp s.r.l.',
    'website': 'www.nexapp.it',
    'license': 'AGPL-3',
    "depends": [
        'base',
        'sale',
        'na_ring_size_conversion',
    ],
    "data": [
        'data/res_groups.xml',
        'data/utm_source.xml',
        'data/bl_template_email.xml',
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/bijou_account_views.xml',
    ],
    'installable': True,
}

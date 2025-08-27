# -- coding: utf-8 --
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'NexApp Syd Custom',
    'version': '13.0.1',
    'category': 'NexApp',
    'summary': 'NexApp Syd Custom',
    'author': 'NexApp s.r.l.',
    'website': 'www.nexapp.it',
    'license': 'AGPL-3',
    "depends": [
        'base',
        'product',
        'syd_custom',
        'syd_product_milor',
    ],
    "data": [
        'views/product_template_views.xml',
    ],
    'installable': True,
}

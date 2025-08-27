# -*- encoding: utf-8 -*-

{
    'name': 'Qty CRMA in invoice',
    'version': '13.0.0.0.1',
    'author': "Rapsodoo",
    'maintainer': 'Rapsodoo',
    'category': 'base',
    'depends': ['account','syd_commercial_return'],
    'description': """
                Check Qty CRMA in Invoice
                """,
    'summary': """Check Qty CRMA in Invoice""",
    'website': 'http://www.rapsodoo.com',
    'data': [
        'views/account_move_view.xml',
    ],
    'license': 'LGPL-3',
    'auto_install': True,
}

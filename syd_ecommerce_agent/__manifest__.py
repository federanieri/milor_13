{
    'name': 'Sys eCommerce Agent',
    'version': '2.0',
    'category' : 'Website',
    'summary': '',
    'description': """
        Through this module the agents can operate and buy for their client’s portfolio (retailers) on the B2B Website.
        """,
    'depends': [
        'syd_b2b_retailers','syd_commercial_return',
    ],
    'data': [
        'security/base_security.xml',

        'views/templates.xml',
#         'views/sale_view.xml',
        'views/partner_views.xml',
        'views/return_order_view.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

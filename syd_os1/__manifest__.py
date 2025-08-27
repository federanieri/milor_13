# -*- coding: utf-8 -*-
{
    'name': "OS1",

    'summary': """
        OS1 Integration""",

    'description': """
        OS1 Integration
    """,

    'author': "SayDigital",
    'website': "http://www.saydigital.it",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/10.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '13.0.4.0.7',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'base_automation',
                'account',
                'syd_product_milor',
                'syd_partner_milor',
                'l10n_it_edi',
                'website_shop_return_rma',
                'delivery_dhl',
                'delivery_ups',
                'l10n_it_edi',
                'syd_commercial_return'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/views_os1.xml',
        'views/templates.xml',
       'views/views_sale_order.xml',
        'views/views_document_os1.xml',
        'views/views_stock_picking.xml',
        'views/views_return_order_sheet.xml',
        'views/partner_view.xml',
#         'views/views_stock_quant_package.xml',
        'data/service_cron.xml',
        'data/action_data.xml',
        'data/ir_sequence_data.xml',
        'data/action_server.xml',
        'wizard/view.xml',
        'wizard/view_force_done.xml',
        'views/menu.xml',
        'views/account_move.xml',
        'views/res_config_settings.xml'
    ],
    'license': 'LGPL-3',
}

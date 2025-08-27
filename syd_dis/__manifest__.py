# -*- coding: utf-8 -*-
{
    "name": "Syd DIS",
    "version": "13.0.0.1.1",
    "category": "API",
    "author": "SayDigital",
    "website": "https://www.saydigital.it",
    "summary": "Drawings management",
    "support": "info@rapsodoo.com",
    "description": """""",
    "depends": [
        'project',
        'product',
        'purchase',
        'syd_custom',
        'syd_product_milor',
        'syd_odas2',
        'syd_website_stl_viewer'
    ],
    "data": [
        # data
        'data/action_data.xml',
        'data/ir_cron_data.xml',

        # security
        'security/security.xml',
        'security/ir.model.access.csv',

        # views
        'views/portal_templates.xml',
        'views/product_views.xml',
        'views/project_views.xml',
        'views/purchase_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}

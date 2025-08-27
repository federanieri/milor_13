{
    "name": "Product Milor",
    "version": "13.0.0.2.8",
    "category": "base",
    "author": "SayDigital",
    "website": "https://www.saydigital.it",
    "summary": "Product Specification for Milor",
    "support": "info@saydigital.it",
    "description": """ 
        Product Specification for Milor
    """,
    "depends": ["web","product","sale","website_sale","purchase_stock","utm"],
    "data": [
        "data/data.xml",
        "data/mail_templates.xml",
        "data/ir_cron_data.xml",
        "security/ir.model.access.csv",
        "views/views.xml",
        "views/sale_order.xml",
        "views/utm_views.xml",

    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": True,
}


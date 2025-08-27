{
    "name": "Inventory Extended",
    "version": "13.0.1.0.1",
    "category": "base",
    "author": "SayDigital",
    "website": "https://www.saydigital.it",
    "summary": "Inventory Extended",
    "support": "info@saydigital.it",
    "description": """ 
        Inventory Extended
    """,
    "depends": ["web","purchase_stock","delivery","sale_stock",'inter_company_rules'],
    "data": [
             "security/security.xml",
             "security/ir.model.access.csv",
             "views/views.xml",
             "views/stock_barcode_templates.xml",
             "report/report_package_barcode.xml",
             "report/stock_report_views.xml",
             "wizard/wizard.xml",
             "data/data.xml"
             ],
    'qweb': [
        "static/src/xml/qweb_templates.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}


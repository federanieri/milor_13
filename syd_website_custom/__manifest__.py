{
    "name": "Website Custom Milor",
    'version': "13.0.1.8",
    "category": "base",
    "author": "SayDigital",
    "website": "https://www.saydigital.it",
    "summary": "Custom Website Milor",
    "support": "info@saydigital.it",
    "description": """ 
        Custom Website Milor
    """,
    "depends": ["base","theme_clarico","sale","website","website_sale","product","sale_stock","delivery"],
    "data": [
             'views/website_product_templates.xml',
             'views/assets.xml',
             'views/sale_views.xml',
             'views/templates.xml',
             'views/order_templates.xml'
        ],
    'qweb': ['static/src/xml/*.xml'],
    'license': 'LGPL-3',
    "installable": True,
}
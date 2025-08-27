{
    'name': "Variant Grid On Website",
    'version': '13.0.1.0.0',
    "author": "SayDigital",
    "website": "https://www.saydigital.it",
    'summary': """Report Variant Grid""",
    'description': """
        This module will add a variant grid feature on website.
    """,
    'category' : 'Operations/Purchase',
    'depends': [
        'purchase',
        'purchase_product_matrix',
    ],
    'data':[
        'report/purchase_order_templates.xml',
        'report/purchase_order_report.xml',
    ],
    'license': 'LGPL-3',
    'auto_install': True,
    'installable' : True,
    'application' : False,
}

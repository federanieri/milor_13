{
    'name': 'Sale Proposal Import',
    'version': '13.0.1.0.0',
    'category': 'Sales',
    'summery': 'Sale Proposal Import',
    'author': '',
    'depends': ['syd_product_proposal', 'syd_commercial_return', 'syd_custom'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/proposal_sale_line_import_wizard_view.xml',
        'views/proposal_sale_order_view.xml',
        'data/sample_sale_proposal_import.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}

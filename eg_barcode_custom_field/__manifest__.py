{
    'name': 'Barcode Custom Field',
    'version': '13.0.1.0.0',
    'category': 'Inventory',
    'summery': 'Barcode Custom Field',
    'author': '',
    'depends': ['stock_barcode', 'syd_inventory_extended'],
    'data': [
    ],
    'qweb': [
        'static/src/xml/stock_barcode_lines_widget.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}

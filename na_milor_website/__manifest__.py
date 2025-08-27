{
    'name': 'NA MIlor Website',
    'summary': "Sito web milor B2B",
    'description': "Modulo Odoo 13EE per customizzare il sito web B2B del cliente Milor",
    'version': '1.0',
    'depends':	[
        'website_theme_install',
        'website_sale_wishlist',
	    'website_sale_comparison',
        'website_blog',
        'bi_website_shop_product_filter',
        'emipro_theme_base',
        'syd_product_milor'
    ],
    'author': "Nexapp",
    'license': "LGPL-3",
    'website': 'https://www.nexapp.it',
    'category': 'Nexapp',
    'sequence':	100,
    'data': [
        'views/product_season.xml'
    ],
}

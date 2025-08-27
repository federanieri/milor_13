# -*- encoding: utf-8 -*-

{
 'name': 'Table Commercehub',
 'version': '13.0.0.3.4',
 'author': "Rapsodoo",
 'maintainer': 'Rapsodoo',
 'category': 'base',
 'depends': ['stock','sale','syd_odas2','sale_stock','syd_closable_order','syd_product_milor'],
 'description': """
                Table Commercehub Order Helper
                """,
 'summary': """Table Order Helper""",
 'website': 'http://www.rapsodoo.com',
 'data': [
  'views/views.xml',
  'views/res_config_settings_view.xml',
  'security/ir.model.access.csv'

 ],
 'demo': [],
 'test': [],
 'images': [],
 'license': 'LGPL-3',
 'installable': True,
 'auto_install': False,
 'application': False,
}

# -*- encoding: utf-8 -*-

{'name': 'Table',
 'version': '13.0.0.1',
 'author': "Rapsodoo",
 'maintainer': 'Rapsodoo',
 'category': 'base',   
 'depends': ['stock','sale','common_connector_library','sale_stock','purchase','product','syd_product_milor'],
 'description': """
                Table Order Helper
                """,
 'summary': """Table Order Helper""",
 'website': 'http://www.rapsodoo.com',
 'data': [
          
          'report/table_report_views_main.xml',
          'report/table_report_templates.xml',
          'views/views.xml',
          'security/ir.model.access.csv'
          
          ],
 'demo': [],
 'test': [],
 'installable': True,
 'images': [],
 'auto_install': False,
 'license': 'LGPL-3',
 'application': False,
 }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

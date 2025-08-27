{
    'name': "NA Milor Onpage",
    'version': '1.1',
    'depends': ['base', 'product', 'stock', 'syd_onpage', 'na_milor_product'],
    'author': "Nexapp, Lerda Jacopo",
    'category': 'Nexapp',
    'description': """
                   Modulo per aggiornare la trasmissione di dati dell'anangrafica prodotti a onpage tramite file csv
                    """,
    'external_dependencies': {'python': ['csv', 'requests', 'datetime']},
    'data': [
        'security/ir.model.access.csv',
        'data/ir_action_schedule_export.xml',
        'data/ir_action_schedule_cleanup.xml',
        'data/ir_action_schedule_temporary_onpage.xml',
        'data/na_onpage_actions_server.xml',
        'views/res_config_settings_view.xml',
        'views/stock_location_view.xml',
        'views/onpage_logs.xml'
    ],
    'application': 'true'
}

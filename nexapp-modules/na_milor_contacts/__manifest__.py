{
    'name': "NA Milor contacts",
    'version': '1.0',
    'depends': ['base', 'syd_partner_milor'],
    'author': "Nexapp, Lerda Jacopo",
    'category': 'Nexapp',
    'description': """
                   Modulo per customizzare i contatti per l'azienda Milor
                    """,
    'data': [
        'views/res_partner.xml',
        'views/zone_view.xml',
        'security/ir.model.access.csv',
    ],
    'application': 'true'
}

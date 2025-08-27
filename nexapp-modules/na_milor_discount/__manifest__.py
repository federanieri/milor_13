{
    'name': "NA Milor discount",
    'version': '1.0',
    'depends': ['base', 'sale', 'syd_custom'],
    'author': "Nexapp, Lerda Jacopo",
    'category': 'Nexapp',
    'description': """
                   Modulo per automatizzare l'inserimento dello sconto di riga in funzione del cliente dell'ordine di vendita
                    """,
    'external_dependencies': {'python': ['datetime']},
    'data': [
        'views/res_partner.xml',
        'views/sale_order.xml',
        'security/ir.model.access.csv',
        'wizards/confirmation_wizard.xml',
        'wizards/custom_discount_view.xml',
    ],
    'application': 'true'
}

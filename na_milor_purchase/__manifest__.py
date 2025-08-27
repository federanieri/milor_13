{
    'name': "NA Milor purchase",
    'version': '1.0',
    'depends': ['base', 'syd_inventory_extended', 'syd_custom', 'purchase'],
    'author': "Nexapp, Bortolotti Manuel",
    'category': 'Nexapp',
    'description': """
                   Questo modulo aggiunge una funzionalità all'interno degli acquisti: 
                    - viene creata una nuova voce sotto il menu 
                      Acquisti > Configurazione: "Completa trasferimenti acquisti chiusi" group: base.group_no_one
                    - cliccando sul menu si apre un wizard che contiene un campo date e un bottone
                    - specificando una data, tramite il bottone possiamo andare a completare tutti i movimenti di 
                      magazzino (stock.picking), e le relative righe di dettaglio (stock.move) collegati ai 
                      purchase.order con il campo "closed" impostato a True e precedenti alla data impostata 
                      nel campo del wizard.
                    """,
    'data': [
        'security/ir.model.access.csv',
        'wizard/na_purchase_view.xml',
        'report/purchase_order_templates.xml',
    ],
    'application': 'true'
}

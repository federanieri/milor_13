from odoo import fields, models, api


class NaOnpageLog(models.Model):
    _order = 'create_date desc'
    _name = 'na.onpage.log'

    outcome = fields.Selection([('sent', 'Inviato correttamente'), ('error_onpage', 'Non inviato (Onpage)'),
                                ('error_odoo', 'Non inviato (Odoo)')], string="Esito dell'invio", readonly=True)
    error_message = fields.Text(string="Messaggio di errore", readonly=True)
    trigger_user = fields.Many2one('res.users', string="Utente", readonly=True)
    create_date = fields.Datetime(string="Data di creazione")

    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, f"Trasmissione dati onpage_{record.id}"))
        return res

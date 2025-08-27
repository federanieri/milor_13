from odoo import models

class NaStockPicking(models.Model):
    _inherit = 'stock.picking'

    def _date_deadline(self):
        for a in self:
            date_deadline_from = False
            date_deadline_to = False
            #### Rapsodoo code ####
            #for m in a.move_lines:
            #### Nexapp code ####
            for m in a.move_lines.filtered(lambda x: x.state != "cancel"):
                date_deadline_from = m.date_deadline_from if not date_deadline_from else (
                    m.date_deadline_from if m.date_deadline_from < date_deadline_from else date_deadline_from)
                date_deadline_to = m.date_deadline_to if not date_deadline_to else (
                    m.date_deadline_to if m.date_deadline_to > date_deadline_to else date_deadline_from)
            a.write(
                {
                    'date_deadline_from': date_deadline_from,
                    'date_deadline_to': date_deadline_to
                }
            )

# -- coding: utf-8 --
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def write(self, vals):

        if self.move_id.inventory_id:
            if self.move_id.inventory_id.accounting_date and vals.get('date'):
                vals['date'] = self.move_id.inventory_id.accounting_date
        res = super().write(vals)
        return res
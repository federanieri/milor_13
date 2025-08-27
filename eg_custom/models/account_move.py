from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def set_return_quantity(self):
        """
        action server for set return quantity of main quantity
        :return:
        """
        for rec in self:
            for invoice_line_id in rec.invoice_line_ids:
                invoice_line_id.write({
                    'qty_max_crma': invoice_line_id.quantity,
                })

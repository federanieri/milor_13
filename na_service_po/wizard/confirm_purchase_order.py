# -*- encoding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models, _


class ConfirmPurchaseOrder(models.TransientModel):
    _name = 'confirm.purchase.order'

    def button_confirm_check(self):
        order_id = self._context.get('active_id')
        purchase_order = self.env['purchase.order'].browse(order_id)
        purchase_order.button_confirm(pass_check=True)


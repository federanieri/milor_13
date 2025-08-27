from odoo import models, fields, api, _

class CommercehubOrder(models.Model):
    _inherit = 'order_table.commercehub_order'

    def cancel_ch_orders(self):
        for record in self:
            if record.commercehub_po:
                purchases = self.env['purchase.order'].sudo().search([('commercehub_po','=',record.commercehub_po)])
                sales = self.env['sale.order'].sudo().search([('commercehub_po','=',record.commercehub_po)])
                for purchase in purchases:
                    purchase.button_cancel()
                for sale in sales:
                    sale.action_cancel()

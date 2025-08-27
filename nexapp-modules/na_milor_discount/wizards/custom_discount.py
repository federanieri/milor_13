from odoo import models, fields

class NaCustomDiscount(models.TransientModel):
    _name = "na.custom.discount"

    discount_value = fields.Float(string="Sconto")

    def apply_custom_discount(self):
        sale_order_ids = self.env.context.get('active_ids')
        active_sale_orders = self.env['sale.order'].browse(sale_order_ids)
        for order in active_sale_orders:
            for line in order.order_line:
                line.discount = self.discount_value


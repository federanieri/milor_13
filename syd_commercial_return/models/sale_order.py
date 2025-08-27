from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    crma_origin_id = fields.Many2one('return.order.sheet', string='CRMA to Repair')
    repair_so = fields.Boolean("REPAIR SO")
    
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    repair_product_for = fields.Many2one('product.product', string='Product to repair')
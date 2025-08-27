import datetime, calendar
from dateutil.relativedelta import relativedelta
from odoo import api, exceptions, fields, models, _,SUPERUSER_ID
from odoo.exceptions import UserError, AccessError, ValidationError
from werkzeug import urls
import calendar
from odoo import tools
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_join
from odoo.tools.safe_eval import safe_eval

class WizardOrder(models.TransientModel):
    _name = "syd_custom.wizard_order"
    _description = 'Wizard Order'
    
    customer_id = fields.Many2one('res.partner','Customer')
    product_ids = fields.Many2many('product.product',string='Product')
    
    def create_order(self):
        order_line = []
        for p in self.product_ids:
            order_line.append((0,0,{
                               'product_id':p.id,
                               }))
        sale_order = self.env['sale.order'].create({
                                       'partner_id':self.customer_id.id,
                                       'order_line':order_line
                                       })
    
        action = self.env['ir.actions.act_window'].for_xml_id('sale', 'action_quotations_with_onboarding')
        action['domain'] = [('id','=',sale_order.id)]
        action['res_id'] = sale_order.id
        return action
    
    
class WizardPurchaseOrder(models.TransientModel):
    _name = "syd_custom.wizard_purchase_order"
    _description = 'Wizard Order'
    
    partner_id = fields.Many2one('res.partner','Vendor')
    product_ids = fields.Many2many('product.product',string='Products')
    
    def create_order(self):
        Order_line = self.env['purchase.order.line']
        
        purchase_order = self.env['purchase.order'].create({
                                       'partner_id':self.partner_id.id,
                                       })
        for p in self.product_ids:
            order_line = Order_line.create({
                               'product_id':p.id,
                               'product_qty':0,
                               'price_unit':0.0,
                               'name':p.name,
                               'order_id':purchase_order.id,
                               'date_planned':fields.Date.today(),
                               'product_uom':p.uom_id.id
                               })
            order_line.onchange_product_id()
        action = self.env['ir.actions.act_window'].for_xml_id('purchase', 'purchase_rfq')
        action['domain'] = [('id','=',purchase_order.id)]
        action['res_id'] = purchase_order.id
        return action
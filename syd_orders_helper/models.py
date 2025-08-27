from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from random import randint
import datetime
import time
import collections
from odoo.tools.safe_eval import safe_eval

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    helper_id = fields.Many2one('syd_orders_helper.forecast_order',string="Helper")
    
class ForecastOrder(models.Model):
    _name = 'syd_orders_helper.forecast_order'
    _description = 'Purchase order helper'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    
    user_id = fields.Many2one('res.users','User',default=lambda self: self.env.user.id)
    date = fields.Date('Date Orders',required=True)
    name=fields.Char('Name',required=True)
    under_stock = fields.Boolean('Under stock')
    filter_domain = fields.Char('Product Filter', help=" Filter on the object")
    model_name = fields.Char(default='product.product', string='Model Name', readonly=True, store=True)
    forecast_order_line_ids = fields.One2many('syd_orders_helper.forecast_order_line','forecast_order_id')
    move_show = fields.Boolean('Show movement',default=False)
    move_type= fields.Selection([('incoming', 'Receipt'), ('outgoing', 'Delivery')], 'Type of Operation')
    month_number = fields.Integer('Month movements',default=12,required=True)
    state=fields.Selection([('draft','Draft'),('in_progress','In Progress'),('confirmed','Confirmed')],default="draft",string="State")
    po_ids = fields.One2many('purchase.order','helper_id',string="Purchase Orders")
    po_count = fields.Integer('Po Count',compute="_po_count")
    show=fields.Boolean('Show')
    filter_id = fields.Many2one('ir.filters','Product Filter',domain="[('model_id','=','product.product'),'|',('user_id','=',user_id),('user_id','=',False)]")
    
    @api.onchange('filter_id')
    def onchange_filter(self):
        if self.filter_id:
            self.filter_domain = self.filter_id.domain
            
    def _po_count(self):
        for a in self:
            a.po_count = len(a.po_ids)
            
    def generate_html(self,product,number=12):
        if number == 0:
            return ""
        domain = [
            ('state', 'in', ['done']),
            ('product_id', '=', product.id),
            ('picking_code','=',self.move_type)
        ]
        
        movements = self.env['stock.move'].search(domain)
        d = datetime.datetime.now()
        months = collections.OrderedDict()
        months[d.strftime("%b-%y")] = 0
        for i in range(number-1):
            d = d - relativedelta(months=1)
            months[d.strftime("%b-%y")] = 0
            
        for o in movements:
            dt = fields.Date.from_string(o.date)
            if dt.strftime("%b-%y") in months:
                months[dt.strftime("%b-%y")] += o.quantity_done 
        theader =""
        tbody = ""
        for m in months:
            theader+="""<th style="border: 1px solid black;padding:4px;">%s</th>""" % (m)
            tbody+= """<td style="border: 1px solid black;padding:4px;">%d</td>""" % (months[m])
        
        return "<table><tr>%s</tr><tr>%s</tr></table>"%(theader,tbody) 
               
    def action_view_po(self):
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        action['context'] = dict(self._context or {})
        action['domain'] = [('id','in',self.po_ids.ids)]
        return action
        
    def create_order(self):
        orders = {}
        for l in self.forecast_order_line_ids:
            if l.to_order > 0 :
                if not l.partner_id.id:
                    raise ValidationError('No vendor for %s'%l.product_id.display_name)
                else:
                    if l.partner_id.id not in orders:
                       orders[l.partner_id.id]=[[0,False, {'price_unit':0,u'product_id': l.product_id.id, 'product_uom': l.product_id.uom_id.id, u'date_planned': self.date, u'sequence': l.sequence,'product_qty': l.to_order, 'name': l.product_id.name}]]
                    else:
                        orders[l.partner_id.id].append([0,False, {'price_unit':0,'product_id': l.product_id.id, 'product_uom': l.product_id.uom_id.id, u'date_planned': self.date, u'sequence': l.sequence,'product_qty': l.to_order, 'name': l.product_id.name}])
        for partner_id,lines in orders.items():
                
                vals = {
                    'date_order': self.date,  
                    'date_planned': self.date, 
                    'partner_id': partner_id,
                    
                    'helper_id':self.id
                    }
                
                order = self.env['purchase.order'].create(vals)
                for line in lines:
                    line[2]['order_id']=order.id
                    order_line = self.env['purchase.order.line'].create(
                                   line[2]
                                   )
                    order_line.onchange_product_id()
                    order_line.product_qty = line[2]['product_qty']
        
        
        return True
    
        
    def confirm(self):
        self.state = 'confirmed'
        for p in self.forecast_order_line_ids:
            if p.to_order == 0:
                p.unlink()

    def populate(self):
        
        domain = (safe_eval(self.filter_domain,  {}) if self.filter_domain else [])
        products = self.env['product.product'].search(domain)
        pr = []
        for p in products:
                product_id = p.id
                sold = self.generate_html(p,self.month_number)
                backorder = p.virtual_available
                stock = p.qty_available
                pref_stock = int(p.reordering_max_qty)
                tot_sold = p.sales_count
                to_order = (pref_stock-backorder) if (pref_stock-backorder) > 0 else 0
                if not self.under_stock or to_order > 0:
                    values = {
                              'product_id':product_id,
                              'sold':sold,
                              'forecast':backorder,
                              'stock':stock,
                              'pref_stock':pref_stock,
                              'to_order':to_order,
                              'tot_sold':tot_sold,
                              
                              }
#
                    pr.append([0,False,values])
        self.forecast_order_line_ids = pr
        self.show = True
        self.state = 'in_progress'
        
        
class ForecastOrderLine(models.Model):
    _name = 'syd_orders_helper.forecast_order_line'
    _description = 'Purchase order helper Line '
    forecast_order_id = fields.Many2one('syd_orders_helper.forecast_order','Order')
    product_id = fields.Many2one('product.product','Product',readonly=True)
    
    sold = fields.Html('Movements in month',readonly=True)
    tot_sold = fields.Integer('Tot Sold',readonly=True)

    forecast = fields.Integer('Forecast',readonly=True)
    stock = fields.Integer('In Stock',readonly=True)
    pref_stock = fields.Integer('Preferred Stock',readonly=True)
    to_order = fields.Integer('To Order',readonly=False)
    under_stock = fields.Boolean('Under stock',compute="_under_stock")
    sequence = fields.Integer('Sequence')
    partner_id = fields.Many2one('res.partner',string='Vendor',compute="_get_vendor",store=True,readonly=False)
    image_1024 = fields.Image("Image 1024", related="product_id.image_1024", max_width=1024, max_height=1024)
    image_512 = fields.Image("Image 512", related="product_id.image_512", max_width=512, max_height=512)
    image_256 = fields.Image("Image 256", related="product_id.image_256", max_width=256, max_height=256)
    image_128 = fields.Image("Image 128", related="product_id.image_128", max_width=128, max_height=128)
    
    def _get_vendor(self):
        for a in self:
            sinfo = self.env['product.supplierinfo'].search([('name','=',a.partner_id.id),('product_tmpl_id','=',a.product_tmpl_id.id)],limit=1)
            a.partner_id = sinfo.id
            
    def _under_stock(self):
        for o in self:
            if o.to_order > 0:
                o.under_stock = True
            else :
                o.under_stock = False
    
    
            
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
    
    table_id = fields.Many2one('order_table.forecast_order',string="Table")



class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    table_id = fields.Many2one('order_table.forecast_order',string="Table")
    
class ForecastTemplateOrder(models.Model):
    _name = 'order_table.template_forecast'
    _description = "Sale Forecast Template"
    
    name=fields.Char('Name')
    base_pricelist_id = fields.Many2one('product.pricelist','Base Pricelist')
    internal_pricelist_id = fields.Many2one('product.pricelist','Internal Pricelist')
    promo_pricelist_id = fields.Many2one('product.pricelist','Promo Pricelist')
    stock_location_id = fields.Many2one('stock.location','Milor SPA Location')
    other_location_id = fields.Many2one('stock.location','Milor Group Location')
    report_sale_domain = fields.Char('Report Sale Domain')
    report_sale_model = fields.Char(default="sale.report")
    report_sale_domain_other = fields.Char('Report Sale Domain Milor Group')
        
    product_filter_domain = fields.Char('Product Filter', help="Filter on the object")
    product_model_name = fields.Char(default='product.product', string='Model Name', readonly=True, store=True)
    filter_id = fields.Many2one('ir.filters','Product Filter',domain="[('model_id','=','product.product'),'|',('user_id','=',user_id),('user_id','=',False)]")
    company_id = fields.Many2one('res.company',required=True,default=lambda self: self.env.company.id)
    other_company_id = fields.Many2one('res.partner','Milor Group')
    
class ForecastOrder(models.Model):
    _name = 'order_table.forecast_order'
    _description = 'Sale order helper'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    
    user_id = fields.Many2one('res.users','User',default=lambda self: self.env.user.id)
    date = fields.Date('Date Orders',required=True,default=fields.Date.today)
    name=fields.Char('Name',required=True)
    template_id = fields.Many2one('order_table.template_forecast',required=True,default=lambda self: self.env['order_table.template_forecast'].search([],limit=1).id)

    forecast_order_line_ids = fields.One2many('order_table.forecast_order_line','forecast_order_id')
    
    state=fields.Selection([('draft','Draft'),('in_progress','In Progress'),('confirmed','Confirmed')],default="draft",string="State")
    
    
    date_order_start = fields.Date('Date Order Start')
    date_order_end = fields.Date('Date Order End')
    po_ids = fields.One2many('purchase.order','table_id',string="Purchase Orders")
    po_count = fields.Integer('Po Count',compute="_po_count")
    so_ids = fields.One2many('sale.order','table_id',string="Purchase Orders")
    so_count = fields.Integer('So Count',compute="_so_count")
    line_count = fields.Integer('Po Count',compute="_line_count")
    
     
    def _line_count(self):
        for a in self:
            a.line_count = len(a.forecast_order_line_ids)     
            
            
    def create_so(self):
        self.ensure_one()
        order_line = []
        for p in self.forecast_order_line_ids.filtered(lambda x : x.to_send>0):
            order_line.append((0,0,{
                               'product_id':p.product_id.id,
                               'product_qty':p.to_send
                               
                               }))
        sale_order = self.env['sale.order'].create({
                                       'partner_id':self.template_id.other_company_id.id,
                                       'order_line':order_line,
                                       'table_id':self.id
                                       })
    
        



    def _po_count(self):
        for a in self:
            a.po_count = len(a.po_ids)
            
       
               
    def action_view_po(self):
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        action['context'] = dict(self._context or {})
        action['domain'] = [('id','in',self.po_ids.ids)]
        return action
    
    
    def _so_count(self):
        for a in self:
            a.so_count = len(a.so_ids)
            
               
    def action_view_so(self):
        action = self.env.ref('sale.action_quotations_with_onboarding').read()[0]
        action['context'] = dict(self._context or {})
        action['domain'] = [('id','in',self.so_ids.ids)]
        return action
        
    def create_po(self):
        orders = {}
        for l in self.forecast_order_line_ids.filtered(lambda x : x.to_order>0):
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
                    
                    'table_id':self.id
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
        

    def populate(self):
        
        domain = (safe_eval(self.template_id.product_filter_domain,  {}) if self.template_id.product_filter_domain else [])
        products = self.env['product.product'].search(domain)
        pr = []
        for p in products:
                product_id = p.id
                values = {
                              'product_id':product_id,
                              
                              
                              }
#
                pr.append([0,False,values])
        self.forecast_order_line_ids = pr
        self.state='in_progress'
        
    def action_view_lines(self):
        self.ensure_one()
       
        action = {
            'res_model': 'order_table.forecast_order_line',
            'type': 'ir.actions.act_window',
        }
        
        
        action.update({
                'name': _("Lines for  %s") % self.display_name,
                'domain': [('id','in',self.forecast_order_line_ids.ids)],
                'view_mode': 'tree'
            })
        return action
    
       
class ForecastOrderLine(models.Model):
    _name = 'order_table.forecast_order_line'
    _description = 'Order helper Line '
    
    sequence = fields.Integer('Sequence')  
    forecast_order_id = fields.Many2one('order_table.forecast_order','Order')
    product_id = fields.Many2one('product.product','Product')
    product_tmpl_id = fields.Many2one('product.template','Template',related="product_id.product_tmpl_id",store=True,readonly=True)
    product_brand_id = fields.Many2one('common.product.brand.ept', string="Brand",related="product_tmpl_id.product_brand_id",store=True,
                                       help='Select a brand for this product.')
    qvc_code = fields.Char('QVC Code',related="product_tmpl_id.qvc_code",store=True)
    qvc_extension_code = fields.Char('QVC Code',related="product_id.qvc_extension_code",store=True)
    milor_code = fields.Char('Milor Code',related="product_tmpl_id.milor_code",store=True)
    default_code = fields.Char('Default Code',related="product_tmpl_id.default_code",store=True)
    milor_extension_code = fields.Char('Extension Code',related="product_id.milor_extension_code",store=True)
    vendor_sku = fields.Char('Vendor Sku',compute="_compute_vendor_sku",store=True)
    supplier_ids= fields.Many2many('res.partner',compute="_get_vendors")
    barcode = fields.Char('EAN',related="product_id.barcode",store=True)
    
    base_pricelist_id = fields.Many2one('product.pricelist','Base Pricelist',related="forecast_order_id.template_id.base_pricelist_id")
    currency_base = fields.Many2one('res.currency',related="base_pricelist_id.currency_id")
    base_price = fields.Monetary('Base Price',currency_field="currency_base",compute="_get_prices",store=True)
    
    internal_pricelist_id = fields.Many2one('product.pricelist','Internal Pricelist',related="forecast_order_id.template_id.internal_pricelist_id")
    currency_internal=fields.Many2one('res.currency',related="internal_pricelist_id.currency_id")
    internal_price = fields.Monetary('Internal Price',currency_field="currency_internal",compute="_get_prices",store=True)
    
    promo_pricelist_id = fields.Many2one('product.pricelist','Promo Pricelist',related="forecast_order_id.template_id.promo_pricelist_id")
    currency_promo = fields.Many2one('res.currency',related="promo_pricelist_id.currency_id")
    promo_price = fields.Monetary('Promo Price',currency_field="currency_promo",compute="_get_prices",store=True)
    has_promo = fields.Boolean('Has Promo',compute="_total_sold",store=True)
    
    stock = fields.Float('Milor SPA Stock',compute="_stock",readonly=True,store=True)
    other_stock = fields.Float('Milor Group Stock',compute="_stock",readonly=True,store=True)
    
    to_order = fields.Integer('To Order',readonly=False,default=0)
    to_send = fields.Integer('To Send Milor Group',readonly=False,default=0)
    
    currency_sold = fields.Many2one('res.currency','Promo Pricelist',compute="_total_sold",store=True)
    total_sold = fields.Monetary('Total Sold',compute="_total_sold",currency_field="currency_sold",store=True)
    qty_sold = fields.Float('Qty Sold',compute="_total_sold",store=True)
    
    incoming_qty = fields.Float('In Order',compute="_stock")
    
    image_1024 = fields.Image("Image 1024", related="product_id.image_1024", max_width=1024, max_height=1024)
    image_512 = fields.Image("Image 512", related="product_id.image_512", max_width=512, max_height=512)
    image_256 = fields.Image("Image 256", related="product_id.image_256", max_width=256, max_height=256)
    image_128 = fields.Image("Image 128", related="product_id.image_128", max_width=128, max_height=128)
    partner_id = fields.Many2one('res.partner',string='Vendor',compute="_get_vendors",store=True,readonly=False)
    
    
    
    def _get_prices(self):
        for a in self:
            base_price = a.base_pricelist_id.price_get(a.product_id.id,1).get(a.base_pricelist_id.id,0)
            internal_price = a.internal_pricelist_id.price_get(a.product_id.id,1).get(a.internal_pricelist_id.id,0)
            promo_price = a.promo_pricelist_id.price_get(a.product_id.id,1).get(a.promo_pricelist_id.id,0)
            a.write({
                     'base_price':base_price,
                     'internal_price':internal_price,
                     'promo_price':promo_price
                     })
    
    @api.depends('milor_code','milor_extension_code')
    def _compute_vendor_sku(self):
        for a in self:
            a.vendor_sku = "%s %s" % (a.default_code,a.milor_code)
            
            
    def _get_vendors(self):
        for a in self:
            sinfo = self.env['product.supplierinfo'].search([('name','=',a.partner_id.id),('company_id','=',a.forecast_order_id.template_id.company_id.id),'|',('product_id','=',a.product_id.id),('product_tmpl_id','=',a.product_tmpl_id.id)])
            if sinfo:
                a.supplier_ids = sinfo.mapped('partner_id').ids
                a.partner_id = sinfo[0].id
            else:
                a.supplier_ids = False
                a.partner_id = False
                
    def _stock(self):
        for a in self:
            stock_location_id = a.forecast_order_id.template_id.stock_location_id
            stock_quant = self.sudo().env['stock.quant'].search([('product_id','=',a.product_id.id),('location_id','=',stock_location_id.id)],limit=1)
            
            
            other_location_id = a.forecast_order_id.template_id.other_location_id
            other_quant = self.sudo().env['stock.quant'].search([('product_id','=',a.product_id.id),('location_id','=',other_location_id.id)],limit=1)
            a.write({
                     'stock':stock_quant.quantity if stock_quant else 0,
                     'other_stock':other_quant.quantity if other_quant else 0,
                     'incoming_qty':a.product_id.incoming_qty
                     })
    
    
    def _get_sold_domain(self):
        self.ensure_one()
        report_sale_domain = self.forecast_order_id.template_id.report_sale_domain if self.forecast_order_id.template_id.report_sale_domain else []
        domain_sold = (safe_eval(report_sale_domain,  {}) if report_sale_domain else []) + [('date','<=',self.forecast_order_id.date_order_end),('date','>=',self.forecast_order_id.date_order_start)]
        return domain_sold
    
    def _get_other_sold_domain(self):
        self.ensure_one()
        report_sale_domain_other = self.forecast_order_id.template_id.report_sale_domain_other if self.forecast_order_id.template_id.report_sale_domain_other else []
        domain_sold = (safe_eval(report_sale_domain_other,  {}) if report_sale_domain_other else []) + [('date','<=',self.forecast_order_id.date_order_end),('date','>=',self.forecast_order_id.date_order_start)]
        return domain_sold
    
    @api.depends('forecast_order_id.date_order_end','forecast_order_id.date_order_start') 
    def _total_sold(self):
        
        for a in self:
            product_uom_qty = 0
            price_subtotal = 0
            currency_sold = a.base_pricelist_id.currency_id.id
            has_promo = False
            filter_domain = a._get_other_sold_domain()
            domain = filter_domain
            report_sale = self.sudo().env['sale.report'].search(domain)
            if report_sale:
                product_uom_qty = sum(report_sale.mapped('product_uom_qty'))
                price_subtotal = sum(report_sale.mapped('price_subtotal'))
                currency_sold = report_sale[0].pricelist_id.id
                has_promo = any(report_sale.mapped('pricelist_id').filtered(lambda pricelist_id: pricelist_id.id == a.promo_pricelist_id.id))
            
            a.write({
                         'currency_sold':currency_sold,
                         'total_sold':price_subtotal,
                         'qty_sold':product_uom_qty,
                         'has_promo':has_promo
                         })
            
    def action_view_other_sold(self):
        self.ensure_one()
       
        action = {
            'res_model': 'sale.report',
            'type': 'ir.actions.act_window',
        }
        
        
        action.update({
                'name': _("Statistic for  %s") % self.product_id.display_name,
                'domain': self._get_other_sold_domain(),
                'view_mode': 'dashboard,pivot,graph,tree'
            })
        return action
        
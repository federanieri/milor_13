# -*- coding: utf-8 -*-
# © 2019 SayDigital s.r.l.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

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




class ProcurementGroup(models.Model):
    _inherit = "procurement.group"
    
    purchase_order_id = fields.Many2one('purchase.order','PO')

            
class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    
    parent_po_id = fields.Many2one('purchase.order','Parent PO',copy=False)
    service_po = fields.Boolean('Service/Component PO',copy=False)
    next_po_id= fields.Many2one('purchase.order','Next PO',copy=False)
    po_product_tmpl_id = fields.Many2one('product.template',string="Template Product",store=True,compute="_get_po_product_template_id")
    supplier_info_sequence_ids = fields.One2many("product.supplier_info_sequence",related="po_product_tmpl_id.template_supplier_info_sequence_ids",string="Supplier Sequence")
    supplier_info_sequence_count = fields.Integer('Count Sequence',compute="_supplier_info_count")
    child_po_ids = fields.One2many('purchase.order','parent_po_id',string="Child Purchase Orders")
    child_po_count = fields.Integer('Count Child',compute="_supplier_info_count")
    product_of_service_id = fields.Many2one('product.product',related="order_line.product_of_service_id")
    
    
    
    def button_confirm(self):
        res = super(PurchaseOrder,self).button_confirm()
        for a in self:
            for p in a.child_po_ids:
                p.button_confirm()
        return res
    
    
    def message_delivery(self,message):
        for a in self:
            body = ("Delivery from %s"%self.env.user.partner_id.name) + message
            a.message_post(body=body, subject="Message from %s "%self.env.user.partner_id.name,message_type='comment',subtype='mail.mt_comment',partner_ids=[a.partner_id.id]+a.message_partner_ids.ids)
            if a.next_po_id:
                a.next_po_id.message_post(body=body, subject="Message from %s "%self.env.user.partner_id.name,message_type='comment',subtype='mail.mt_comment',partner_ids=[a.next_po_id.partner_id.id]+a.next_po_id.message_partner_ids.ids)
    
    def _supplier_info_count(self):
        for a in self:
            a.supplier_info_sequence_count = len(a.supplier_info_sequence_ids)
            a.child_po_count = len(a.child_po_ids)
            
    def action_launch_sequence(self):
        self.ensure_one()
        self.order_line.filtered(lambda l: not l.display_type and l.product_id.type == 'product')._manage_sequence_po()
            
            
    @api.depends('order_line.product_id')
    def _get_po_product_template_id(self):
        for a in self:
            po_product_tmpl_id = False
            for o in a.order_line.filtered(lambda l: not l.display_type and l.product_id.type == 'product'):
                if not po_product_tmpl_id:
                    po_product_tmpl_id = o.product_id.product_tmpl_id.id
                elif po_product_tmpl_id != o.product_id.product_tmpl_id.id:
                    po_product_tmpl_id = False
            a.po_product_tmpl_id = po_product_tmpl_id     
                
    def _create_picking(self):
        # consider the send to other vendor
        return super(PurchaseOrder,self.filtered(lambda a : not a.service_po))._create_picking()
            
class PurchaseLine(models.Model):
    _inherit = "purchase.order.line"
    
    product_of_service_id = fields.Many2one('product.product',string="Product of Service")
    
    def _compute_qty_received_method(self):
        super(PurchaseLine, self)._compute_qty_received_method()
        for line in self.filtered(lambda l: not l.display_type):
            if line.order_id.service_po and line.order_id.dest_address_id:
                line.qty_received_method = 'manual'
    
    #### TO DO MOVE FROM HERE
    @api.model
    def create(self,values):
        res = super(PurchaseLine,self).create(values)
        
        return res    
    
    def _manage_sequence_po(self,supplier_info_sequence_ids=False):
        for res in self:
            product_id = res.product_id
            parent_id = res.order_id
            if not supplier_info_sequence_ids and product_id.supplier_info_sequence_ids:
                supplier_info_sequence_ids = product_id.supplier_info_sequence_ids
            elif not supplier_info_sequence_ids and product_id.template_supplier_info_sequence_ids:
                supplier_info_sequence_ids = product_id.template_supplier_info_sequence_ids
            if supplier_info_sequence_ids:
                if not parent_id.group_id:
                    parent_id.group_id = self.env["procurement.group"].create(
                                                                           {
                                                                            'purchase_order_id':parent_id.id,
                                                                            'name':parent_id.name
                                                                           }
                                                                           )
            
                supplier_info_sequence_ids.create_po(parent_id,res.product_uom_qty,product_id)
            

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    template_supplier_info_sequence_ids = fields.One2many("product.supplier_info_sequence","product_tmpl_id",string="Supplier Sequence")
            
class ProductProduct(models.Model):
    _inherit = "product.product"
    
    supplier_info_sequence_ids = fields.One2many("product.supplier_info_sequence","product_id",string="Supplier Sequence")
    
    def _compute_bom_price(self, bom, boms_to_recompute=False):
        self.ensure_one()
        price = super(ProductProduct,self)._compute_bom_price(bom, boms_to_recompute)
        supplier_info_sequence_ids = self.supplier_info_sequence_ids or self.product_tmpl_id.template_supplier_info_sequence_ids or bom.supplier_info_sequence_ids
        for s in supplier_info_sequence_ids:
            company_id = self.env.user.company_id
            partner = s.partner_id
            # _select_seller is used if the supplier have different price depending
            # the quantities ordered.
            seller = s
            product_id = s.purchase_product_id
            
            taxes = s.purchase_product_id.supplier_taxes_id
            fpos = partner.property_account_position_id
            taxes_id = fpos.map_tax(taxes, s.purchase_product_id, seller.partner_id) if fpos else taxes
            if taxes_id:
                taxes_id = taxes_id.filtered(lambda x: x.company_id.id == company_id.id)
    
            price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price,  s.purchase_product_id.supplier_taxes_id, taxes_id, company_id) if seller else 0.0
            if price_unit and seller and s.currency_id and seller.currency_id != self.env.company.currency_id:
                price_unit = seller.currency_id._convert(
                    price_unit, po.currency_id, po.company_id, po.date_order or fields.Date.today())
            price += price_unit
            
        return price
    
class StockMove(models.Model):
    _inherit = 'stock.move' 
    
    raw_delivery_partner_id = fields.Many2one('res.partner',string="Raw Send To")
    
    def _key_assign_picking(self):
        self.ensure_one()
        return self.group_id, self.location_id, self.location_dest_id, self.picking_type_id, self.partner_id

class StockRule(models.Model):
    _inherit = 'stock.rule'
    
    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        res = super(StockRule,self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        raw_delivery_partner_id = values['move_dest_ids'].raw_delivery_partner_id if 'move_dest_ids' in values else False
        if raw_delivery_partner_id:
            res['partner_id'] =raw_delivery_partner_id.id
            res['raw_delivery_partner_id'] =raw_delivery_partner_id.id
        return res
    
class MrpProduction(models.Model):
    _inherit  = 'mrp.production'
    
    def _get_move_raw_values(self, bom_line, line_data):
        data = super(MrpProduction,self)._get_move_raw_values(bom_line,line_data)
        if bom_line.delivery_to_partner_id:
            data['raw_delivery_partner_id']= bom_line.delivery_to_partner_id.id
        return data
    
class MrpBomLine(models.Model):
    _inherit="mrp.bom.line" 
    
    delivery_to_partner_id = fields.Many2one('res.partner',string="Send To")
   
class MrpBom(models.Model):
    _inherit="mrp.bom" 
    
    supplier_info_sequence_ids = fields.One2many("product.supplier_info_sequence","bom_id",string="Supplier Sequence")


class ProductPOSequence(models.Model):
    _name="product.supplier_info_sequence"
    
    bom_id = fields.Many2one('mrp.bom',string="Bom")
    sequence = fields.Integer('Sequence')
    product_id = fields.Many2one('product.product',string="Variant")
    product_tmpl_id = fields.Many2one('product.template',string="Product Template",required=True)
    purchase_product_id = fields.Many2one('product.product',string="Component Product",required=True)
    
    partner_id = fields.Many2one('res.partner',string="Vendor",required=True)
    price = fields.Monetary('Price')
    product_uom = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        help="This comes from the product form.")
    currency_id = fields.Many2one(
        'res.currency', 'Currency',
        default=lambda self: self.env.company.currency_id.id,
        required=True)
    qty_per_unit = fields.Float(
        'Quantity per Unit', default=1.0, required=True,
        )
    send_to_other_vendor = fields.Boolean('Send To Other Vendor',default=True)
    dest_address_id = fields.Many2one('res.partner',string="Dest Vendor")
    
    @api.constrains('product_id')
    def _onchange_product_id(self):
        for a in self:
            if a.product_id and a.product_id.product_tmpl_id:
                if a.product_tmpl_id.id != a.product_id.product_tmpl_id.id:
                    a.product_tmpl_id = a.product_id.product_tmpl_id.id
    
    @api.constrains('bom_id')
    def _onchange_bom_id(self):
        for a in self:
            if a.bom_id.product_id:
                a.product_id = a.bom_id.product_id.id
            elif a.bom_id.product_tmpl_id:
                a.product_tmpl_id = a.bom_id.product_tmpl_id.id
    
    @api.onchange('purchase_product_id')
    def onchange_purchase_product_id(self):
        for a in self:
            if a.purchase_product_id:
                a.product_uom = a.purchase_product_id.uom_po_id.id
    
    
    
    @api.onchange('partner_id')
    def onchange_vendor(self):
        for a in self:
            if a.send_to_other_vendor:
                a.dest_address_id = a.partner_id.id
            else:
                a.dest_address_id = self.env.user.company_id.partner_id.id
    
    @api.onchange('send_to_other_vendor')
    def onchange_send_to_other_vendor(self):
        for a in self:
            if not a.send_to_other_vendor:
                a.dest_address_id = False
            
    def create_po(self,parent_id,product_qty,original_product_id):
        old_po = False
        for i in range(len(self)):
            actual = self[i]
            next = self[i+1] if (i+1) < len(self) else parent_id
            dest_address_id = actual.dest_address_id.id if actual.send_to_other_vendor else False
            
            po = self.env['purchase.order'].search(actual._make_po_get_domain(parent_id,dest_address_id))
            if not po:
                po = self.env['purchase.order'].create(actual._prepare_purchase_order(parent_id,dest_address_id,i+1))
            if old_po and not old_po.next_po_id:
                old_po.next_po_id = po.id
            old_po = po
            self.env['purchase.order.line'].create(actual._prepare_purchase_order_line(product_qty,po,original_product_id))
            notes = ''
            if po.product_of_service_id and not po.notes:
                notes += po.product_of_service_id.description 
                notes += po.product_id.description   
            po.notes =  notes 
        old_po.next_po_id = parent_id.id
        
    def _make_po_get_domain(self,parent_id,dest_address_id):
        self.ensure_one()
        group_id = parent_id.group_id.id
    
        domain = (
                ('partner_id', '=', self.partner_id.id),
                ('state', '=', 'draft'),
                ('picking_type_id', '=', parent_id.picking_type_id.id),
                ('company_id', '=', parent_id.company_id.id),
                ('dest_address_id', '=', dest_address_id),
                ('service_po','!=',False)
            )
        if group_id:
                domain += (('group_id', '=', group_id),)
        return domain
        
    def _prepare_purchase_order(self, parent_id,dest_address_id,i=0):
        self.ensure_one()
        fpos = self.env['account.fiscal.position'].with_context(force_company=parent_id.company_id.id).get_fiscal_position(self.partner_id.id)
        group_id = parent_id.group_id.id
        return {
            'name':"%s/%d"%(parent_id.name,i),
            'partner_id': self.partner_id.id,
            'user_id': False,
            'picking_type_id': parent_id.picking_type_id.id,
            'company_id': parent_id.company_id.id,
            'currency_id': self.partner_id.with_context(force_company=parent_id.company_id.id).property_purchase_currency_id.id or parent_id.company_id.currency_id.id,
            'dest_address_id': dest_address_id,
            'origin': parent_id.origin if parent_id.origin else parent_id.name,
            'payment_term_id': self.partner_id.with_context(force_company=parent_id.company_id.id).property_supplier_payment_term_id.id,
            'date_order': parent_id.date_order,
            'fiscal_position_id': fpos,
            'group_id': group_id,
            'parent_po_id':parent_id.id,
            'service_po':True
            
        }
    
    def _prepare_purchase_order_line(self,  product_qty, po,original_product_id):
        self.ensure_one()
        company_id = po.company_id
        partner = self.partner_id
        # _select_seller is used if the supplier have different price depending
        # the quantities ordered.
        seller = self
        product_id = self.purchase_product_id
        
        taxes = self.purchase_product_id.supplier_taxes_id
        fpos = po.fiscal_position_id
        taxes_id = fpos.map_tax(taxes, self.purchase_product_id, seller.partner_id) if fpos else taxes
        if taxes_id:
            taxes_id = taxes_id.filtered(lambda x: x.company_id.id == company_id.id)

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price,  self.purchase_product_id.supplier_taxes_id, taxes_id, company_id) if seller else 0.0
        if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, po.currency_id, po.company_id, po.date_order or fields.Date.today())

        product_lang = self.purchase_product_id.with_prefetch().with_context(
            lang=partner.lang,
            partner_id=partner.id,
        )
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        date_planned = po.date_order

        return {
            'name': name,
            'product_qty': product_qty * self.qty_per_unit,
            'product_id': self.purchase_product_id.id,
            'product_of_service_id':original_product_id.id,
            'product_uom': self.product_uom.id,
            'price_unit': price_unit,
            'date_planned': date_planned,
            'taxes_id': [(6, 0, taxes_id.ids)],
            'order_id': po.id
        }
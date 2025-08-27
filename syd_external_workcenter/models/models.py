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


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    service_po = fields.Boolean('Service/Component PO')
    
class PurchaseLine(models.Model):
    _inherit = "purchase.order.line"
    
    product_of_service_id = fields.Many2one('product.product',string="Product of Service")
    
class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'
    
    is_external = fields.Boolean('Is External')
    vendor_id = fields.Many2one('res.partner',string="Vendor")

class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'
   
    is_external = fields.Boolean('Is External',related="workcenter_id.is_external")
    service_product_id = fields.Many2one('product.product',domain=[('type','=','service')],string="Service Product")
    vendor_id = fields.Many2one('res.partner',string="Vendor",related="workcenter_id.vendor_id")
    product_uom = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        related='service_product_id.uom_po_id',
        help="This comes from the product form.")
    product_qty = fields.Float(
        'Quantity per Unit')
    price = fields.Monetary(
        'Price', default=0.0, digits='Product Price',
        required=True, help="The price to purchase a product")
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company.id, index=1)
    currency_id = fields.Many2one(
        'res.currency', 'Currency',
        default=lambda self: self.env.company.currency_id.id,
        required=True)
    
class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'
    
    purchase_order_line_id = fields.Many2one('purchase.order.line',string="Purchase Order Line")
    purchase_order_id = fields.Many2one('purchase.order',string="Purchase Order",related="purchase_order_line_id.order_id")
    
    def create(self,values):
        res = super(MrpWorkorder,self).create(values)
        if res.workcenter_id.is_external:
            res._create_po_line()
        return res
    
    def _get_po(self):
        partner = self.workcenter_id.vendor_id
        procurement_group_id = self.production_id.procurement_group_id
        return self.env['purchase.order'].search([('partner_id','=',partner.id),('group_id','=',procurement_group_id.id),('state','=','draft')],limit=1)
    
    def _create_po_line(self):
        partner = self.workcenter_id.vendor_id
        currency = self.operation_id.currency_id
        company_id = self.operation_id.company_id
        procurement_group_id = self.production_id.procurement_group_id
        fpos = self.env['account.fiscal.position'].with_context(force_company=company_id.id).get_fiscal_position(partner.id)
        po = self._get_po()
        if not po:
            po_vals =  {
                'partner_id': partner.id,
                'user_id': False,
                'company_id': company_id.id,
                'currency_id': currency.id,
                'fiscal_position_id': fpos,
                'service_po':True,
                'origin': procurement_group_id.name,
                'payment_term_id': partner.with_context(force_company=company_id.id).property_supplier_payment_term_id.id,
                'group_id':procurement_group_id.id
            }
            po = self.env['purchase.order'].create(po_vals)
        qty_order = self.operation_id.product_qty * self.qty_production
        uom = self.operation_id.product_uom
        price_unit = self.operation_id.price
        product_id = self.operation_id.service_product_id
        fpos = po.fiscal_position_id
        
        taxes = product_id.supplier_taxes_id
        taxes_id = fpos.map_tax(taxes, product_id, partner.name) if fpos else taxes
        po_line = {
            'name': product_id.name,
            'product_qty': qty_order,
            'product_id': product_id.id,
            'product_uom': uom.id,
            'price_unit': price_unit,
            'taxes_id': [(6, 0, taxes_id.ids)],
            'order_id': po.id,
            'date_planned':self.date_planned_start or fields.Date.today(),
            'product_of_service_id':self.production_id.product_id.id
        }
        self.purchase_order_line_id = self.env['purchase.order.line'].create(po_line).id
        
class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    
    def _compute_bom_price(self, bom, boms_to_recompute=False):
        self.ensure_one()
        if not bom:
            return 0
        if not boms_to_recompute:
            boms_to_recompute = []
        total = 0
        for opt in bom.routing_id.operation_ids:
            if opt.workcenter_id.is_external:
                total += opt.price
            else:
                duration_expected = (
                    opt.workcenter_id.time_start +
                    opt.workcenter_id.time_stop +
                    opt.time_cycle)
                total += (duration_expected / 60) * opt.workcenter_id.costs_hour
        for line in bom.bom_line_ids:
            if line._skip_bom_line(self):
                continue

            # Compute recursive if line has `child_line_ids`
            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                child_total = line.product_id._compute_bom_price(line.child_bom_id, boms_to_recompute=boms_to_recompute)
                total += line.product_id.uom_id._compute_price(child_total, line.product_uom_id) * line.product_qty
            else:
                total += line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * line.product_qty
        return bom.product_uom_id._compute_price(total / bom.product_qty, self.uom_id)
    


    
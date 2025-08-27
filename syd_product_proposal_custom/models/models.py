# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.misc import get_lang
from odoo import api, fields, models, _
from werkzeug.urls import url_encode
from collections import defaultdict
from odoo.tools.safe_eval import safe_eval
import datetime
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context

class saleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    was_replenished = fields.Boolean(string='Was Replenish?', default=False)
    qty_to_replenish = fields.Integer(string='Quantity to replenish', default=0)

    def write(self, vals):
        if bool(self.was_replenished) and 'product_uom_qty' in vals and self.order_id.state == 'sale': 
            self.qty_to_replenish = vals.get('product_uom_qty') - self.product_uom_qty
        return super(saleOrderLine, self).write(vals)


class saleOrder(models.Model):
    _inherit = 'sale.order'
    
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """
            Set values to 0 and was_replenished to False when duplicating the sale.order
        """
        res = super(saleOrder, self).copy(default)
        for ol in res.order_line:
            ol.write({'was_replenished':False,'qty_to_replenish':0}) 
        return res
    
    def _check_forecasted_replenishment(self, product_id=False):               
        sorders = self.env['sale.order'].search([('order_line.was_replenished', '=', True),('state','=','sale'),('order_line.product_id.id','=',product_id),('company_id', '=', self.company_id.id)])
        return True if any([self.env['purchase.order'].search([('origin','ilike','%'+so.name+'%'),('state','=','draft'),('company_id', '=', self.company_id.id)]) for so in sorders]) else False
                            
    def from_sale_replenishment(self):
        for so in self.order_line:
            is_forecasted = False
            if not bool(self.env.ref('stock.route_warehouse0_mto').id in so.product_id.route_ids.ids) and (not bool(so.was_replenished) or (bool(so.was_replenished) and so.qty_to_replenish != 0)):
                product_id = so.product_id
                quantity = so.product_id.virtual_available 
                
                if bool(quantity >= 0) or bool(so.product_id.nbr_reordering_rules):
                    pass
                else:
                    """
                        _check_forecasted_replenishment: Check first if a sale.order with that product has been replenished (was_replenished = True)
                        and has been written in the PO. In that case, just replenish the quantity of the product.
                    """
                    if not bool(so.was_replenished):
                        is_forecasted = self._check_forecasted_replenishment(product_id.id)
                                        
                    if not bool(is_forecasted):
                        quantity = so.qty_to_replenish if so.qty_to_replenish != 0 else abs(quantity)
                    else:
                        quantity = so.product_uom_qty
                        
                    company = so.company_id or self.env.company
                    warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
                    date_planned = datetime.datetime.now()
                    product_uom_id = so.product_id.uom_id
                    uom_reference = product_id.uom_id
                    quantity = product_uom_id._compute_quantity(quantity, uom_reference)
                    
                    try:
                        self.env['procurement.group'].with_context(clean_context(self.env.context)).run([
                            self.env['procurement.group'].Procurement(
                                product_id,
                                quantity,
                                uom_reference,
                                warehouse_id.lot_stock_id,  # Location
                                _("Replenishment"),  # Name
                                _("Replenishment"),  # Origin
                                warehouse_id.company_id,
                                self._prepare_run_values(product_id,company,warehouse_id,date_planned)  # Values
                            )
                        ])
                        so.was_replenished = True
                        so.qty_to_replenish = 0
                    except UserError as error:
                        raise UserError(error)
        
        # Message post with all the purchase orders related to the replenishment:
        pos = self.env['purchase.order'].search([('origin','ilike','%'+self.name+'%'),('date_deadline_from','=',self.date_deadline_from),('date_deadline_to','=',self.date_deadline_to),('state','=','draft'),('company_id', '=', self.company_id.id)])
        if bool(pos): 
            subject = _('Purchase Orders has been created or updated: ') + "<br/>".join('<a href=# data-oe-model=purchase.order data-oe-id=%d>%s</a>' % (po.id, po.name) for po in pos)
            self.message_post(body=subject)
            

    def _prepare_run_values(self, product_id=False, company=False, warehouse_id=False, date_planned=False):
        replenishment = self.env['procurement.group'].create({
            'partner_id': product_id.with_context(force_company=company.id).responsible_id.partner_id.id,
        })

        values = {
            'warehouse_id': warehouse_id,
            'date_planned': date_planned,
            'group_id': replenishment
        }
        return values

class purchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    origin_sale_id = fields.Many2one('sale.order',string='Origin Sale Order')
    date_deadline_from = fields.Date('Date Deadline From')
    date_deadline_to = fields.Date('Date Deadline To')
    
    @api.model
    def create(self, vals):
        res = super(purchaseOrder, self).create(vals)
        if ('sale_order' in self._context):
            order = self.env['sale.order'].browse(self._context.get('sale_order'))
            res.update({'origin_sale_id':self._context.get('sale_order'),'date_deadline_from':order.date_deadline_from, 'date_deadline_to':order.date_deadline_to})
            if 'origin' in res:
                name = order.name
                if name not in res.origin:
                    res.origin = res.origin + ', ' + name
            else:
                res.origin = order.names
        ctx = dict(self.env.context)
        ctx.pop('default_product_id', None)
        ctx.pop('sale_order', None)

        self = self.with_context(ctx)
        return res
    
    def write(self, vals):
        if ('sale_order' in self._context):
            order = self.env['sale.order'].browse(self._context.get('sale_order'))
            name = order.name
            if name not in vals['origin']:
                vals['origin'] = vals['origin'] + ', ' + name
        return super(purchaseOrder, self).write(vals)

class purchaseOrderLines(models.Model):
    _inherit = 'purchase.order.line'
    
    @api.model
    def create(self, vals):
        res = super(purchaseOrderLines, self).create(vals)
        seller = res.product_id._select_seller(
                partner_id=res.partner_id, quantity=res.product_qty,
                date=res.order_id.date_order and res.order_id.date_order.date(), uom_id=res.product_uom)
        res.date_planned = res._get_date_planned(seller)
        return res
    
    
class stockMoves(models.Model):
    _inherit = 'stock.move'

    @api.model
    def create(self, vals):
        if 'date_deadline_from' in self._context and 'date_deadline_to' in self._context and self._context.get('date_deadline_from') and self._context.get('date_deadline_to'):
            vals.update({'date_deadline_from':self._context.get('date_deadline_from'),'date_deadline_to':self._context.get('date_deadline_to')})
        res = super(stockMoves, self).create(vals)
        return res

class stockRule(models.Model):
    _inherit = 'stock.rule'
    
    def _make_po_get_domain(self, company_id, values, partner):
        domain = super(stockRule, self)._make_po_get_domain(company_id, values, partner)
        if domain and 'sale_order' in self._context:
            order = self.env['sale.order'].browse(self._context.get('sale_order'))
            if order.date_deadline_from and order.date_deadline_to:
                domain = tuple(list(domain) + [('date_deadline_from', '=', order.date_deadline_from),('date_deadline_to', '=', order.date_deadline_to),('origin_sale_id','=', order.id)])
            else:
                domain = tuple(list(domain) + [('date_deadline_from', '=', False),('date_deadline_to', '=', False)])
        return domain

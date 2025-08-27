# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import groupby as groupbyelem
from operator import itemgetter
    
class ReturnOrderSheet(models.Model):
    _name = 'return.order.sheet'
    _description = "Return Order Sheet"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin'] 
    _rec_name = 'number'
    
    
    from_web = fields.Boolean('From Web',default=False)
    return_type = fields.Selection(
        [('replacement', 'Replacement'),
         ('refund', 'Refund'),
         ('repair', 'Repair')],
        track_visibility='onchange',
        required=True,
        default="refund",
        translate=True
    )
    picking_type_id = fields.Many2one("stock.picking.type",string="Picking Type")
    picking_type_code = fields.Selection([
        ('incoming', 'Vendors'),
        ('outgoing', 'Customers'),
        ('internal', 'Internal')], related='picking_type_id.code',
        readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', related='picking_type_id.company_id',
        readonly=True, store=True, index=True)
    warehouse_id = fields.Many2one('stock.warehouse',string="Warehouse",related='picking_type_id.warehouse_id')
    
    delivery_method = fields.Char('Delivery Method')
    document_number = fields.Char('Document')
    document_date = fields.Char('Document Date')
    number = fields.Char(
        string="Number"
    )
    state = fields.Selection(
        [('draft','Draft'),
          ('sent','Sent'),
         ('confirm','Confirmed'),
         ('done','Done'),
         ('cancel','Cancelled')],
        track_visibility='onchange',
        default='draft',
        copy=False, 
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Customer",
        track_visibility='onchange',
        
    )
    partner_invoice_id = fields.Many2one(
        'res.partner', string='Invoice Address',required=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)
    partner_shipping_id = fields.Many2one(
        'res.partner', string='Delivery Address', required=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)


    return_order_line_ids = fields.One2many('return.order.line','return_order_sheet_id',string="Lines")
    notes = fields.Text('Notes')
    location_id = fields.Many2one('stock.location',string="Location Origin",related='picking_type_id.default_location_src_id')
    location_dest_id = fields.Many2one('stock.location',string="Location Dest",related='picking_type_id.default_location_dest_id')
    procurement_id = fields.Many2one('procurement.group','Procurement Group')
    picking_ids = fields.One2many('stock.picking',related="procurement_id.picking_ids")
    picking_count = fields.Integer(
        compute="_picking_count",
    )
    pricelist_id = fields.Many2one('product.pricelist',related="partner_id.property_product_pricelist",store=True)
    currency_id = fields.Many2one('res.currency',related="pricelist_id.currency_id")
    reasons = fields.Many2one('return.order.reason', string="Reasons", related='return_order_line_ids.reason', store=True)
    salesman_partner_id = fields.Many2one('res.partner')
    sale_order_count = fields.Integer(compute='_compute_sale_order_count', string='Sale Order Count')
    sale_order_ids = fields.One2many('sale.order', 'crma_origin_id', 'Sales Order')
    doc_cliente = fields.Char(string="Documento Cliente")

    def _compute_sale_order_count(self):
        for so in self:
            so.sale_order_ids = self.env['sale.order'].search([('crma_origin_id','=',self.id)])
            so.sale_order_count = len(so.sale_order_ids)
    
    def return_cancel(self):
        for rec in self:
            rec.state = 'cancel'
            for picking in self.env['stock.picking'].search([('origin','ilike',rec.number)]):
                picking.action_cancel()

    def _picking_count(self):
        for rec in self:
            rec.picking_count = len(self.env['stock.picking'].search([('origin','ilike',rec.number)],order='create_date desc'))
    
    
    @api.onchange('partner_id')
    def _onchange_set_agent(self):
        if bool(self.partner_id) and bool(self.partner_id.salesman_partner_id):
            self.salesman_partner_id = self.partner_id.salesman_partner_id
    
    @api.onchange('partner_id')
    def _onchange_set_addresses(self):
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'partner_invoice_id': False,
            })
            return

        addresses = self.partner_id.address_get(['delivery', 'invoice'])
        self.partner_invoice_id = addresses.get('invoice',None)
        self.partner_shipping_id = addresses.get('delivery',None)
        

    @api.onchange('picking_type_id')
    def onchange_picking_type(self):
        if self.picking_type_id:
            location_id = False
            location_dest_id = False
            warehouse_id = self.picking_type_id.warehouse_id
            if self.picking_type_id.default_location_src_id:
                location_id = self.picking_type_id.default_location_src_id.id
            if self.picking_type_id.default_location_dest_id:
                location_dest_id = self.picking_type_id.default_location_dest_id.id
            if not self.location_id:
                self.location_id = location_id
            if not self.location_dest_id:
                self.location_dest_id = location_dest_id
            self.warehouse_id = warehouse_id.id
    
    def action_match_lines(self):
        for rec in self:
             rec.return_order_line_ids._match_lines()
    
    def action_sent(self):
        for rec in self:
            rec.state = 'sent'
            
    def action_confirm(self):
        for rec in self:
            rec.state = 'confirm'
            rec.with_context(type=rec.return_type).create_picking()
            if rec.return_type == 'repair':
                rec.create_sale_order()
            
    def reset_draft(self):
        for rec in self:
            rec.state = 'draft'
            
    def action_done(self):
        for rec in self:
            rec.state = 'done'
    
    @api.model
    def create(self, vals):
        number = self.env['ir.sequence'].next_by_code('return.rma_sheet.seq')
        vals.update({
            'number': number,
            })
        res = super(ReturnOrderSheet, self).create(vals)
        res.write({
                   'picking_type_id':self.env.user.company_id.commercial_return_p_type_id.id
                   })
        return res
    
    def create_sale_order(self):
        vals = {
                'partner_id':self.partner_id.id,
                'partner_invoice_id':self.partner_invoice_id.id,
                'partner_shipping_id':self.partner_shipping_id.id,
                'salesman_partner_id':self.salesman_partner_id.id,
                'origin':self.number,
                'crma_origin_id':self.id,
                'repair_so':True,
                'order_line':[(0,0,line._get_orderlines_values()) for line in self.return_order_line_ids]
                }
        sale_order = self.env['sale.order'].create(vals)
    
    def create_picking(self):
        vals = {
                'location_id':self.location_id.id,
                'location_dest_id':self.location_dest_id.id,
                'partner_id':self.partner_id.id,
                'picking_type_id':self.picking_type_id.id,
                'origin':self.number,
                'move_lines':[(0,0,line._get_move_values()) for line in self.return_order_line_ids]
                }
        picking_id = self.env['stock.picking'].create(vals)
        if not self.env.context.get('type',None) == 'repair':
            return self.action_view_delivery()
    
    def _get_group_id(self): 
        self.ensure_one()
        
        if self.procurement_id:
            return self.procurement_id
        
        self.procurement_id  =  self.env['procurement.group'].create({
                                                         'name':self.number,
                                                         'partner_id':self.partner_id.id,
                                                         'crma_id':self.id
                                                         }).id
            
        return self.procurement_id 
        
    def _get_pickings_created(self):
        picking_ids = self.env['stock.picking'].search([('origin','ilike',self.number)],order='create_date desc')
        return picking_ids
    
    
    def action_view_delivery(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        picking_ids = self._get_pickings_created()

        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
        if len(picking_ids) > 1:
            action['domain'] = [('id', 'in', picking_ids.ids)]
        elif picking_ids:
            action['res_id'] = picking_ids.id
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
        return action
    
    def action_view_saleorder(self):
        self.ensure_one()
        sale_order_ids = self.sale_order_ids
        action = {
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
        }
        if len(sale_order_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': sale_order_ids.id,
            })
        else:
            action.update({
                'name': _("Sources Sale Orders of %s", self.name),
                'domain': [('id', 'in', sale_order_ids.ids)],
                'view_mode': 'tree,form',
            })
        return action    
            
    def action_wizard_transfer(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        vals = {
                'partner_id':self.partner_id.id,
                'wizard_transfer_line_ids':[(0,0,a._get_wizard_values()) for a in self.return_order_line_ids],
                
                'crma_id':self.id
                
                }
        res_id = self.env["syd_inventory_extended.wizard_transfer"].create(vals)
        action = self.env.ref('syd_inventory_extended.action_picking_creation_helper').read()[0]
        
        action['res_id'] = res_id.id
        return action
    
    def unlink(self):
        for order in self:
            if order.state in ('done'):
                raise UserError(_("You can not remove a Return Order if it's done."))
            picking_ids = order._get_pickings_created()
            if picking_ids:
                picking_ids.unlink()
            if order.sale_order_ids:
                order.sale_order_ids.unlink()
        return super(ReturnOrderSheet, self).unlink()

    def translation_return_type(self):
        return_type = False
        if 'template_preview_lang' in self._context:
            return_type = [opt[1] for opt in self.with_context(lang=self._context.get('template_preview_lang')).fields_get()['return_type']['selection'] if opt[0] == self.return_type]
        else:
            return_type = [opt[1] for opt in self.with_context(lang=self._context.get('lang')).fields_get()['return_type']['selection'] if opt[0] == self.return_type]
        return return_type[0] if return_type else ''

class ReturnOrderLine(models.Model):
    _name = 'return.order.line'
    _rec_name = 'partner_id'
    _order = 'id desc'
#    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    _description = "Multiple Return Order"
    
    return_order_sheet_id = fields.Many2one('return.order.sheet',string="Sheet")
    product_code = fields.Char('Product Code')
    sale_code = fields.Char('Order Reference')
    partner_id = fields.Many2one(
        'res.partner',
        related="return_order_sheet_id.partner_id",store=True
        
    )
    commercial_partner_id = fields.Many2one(
        'res.partner',
        related="partner_id.commercial_partner_id",store=True
        
    )
    origin_saleorder_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        related="origin_sale_order_line_id.order_id",
        store=True
        
    )
    origin_sale_order_line_id = fields.Many2one('sale.order.line',string="Origin Sale Order Line",domain="[('order_id.partner_id','=',commercial_partner_id),('product_id','=',product_id)]",store=True)
    invoice_ids = fields.Many2many('account.move',compute="_get_invoice_ids", string="Invoices")
    origin_invoice_id = fields.Many2one('account.move',domain="[('id','in',invoice_ids)]",string="Invoice",store=True)
    invoice_code = fields.Char('Invoice code')
    date_invoice = fields.Date(string='Invoice/Bill Date')
    pricelist_id = fields.Many2one('product.pricelist',related="return_order_sheet_id.pricelist_id",store=True)
    currency_id = fields.Many2one('res.currency',related="return_order_sheet_id.currency_id",store=True)
    price = fields.Monetary('Price')
    
    
    
    
    
 
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    uom_id = fields.Many2one(
        'uom.uom',
        string='Uom',
        compute='compute_set_uom',
       
    )
    product_id = fields.Many2one(
        'product.product',
        string="Return Product",
        track_visibility='onchange',
        
        
    )
    quantity = fields.Float(
        string="Return Quantity",
        required = True,
        default=1.0,
        track_visibility='onchange',
    )
    reason = fields.Many2one('return.order.reason',string="Reason",track_visibility='onchange')
    specify_reason = fields.Text(string='Other reason')
    
    saleorderline_id = fields.Many2one(
        'sale.order.line',
        string="Sale Order Line",
        domain="[('order_id','=',saleorder_id)]"
    )
    
    
    
    
    
    #WIP
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', related="uom_id")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True)
    scheduled_date = fields.Datetime(compute='_compute_qty_at_date_scheduled', default=fields.Datetime.now, store=False) 
    display_qty_widget = fields.Boolean(compute='_compute_qty_to_deliver')
    virtual_available_at_date = fields.Float('Forecast Quantity',related='product_id.virtual_available')
    free_qty_today  = fields.Float('Free To Use Quantity', related='product_id.free_qty')
    rif_interno_cliente = fields.Char(string="Riferimento Interno Cliente")


    @api.model
    def _default_warehouse_id(self):
        company = self.env.company.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids
    
    

    def _compute_qty_to_deliver(self):
        
        for return_order_line in self: 
            return_order_line.display_qty_widget = True  
    
    @api.depends('scheduled_date')
    def _compute_qty_at_date_scheduled(self):
        for proposal_order_line in self:
            proposal_order_line.scheduled_date = fields.Datetime.now()   
    #WIP   
    
    
    
    
    
    
    
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',related="return_order_sheet_id.warehouse_id")

    def _compute_qty_to_deliver(self):
        for proposal_order_line in self:
            proposal_order_line.display_qty_widget = True  
    
    @api.depends('scheduled_date')
    def _compute_qty_at_date_scheduled(self):
        for proposal_order_line in self:
            proposal_order_line.scheduled_date = fields.Datetime.now()   
        
    
    
    
    
    @api.constrains('origin_sale_order_line_id','product_id','pricelist_id')
    def _price(self):
        for a in self:
            if a.origin_sale_order_line_id:
                a.price = a.origin_sale_order_line_id.price_unit
            elif a.pricelist_id:
                res = {}
                res = a.pricelist_id.price_get(a.product_id.id,1)
                a.price = res.get(a.pricelist_id.id,0)
    
    def _match_lines(self):
        for a in self:
            sale_order_line_id = self.env['sale.order.line'].search([('order_id.partner_id','=',a.commercial_partner_id),('product_id','=',a.product_id)],limit=1)
            a.sale_order_line_id = sale_order_line_id.id
            origin_invoice_id = self.env['account.move'].search([('id','in',a.invoice_ids.ids)],limit=1)
            a.origin_invoice_id = origin_invoice_id.id
        
    @api.depends('origin_saleorder_id','product_id')
    def _get_invoice_ids(self):
        for so in self:
            if bool(so.product_id) and bool(so.return_order_sheet_id.partner_id.commercial_partner_id):
                so.invoice_ids = so.env['account.move'].search([('invoice_line_ids.product_id','=',so.product_id.id),('partner_id','=',so.return_order_sheet_id.partner_id.commercial_partner_id.id),('state','=','posted')]).ids
            elif bool(so.origin_sale_order_line_id):
                so.invoice_ids = so.origin_saleorder_id.invoice_ids.ids
            else:
                so.invoice_ids = False
            
    @api.constrains('origin_invoice_id')
    @api.onchange('origin_invoice_id')
    def _invoice_code(self):
        for a in self:
            a.invoice_code = a.origin_invoice_id.name
            a.date_invoice = a.origin_invoice_id.invoice_date
    
    @api.depends('product_id')
    def compute_set_uom(self):
        for rec in self:
            rec.uom_id = rec.product_id.uom_id.id
    
    
    def _get_move_values(self):
        self.ensure_one()
        vals = {
                'location_id':self.return_order_sheet_id.location_id.id,
                'location_dest_id':self.return_order_sheet_id.location_dest_id.id,
                'product_uom_qty':self.quantity,
                'product_uom':self.uom_id.id,
                'product_id':self.product_id.id,
                'origin':self.return_order_sheet_id.number,
                'group_id':self.return_order_sheet_id._get_group_id().id,
                'name':self.product_id.name,
                'origin_ro_line_id':self.id
                }
        return vals
    
        
    def _get_orderlines_values(self):
        self.ensure_one()
        categ_id = self.env.ref('syd_commercial_return.repair_product_category')
        repair_service = self.env['product.product'].search([('type','=','service'),('categ_id','=',categ_id.id)], limit=1)
        vals = {
                'repair_product_for':self.product_id.id,
                'product_id':repair_service.id or False,
                'product_uom_qty':self.quantity,
                'product_uom':repair_service.uom_id.id or False,
                }
        return vals
    
#     def _prepare_procurement_values(self):
#         """ Prepare specific key for moves or other components that will be created from a stock rule
#         comming from a sale order line. This method could be override in order to add other custom key that could
#         be used in move/po creation.
#         """
#         return {
#                     'group_id': self.return_order_sheet_id._get_group_id(), 
#                     'date_planned': fields.Datetime.now(), 
#                     'warehouse_id': self.return_order_sheet_id.warehouse_id, 
#                     'partner_id': self.return_order_sheet_id.partner_id.id, 
#                     'company_id': self.return_order_sheet_id.company_id 
#                     }
    
#     def _action_launch_procurement(self):
#         """
#         Launch procurement group run method with required/custom fields genrated by a
#         sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
#         depending on the sale order line product rule.
#         """
#         procurements = []
#         for line in self:
#             values = line._prepare_procurement_values()
#             procurements.append(self.env['procurement.group'].Procurement(
#                 line.product_id, line.quantity, line.uom_id,
#                 self.return_order_sheet_id.location_dest_id,
#                 line.product_id.name, line.return_order_sheet_id.number, line.return_order_sheet_id.company_id, values))
#         if procurements:
#             self.env['procurement.group'].run(procurements)
#         return True
#     
#     

        
    def _get_wizard_values(self):
        self.ensure_one()
        vals = {
                'product_uom_qty':self.quantity,
                'product_uom':self.uom_id.id,
                'product_id':self.product_id.id,
                'sale_order_line_id':self.origin_sale_order_line_id.id
                }               
        return vals    

class StockMove(models.Model):
    _inherit = 'stock.move'
    
    origin_ro_line_id = fields.Many2one('return.order.line','Return Order Line')
    origin_ro_id = fields.Many2one('return.order.sheet',related="origin_ro_line_id.return_order_sheet_id",store=True,string='Origin Return Order')
    total_grouped_ro_ids= fields.Many2many('return.order.sheet',relation="ro_order_stock_move")
    total_grouped_ro_line_ids= fields.Many2many('return.order.line',relation="ro_order_line_stock_move")
    
    
    # for merged move save the origin sale and origin sale line (for example PacK) 
    def _merge_moves_fields(self):
        vals = super(StockMove,self)._merge_moves_fields()
        vals['total_grouped_ro_ids']= [(4, m.id) for m in self.mapped('origin_ro_id')]
        vals['total_grouped_ro_line_ids']= [(4, m.id) for m in self.mapped('origin_ro_line_id')]
        return vals
        
        
    def _prepare_procurement_values(self):
        values = super(StockMove,self)._prepare_procurement_values()
        values['origin_ro_line_id']= self.origin_ro_line_id.id
       
        return values
    
class StockRule(models.Model):
    """ A rule describe what a procurement should do; produce, buy, move, ... """
    _inherit = 'stock.rule'

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        val = super(StockRule,self)._push_prepare_move_copy_values(move_to_copy,new_date)  
        val['origin_ro_line_id']=move_to_copy.origin_ro_line_id.id
        return val
    
    def _get_custom_move_fields(self):
        values = super(StockRule,self)._get_custom_move_fields()
        values+= ['origin_ro_line_id']
        return values        
    
        
class WizardTransfer(models.TransientModel):
    _inherit = "syd_inventory_extended.wizard_transfer"
    
    crma_id = fields.Many2one('return.order.sheet',string="Commercial return")
    
    def _get_group_id(self):
        if self.crma_id :
            if self.crma_id.procurement_id:
                return self.crma_id.procurement_id
            else :
                self.crma_id.procurement_id = self.env['procurement.group'].create({
                                                         'name':self.crma_id.number,
                                                         'partner_id':self.partner_id.id,
                                                         'crma_id':self.crma_id.id
                                                         
                                                         }).id
            return self.crma_id.procurement_id
        return super(WizardTransfer,self)._get_group_id()
    
    def _get_origin(self): 
        if self.crma_id:
            return self.crma_id.number
        return super(WizardTransfer,self)._get_origin()
    
    def create_picking(self):
        res = super(WizardTransfer,self).create_picking()
        if self.crma_id:
            picking_ids = self.env['stock.picking'].search([('origin','ilike',self.crma_id.number)],order='create_date desc')
            res['domain'] = [('id', 'in', picking_ids.ids)]
        return res
    
    
    def _get_pickings_created(self):
        picking_ids = super(WizardTransfer,self)._get_pickings_created()
        if self.rma_id:
            picking_ids = self.env['stock.picking'].search([('origin','ilike',self.crma_id.number)],order='create_date desc')
        return picking_ids

class Company(models.Model):
    _inherit = 'res.company'
    
    commercial_return_p_type_id = fields.Many2one("stock.picking.type",string="Commercial Picking Type")


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'
    
    picking_ids = fields.One2many('stock.picking','group_id')
    crma_id = fields.Many2one('return.order.sheet',string="Commercial return")

class Partner(models.Model):
    _inherit = 'res.partner'
    
    has_commercial_return = fields.Boolean('Has Commercial Return',default=False)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def name_get(self):
        res = []
        for rec in self:
            name = rec.name
            if rec.invoice_date:
                name = rec.name + " / Invoice Date: " + str(rec.invoice_date)
            res.append((rec.id, name))
        return res
    
# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ReturnOrder(models.Model):
    _name = 'return.order'
    _rec_name = 'number'
    _order = 'id desc'
#    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin'] #odoo11
    _description = "Return Order"
    
    
    origin = fields.Selection(
        [('form','Form'),
         ('web','web')],
        required = True,
        default='web'
    )
    email= fields.Char('Email')
    product_code = fields.Char('Product Code')
    order_code= fields.Char('Order Code')
    
    
    delivery_method = fields.Char('Delivery Method')
    document_number = fields.Char('Document')
    document_date = fields.Char('Document Date')
    
    
    number = fields.Char(
        string="Number"
    )
    state = fields.Selection(
        [('draft','Draft'),
         ('confirm','Confirmed'),
         ('approve','Approved'),
         ('return','Return'),
         ('refund','Refund'),
         ('cancel','Cancelled')],
        track_visibility='onchange',
        default='draft',
        copy=False, 
    )
    return_type = fields.Selection(
        [('replacement','Replacement'),
         ('refund','Refund')],
        track_visibility='onchange',
        required = True 
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Customer",
        track_visibility='onchange',
        
    )
    saleorder_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        track_visibility='onchange',
        
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
    reason = fields.Text(
        string="Reason",
        required = True,
        track_visibility='onchange',
    )
    saleorderline_id = fields.Many2one(
        'sale.order.line',
        string="Sale Order Line",
        domain="[('order_id','=',saleorder_id)]"
    )
    delivery_id = fields.Many2one(
        'stock.picking',
        string="Customers Delivery Order",
        track_visibility='onchange',
        domain="[('origin_sale_id','=',saleorder_id),('picking_type_code','=','outgoing'),('state','=','done')]"
    )
    incoming_delivery_id = fields.Many2one(
        'stock.picking',
        domain ="[('origin_sale_id','=',saleorder_id),('picking_type_code', '=', 'incoming')]",
        string="Return Delivery Order",
    )
    replacement_delivery_id = fields.Many2one(
        'stock.picking',
        domain ="[('origin_sale_id','=',saleorder_id),('picking_type_code', '=', 'outgoing')]",
        string="Replacement Delivery Order",
    )
    confirm_by = fields.Many2one(
        'res.users',
        string='Confirmed By',
        readonly = True,
        track_visibility='onchange',
    )
    confirm_date = fields.Date(
        string='Confirmed Date',
        readonly = True,
        track_visibility='onchange',
    )
    approve_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly = True,
        track_visibility='onchange'
    )
    approve_date = fields.Date(
        string='Aproved Date',
        readonly = True,
        track_visibility='onchange'
    )
    create_date = fields.Date(
        string='Create Date',
        default=fields.date.today(),
        required = True
    )
    return_by = fields.Many2one(
        'res.users',
        string='Return By',
        readonly = True,
        track_visibility='onchange',
    )
    return_date = fields.Date(
        string='Return Date',
        readonly = True,
        track_visibility='onchange'
    )
   
    uom_id = fields.Many2one(
        'uom.uom',
        string='Uom',
        compute='compute_set_uom',
       
    )
    company_id = fields.Many2one(
        'res.company',
        required = True,
        default=lambda self: self.env.user.company_id,
        string='Company',
    )
    salesperson_id = fields.Many2one(
        'res.users',
        string='Assigned To',
        tracking=True
    )
    team_id = fields.Many2one(
        'crm.team',
        string='Sales Team',
    )
    notes = fields.Text(
        'Add comment'
    )
    order_partner_id = fields.Many2one(
        'res.partner',
        string = "Order Customer",
        related = 'saleorder_id.partner_id',
        readonly = True,
    )
    incoming_delivery_count = fields.Integer(
        compute="_incoming_delivery_count",
    )
    outgoing_delivery_count = fields.Integer(
        compute="_outgoing_delivery_count",
    )
    
    
    
    
    @api.onchange('saleorderline_id')
    @api.constrains('saleorderline_id')
    def _set_product(self):
        for a in self:
            a.product_id = a.saleorderline_id.product_id.id
            
            
#    @api.multi odoo13
    @api.depends()
    def _incoming_delivery_count(self):
        for rec in self:
            if rec.saleorder_id:
                rec.incoming_delivery_count = self.env['stock.picking'].search_count([
                    ('origin_sale_id','=',rec.saleorder_id.id),
                    ('picking_type_code', '=', 'incoming')
                ])
            else:
                rec.incoming_delivery_count = 0
           
    
#    @api.multi odoo13
    def action_view_incoming_delivery(self):
        for rec in self:
            if rec.saleorder_id:
                delivery_id = self.env['stock.picking'].search([
                            ('origin_sale_id','=',rec.saleorder_id.id),
                            ('picking_type_code', '=', 'incoming') 
                ])
            else:
                delivery_id = self.env['stock.picking']
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]
        result['domain'] = [('id', 'in', delivery_id.ids)]
        return result
    
    def _outgoing_delivery_count(self):
        for rec in self:
            if rec.saleorder_id:
                rec.outgoing_delivery_count = self.env['stock.picking'].search_count([
                    ('origin_sale_id', '=', rec.saleorder_id.id),
                    ('picking_type_code', '=', 'outgoing')
                ])
            else:
                rec.outgoing_delivery_count = 0
            

#    @api.multi odoo13
    def action_view_outgoing_delivery(self):
        for rec in self:
            if rec.saleorder_id:
                delivery_id = self.env['stock.picking'].search([
                            ('origin_sale_id', '=', rec.saleorder_id.id),
                            ('picking_type_code', '=', 'outgoing') 
                ])
            else:
                delivery_id = self.env['stock.picking']
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]
        result['domain'] = [('id', 'in', delivery_id.ids)]
        return result
    
    @api.model
    def create(self, vals):
        number = self.env['ir.sequence'].next_by_code('return.rma.seq')
        vals.update({
            'number': number,
            'return_by': self.env.user.id,
            'return_date' : fields.Date.today(),
            })
        res = super(ReturnOrder, self).create(vals)
        return res
        
#    @api.multi odoo13
    def return_confirm(self):
        for rec in self:
            rec.confirm_by = self.env.user.id
            rec.confirm_date = fields.Date.today()
            rec._match_order_line()
            if rec.saleorder_id and rec.saleorderline_id:
                rec.state = 'confirm'
                rec._generate_transfer()
            else:
                raise ValidationError(_('Miss some information'))
      
      
    def _match_order_line(self):
        for a in self:
            if not a.partner_id:
                if a.email:
                  partner_id = self.env['res.partner'].search([('email','=',a.email)],limit=1)
                  if partner_id :
                      a.partner_id = partner_id.id
                  else:
                      raise ValidationError(_('No Contact with this email'))
            if not a.saleorder_id:
                if a.order_code:
                    order_id = self.env['sale.order'].search(['|',('name','=',a.order_code),('origin','=',a.order_code)],limit=1)
                    if order_id :
                        a.saleorder_id = order_id.id
                    
            if not a.product_id:
                if a.product_code :
                    product_id = self.env['product.product'].search(['|',('default_code','=',a.product_code),('barcode','=',a.product_code)],limit=1)
                    if product_id and a.saleorder_id:
                        saleorderline_id = self.env['sale.order.line'].search([('product_id','=',product_id.id),('order_id','=',a.saleorder_id.id)],limit=1)
                        if saleorderline_id :
                            a.saleorderline_id = saleorderline_id.id
                        else:
                            raise ValidationError('The product %s is not in the order %s' % (product_id.name,a.saleorder_id.name))
                    elif product_id and a.partner_id:
                        saleorderline_id = self.env['sale.order.line'].search([('product_id','=',product_id.id),('order_id.state','=','sale'),('order_id.partner_id','child_of', [a.partner_id.commercial_partner_id.id])],order='create_date desc',limit=1)
                        if saleorderline_id :
                            a.saleorder_id = saleorderline_id.order_id.id
                            a.saleorderline_id = saleorderline_id.id
                

            if not a.product_id:
                raise ValidationError('No Product code specified')
            if not a.saleorder_id:
                raise ValidationError('No Order found')
#    @api.multi odoo13
    def return_done(self):
        for rec in self:
            rec.state = 'return'
    

    def refund_done(self):
        for rec in self:
            rec.state = 'refund'
        
#    @api.multi odoo13
    def return_cancel(self):
        for rec in self:
            rec.state = 'cancel'
            
#    @api.multi odoo13
    def reset_draft(self):
        for rec in self:
            rec.state = 'draft'
            
#    @api.multi odoo13
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('You can not delete this record.'))
        return super(ReturnOrder, self).unlink()


    @api.constrains('saleorder_id')
    def _compute_picking_delivery(self):
        for rec in self:
            delivery_ids = self.env['stock.picking'].search(
                                        [('origin_sale_id','=',rec.saleorder_id.id),('picking_type_code','=','outgoing')] 
                                    )
            if len(delivery_ids)==1:
                rec.delivery_id = delivery_ids.id
    

    
    
    def _generate_transfer(self):
        
        if(self.delivery_id):
            wizard = self.env['stock.return.picking'].create({ 'picking_id':self.delivery_id.id})
            
            wizard._onchange_picking_id()
            wizard.location_id = self.env.company.default_return_location_id.id
            for ret in wizard.product_return_moves:
                if ret.product_id.id == self.product_id.id:
                    ret.quantity = self.quantity
                else:
                    ret.unlink()
            
            picking_id, pick_type_id = wizard._create_returns()
            picking = self.env['stock.picking'].browse(picking_id)
            picking.origin += ',' + self.number
            self.incoming_delivery_id = picking.id
            
            return True
        else:
            raise ValidationError(_('No confirmed outgoing transfer'))
        
#    @api.multi odoo13
    def return_approve(self):
        for rec in self:
            rec.approve_by = self.env.user.id
            rec.approve_date = fields.Date.today()
            rec.state = 'approve'
            
            
            
#    @api.multi odoo13
    @api.depends('product_id')
    def compute_set_uom(self):
        for rec in self:
            rec.uom_id = rec.product_id.uom_id.id
        
    def _get_wizard_values(self):
        self.ensure_one()
        vals = {
                'product_uom_qty':self.quantity,
                'product_uom':self.uom_id.id,
                'product_id':self.product_id.id,
                'sale_order_line_id':self.saleorderline_id.id
                }               
        return vals    
            
    def action_wizard_transfer(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        vals = {
                'partner_id':self.saleorder_id.partner_shipping_id.id,
                'wizard_transfer_line_ids':[(0,0,self._get_wizard_values())],
                'sale_order_id':self.saleorder_id.id,
                'rma_id':self.id
                
                }
        res_id = self.env["syd_inventory_extended.wizard_transfer"].create(vals)
        action = self.env.ref('syd_inventory_extended.action_picking_creation_helper').read()[0]
        
        action['res_id'] = res_id.id
        return action
    
 
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    rma_id = fields.Many2one('return.order',string="Return")


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'
    
    
    rma_id = fields.Many2one('return.order',string="Return")
    
        
class WizardTransfer(models.TransientModel):
    _inherit = "syd_inventory_extended.wizard_transfer"
    
    rma_id = fields.Many2one('return.order',string="Return")
    
    def _get_group_id(self):
        if self.rma_id:
            return self.env['procurement.group'].create({
                                                         'name':self.rma_id.number,
                                                         'partner_id':self.partner_id.id,
                                                         'rma_id':self.rma_id.id
                                                         
                                                         })
        return super(WizardTransfer,self)._get_group_id()
    
    def _get_origin(self):
        if self.rma_id:
            return self.rma_id.number
        return  super(WizardTransfer,self)._get_origin()
    
    def create_picking(self):
        res = super(WizardTransfer,self).create_picking()
        if self.rma_id:
            picking_ids = self.env['stock.picking'].search([('origin','ilike',self.rma_id.number)],order='create_date desc')
            for p in picking_ids:
                if not p.rma_id and self.rma_id:
                    p.rma_id = self.rma_id
            res['domain'] = [('id', 'in', picking_ids.ids)]
        return res
    
    
    def _get_pickings_created(self):
        picking_ids = super(WizardTransfer,self)._get_pickings_created()
        if self.rma_id:
            picking_ids = self.env['stock.picking'].search([('origin','ilike',self.rma_id.number)],order='create_date desc')
        return picking_ids
        
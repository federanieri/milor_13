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

class WizardTransferLine(models.TransientModel):
    _name = "syd_inventory_extended.wizard_transfer_line"
    _description = 'Wizard Transfer Line'
    
    product_id = fields.Many2one('product.product',string="Product",required=True)
    product_uom_qty = fields.Float(
        'Quantity',
        digits='Product Unit of Measure',
        default=0.0, required=True,
        help="This is the quantity of products from an inventory "
             "point of view. For moves in the state 'done', this is the "
             "quantity of products that were actually moved. For other "
             "moves, this is the quantity of product that is planned to "
             "be moved. Lowering this quantity does not generate a "
             "backorder. Changing this quantity on assigned moves affects "
             "the product reservation, and should be done with care.")
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_qty = fields.Float(
        'Real Quantity', compute='_compute_product_qty', readonly=True,
        digits=0, store=True, compute_sudo=True,
        help='Quantity in the default UoM of the product')
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product Template',
        related='product_id.product_tmpl_id', readonly=False,
        help="Technical: used in views")
    wizard_transfer_id = fields.Many2one("syd_inventory_extended.wizard_transfer",string="Wizard Transfer")
    sale_order_line_id = fields.Many2one('sale.order.line',string="Sale Order Line")
    purchase_order_line_id = fields.Many2one('purchase.order.line',string="Purchase Order Line")
    scrap_id = fields.Many2one("stock.scrap",string="Scrap Order")
    
    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_product_qty(self):
        # DLE FIXME: `stock/tests/test_move2.py`
        # `product_qty` is a STORED compute field which depends on the context :/
        # I asked SLE to change this, task: 2041971
        # In the mean time I cheat and force the rouding to half-up, it seems it works for all tests.
        rounding_method = 'HALF-UP'
        for move in self:
            move.product_qty = move.product_uom._compute_quantity(
                move.product_uom_qty, move.product_id.uom_id, rounding_method=rounding_method)
    
    def _get_move_values(self):
        self.ensure_one()
        vals = {
                'location_id':self.wizard_transfer_id.location_id.id,
                'location_dest_id':self.wizard_transfer_id.location_dest_id.id,
                'product_uom_qty':self.product_uom_qty,
                'product_uom':self.product_uom.id,
                'product_id':self.product_id.id,
                'sale_line_id':self.sale_order_line_id.id,
                'purchase_line_id':self.purchase_order_line_id.id,
                'origin_sale_line_id':self.sale_order_line_id.id,
                'origin_purchase_line_id':self.purchase_order_line_id.id,
                'origin':self.wizard_transfer_id._get_origin(),
                'group_id':self.wizard_transfer_id._get_group_id().id,
                'name':self.product_id.name
                }
        return vals
            
    def _prepare_procurement_values(self):
        """ Prepare specific key for moves or other components that will be created from a stock rule
        comming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        if self.sale_order_line_id:
            return self.sale_order_line_id._prepare_procurement_values(self.wizard_transfer_id._get_group_id())
        elif self.purchase_order_line_id:
            return {
                    'group_id': self.wizard_transfer_id._get_group_id(), 
                    'purchase_line_id': self.purchase_order_line_id.id, 
                    'date_planned': fields.Datetime.now(), 
                    'warehouse_id': self.wizard_transfer_id.warehouse_id, 
                    'partner_id': self.wizard_transfer_id.partner_id.id, 
                    'company_id': self.wizard_transfer_id.company_id, 
                    'origin_purchase_line_id': self.purchase_order_line_id.id
                    }
        return {
                    'group_id': self.wizard_transfer_id._get_group_id(), 
                    'date_planned': fields.Datetime.now(), 
                    'warehouse_id': self.wizard_transfer_id.warehouse_id, 
                    'partner_id': self.wizard_transfer_id.partner_id.id, 
                    'company_id': self.wizard_transfer_id.company_id, 
                    }
    
    def _action_launch_procurement(self):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        procurements = []
        for line in self:
            values = line._prepare_procurement_values()
            procurements.append(self.env['procurement.group'].Procurement(
                line.product_id, line.product_qty, line.product_uom,
                self.wizard_transfer_id.location_dest_id,
                line.product_id.name, line.wizard_transfer_id._get_origin(), line.wizard_transfer_id.company_id, values))
        if procurements:
            self.env['procurement.group'].run(procurements)
        return True
    
class WizardTransfer(models.TransientModel):
    _name = "syd_inventory_extended.wizard_transfer"
    _description = 'Wizard Transfer'
       
    location_id = fields.Many2one('stock.location',string="Location Origin")
    location_dest_id = fields.Many2one('stock.location',string="Location Dest")
    wizard_transfer_line_ids = fields.One2many("syd_inventory_extended.wizard_transfer_line","wizard_transfer_id",string="Transfer Lines")
    sale_order_id = fields.Many2one('sale.order',string="Sale Order")
    purchase_order_id = fields.Many2one('purchase.order',string="Purchase Order")
    
    partner_id = fields.Many2one('res.partner',string="Address")
    picking_type_id = fields.Many2one("stock.picking.type",string="Picking Type")
    picking_type_code = fields.Selection([
        ('incoming', 'Vendors'),
        ('outgoing', 'Customers'),
        ('internal', 'Internal')], related='picking_type_id.code',
        readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', related='picking_type_id.company_id',
        readonly=True, store=True, index=True)
    warehouse_id = fields.Many2one('stock.warehouse',string="Warehouse")
    
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
                
    def _get_group_id(self): 
        group_id = self.env['procurement.group'].search([('partner_id','=',self.partner_id.id),('name','=',self._get_origin())],limit=1)
        if group_id:
            return group_id                                  
        else:
            return self.env['procurement.group'].create({
                                                     'partner_id':self.partner_id.id,
                                                     'name':self._get_origin()
                                                     })
    
    def _get_origin(self):
        origin = ''
        if self.sale_order_id:
            origin += self.sale_order_id.display_name
        if self.purchase_order_id:
            if origin:
                origin+= ","
            origin += self.purchase_order_id.name
        for a in self.wizard_transfer_line_ids:
            if a.scrap_id:
                if origin:
                    origin+= ","
                origin += a.scrap_id.name
        if not origin:
            origin = 'MT-%s'%(self.create_date)
        return origin
    
    
    def create_picking(self):
        picking_id = False
        if self.picking_type_code=='outgoing':
            self.wizard_transfer_line_ids._action_launch_procurement()
        else:
            vals = {
                    'location_id':self.location_id.id,
                    'location_dest_id':self.location_dest_id.id,
                    'partner_id':self.partner_id.id,
                    'picking_type_id':self.picking_type_id.id,
                    'origin':self._get_origin(),
                    'move_lines':[(0,0,line._get_move_values()) for line in self.wizard_transfer_line_ids]
                    }
            picking_id = self.env['stock.picking'].create(vals)
        return self.action_view_delivery()
        
    def _get_pickings_created(self):
        picking_ids = self.env['stock.picking'].search([('origin','ilike',self._get_origin())],order='create_date desc')
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


class StockQuant(models.Model):
    _inherit = "stock.quant"
    
    def action_wizard_transfer(self):
        location_id = False
        for a in self:
            location_id = a.location_id.id if location_id == False or location_id == a.location_id.id else False
        if location_id == False:
            raise ValidationError(_('These items must have the same location'))
            
        vals = {
                'location_id':location_id,
                'wizard_transfer_line_ids':[(0,0,line._get_wizard_values()) for line in self]
                }
        res_id = self.env["syd_inventory_extended.wizard_transfer"].create(vals)
        action = self.env.ref('syd_inventory_extended.action_picking_creation_helper').read()[0]
        action['res_id'] = res_id.id
        return action
    
    def _get_wizard_values(self):
        self.ensure_one()
        vals = {
                'product_uom_qty':self.quantity,
                'product_uom':self.product_uom_id.id,
                'product_id':self.product_id.id
                }
        return vals


class Scrap(models.Model):
    _inherit = "stock.scrap"
    
    def action_wizard_transfer(self):
        partner_id = False
        purchase_order_id = False
        for a in self:
            partner_id = a.origin_purchase_id.partner_id.id if partner_id == False or partner_id == a.origin_purchase_id.partner_id.id else False
            purchase_order_id = a.origin_purchase_id.id if purchase_order_id == False or purchase_order_id == a.origin_purchase_id.id else False
        if partner_id == False:
            raise ValidationError(_('This scrap item do not have the same vendor'))
            
        vals = {
                'partner_id':partner_id,
                'wizard_transfer_line_ids':[(0,0,line._get_wizard_values()) for line in self],
                'purchase_order_id':purchase_order_id
                }
        res_id = self.env["syd_inventory_extended.wizard_transfer"].create(vals)
        action = self.env.ref('syd_inventory_extended.action_picking_creation_helper').read()[0]
        action['res_id'] = res_id.id
        return action
    
    def _get_wizard_values(self):
        self.ensure_one()
        vals = {
                'product_uom_qty':self.scrap_qty,
                'product_uom':self.product_uom_id.id,
                'product_id':self.product_id.id,
                'sale_order_line_id':self.origin_sale_line_id.id,
                'purchase_order_line_id':self.origin_purchase_line_id.id,
                'scrap_id':self.id
                
                }
        return vals
    
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    def _get_wizard_values(self):
        self.ensure_one()
        vals = {
                'product_uom_qty':self.product_uom_qty,
                'product_uom':self.product_uom.id,
                'product_id':self.product_id.id,
                'sale_order_line_id':self.id
                }
        return vals
    
class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    def action_wizard_transfer(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        vals = {
                'partner_id':self.partner_shipping_id.id,
                'wizard_transfer_line_ids':[(0,0,line._get_wizard_values()) for line in self.order_line.filtered(lambda self: self.display_type == False)],
                'sale_order_id':self.id
                }
        res_id = self.env["syd_inventory_extended.wizard_transfer"].create(vals)
        action = self.env.ref('syd_inventory_extended.action_picking_creation_helper').read()[0]
        
        action['res_id'] = res_id.id
        return action
    

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    
    def _get_wizard_values(self):
        self.ensure_one()
        vals = {
                'product_uom_qty':self.product_uom_qty,
                'product_uom':self.product_uom.id,
                'product_id':self.product_id.id,
                'purchase_order_line_id':self.id
                }
        return vals
    
class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    def action_wizard_transfer(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        vals = {
                'partner_id':self.partner_id.id,
                'wizard_transfer_line_ids':[(0,0,line._get_wizard_values()) for line in self.order_line.filtered(lambda self: self.display_type == False)],
                'purchase_order_id':self.id,
                
                }
        res_id = self.env["syd_inventory_extended.wizard_transfer"].create(vals)
        action = self.env.ref('syd_inventory_extended.action_picking_creation_helper').read()[0]
        
        action['res_id'] = res_id.id
        return action
        
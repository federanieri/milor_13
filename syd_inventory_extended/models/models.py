# -*- coding: utf-8 -*-
# © 2019 SayDigital s.r.l.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from itertools import chain 

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_repr
from odoo.tools.misc import get_lang
from itertools import groupby
from odoo.tools.safe_eval import safe_eval
import logging
_logger = logging.getLogger(__name__)

class ProcurementGroup(models.Model):
    _inherit = "procurement.group"
     
    def _get_orderpoint_domain(self, company_id=False):
        domain = super(ProcurementGroup,self)._get_orderpoint_domain(company_id)
        domain += (('auto_orderpoint', '=', True),)
        return domain
    
class Orderpoint(models.Model):
    """ Defines Minimum stock rules. """
    _inherit = "stock.warehouse.orderpoint"
    
    
    auto_orderpoint = fields.Boolean('Auto orderpoint',default=True)
    
class ResPartner(models.Model):
    _inherit = "res.partner"


    no_group_picking = fields.Boolean('Nessun Raggruppamento nei Picking',default=False,help='Non permettere mai raggruppamento per movimentazioni di questo Partner')

class Product(models.Model):
    _inherit = "product.product"
    
    def _get_domain_locations(self):
            company_id = self.env.company.id
            domain_quant_loc, domain_move_in_loc, domain_move_out_loc = super(Product,self)._get_domain_locations()
            domain_quant_loc = [('location_id.company_id', '=', company_id), ('location_id.usage', 'in', ['internal', 'transit']),('location_id.stock_ubication','=',True)]
            return domain_quant_loc, domain_move_in_loc, domain_move_out_loc
            

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    
    free_qty = fields.Float(
        'Free To Use Quantity ', compute='_compute_free_quantities', 
        digits='Product Unit of Measure', compute_sudo=False,
        help="Forecast quantity (computed as Quantity On Hand "
             "- reserved quantity)\n"
             "In a context with a single Stock Location, this includes "
             "goods stored in this location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods stored in the Stock Location of this Warehouse, or any "
             "of its children.\n"
             "Otherwise, this includes goods stored in any Stock Location "
             "with 'internal' type.")
    
    def _compute_free_quantities(self):
        # TDE FIXME: why not using directly the function fields ?
       
        for template in self:
            free_qty = 0
            
            for p in template.product_variant_ids:
                free_qty += p.free_qty
            template.free_qty = free_qty 
            
        

class PickingType(models.Model):
    _inherit = "stock.picking.type"
    
    dropship_steps = fields.Integer('Dropship Steps',help="Number of step to skip to count received quantity")
    validation_control = fields.Boolean('Validation Control',default=False,help="Control if the quantity is more than reserved you cannot validate")
    #if you change detailed operation after update stock return to default. This function avoid this
    @api.model
    def _disable_detailed_operation(self):
        types = self.search([(True,'=',True)])
        types.write({
                     'show_operations':False,
                     'show_reserved':True
                     })
        
class PickingAssignation(models.Model):
    _name = "stock.picking_assignation"
    _description = "Stock Picking Assignation"
    _order = "sequence"
    
    sequence = fields.Integer('Sequences')
    model_name = fields.Char(string="Model",default="stock.picking",store=True)
    name = fields.Char('Nome Stato per il Picking')
    filter_domain = fields.Char('Filter On', help="Filter on the object")
    user_ids = fields.Many2many('res.users',string="Utenti abilitati a validare")
    batch_user_id = fields.Many2one('res.users',string="Utente a cui viene assegnato il batch giornaliero")
    picking_ids = fields.One2many("stock.picking",'picking_assignation_id','Pickings')
    
    @api.model
    def generate_batch(self):
        assignations = self.search([('batch_user_id','!=',False)])
        for a in assignations:
            picking_ids = [p.id for p in a.picking_ids if p.state in ['draft','confirmed','assigned'] and p.batch_id.id == False]
            batch_values={
                          'user_id':a.batch_user_id.id,
                          'picking_ids':picking_ids
                          }
            if picking_ids:
                bv = self.env["stock.picking.batch"].create(batch_values)

    def align_pickings(self):
        pickings = self.env["stock.picking"].search([(1,'=',1)])
        for a in pickings:
            a.picking_assignation_id = self._calc_picking(a)
            
    @api.model
    def _calc_picking(self,pickings):
        assignations = self.search([(1,'=',1)])
        for a in assignations:
            for p in pickings:
                domain = [('id', 'in', p.ids)] + (safe_eval(a.filter_domain,  {}) if a.filter_domain else [])
                if self.env["stock.picking"].search(domain):
                    return a.id
        return False
                
class Scrap(models.Model):
    _inherit = 'stock.scrap'
    
    
    def _get_default_scrap_location_id(self):
        company_id = self.env.company
        return company_id.default_scrap_location_id.id
    
    
    partner_id = fields.Many2one('res.partner','Vendor',related='origin_purchase_id.partner_id')
    origin_purchase_line_id = fields.Many2one('purchase.order.line','Origin Purchase Line')
    origin_purchase_id = fields.Many2one('purchase.order',string='Origin Purchase Order',related='origin_purchase_line_id.order_id',store=True)
    origin_sale_line_id = fields.Many2one('sale.order.line','Origin Sale Line')
    origin_sale_id = fields.Many2one('sale.order',related="origin_sale_line_id.order_id",store=True,string='Origin Sale Order')
    scrap_location_id = fields.Many2one(
        'stock.location', 'Scrap Location', default=_get_default_scrap_location_id,
        domain="[('scrap_location', '=', True), ('company_id', 'in', [company_id, False])]", required=True, states={'done': [('readonly', True)]}, check_company=True)
    
    
    
class Location(models.Model):
    _inherit = "stock.location"
    
    
    not_bypass_reservation_for_scrap = fields.Boolean('Non bypassare la reservation',default=False)
    group_same_origin = fields.Boolean('Raggruppa per origin',default=False,help='Permetti raggruppamento per movimentazioni verso questa locazione basata sul origine e indipendentemente dal Procurement Group')
    auto_backorder = fields.Boolean('Autobackorder',default=True)
    picking_accepted = fields.Boolean('Default Picking Accepted',default=True)
    scrap_on_backorder= fields.Boolean(string="Scrap on Backorder")
    partner_group = fields.Boolean('Raggruppa per partner',default=False,help='Permetti raggruppamento per movimentazioni verso questa locazione basata sul Partner e indipendentemente dal Procurement Group')
    no_group = fields.Boolean('Nessun Raggruppamento',default=True,help='Non permettere mai raggruppamento per movimentazioni verso questa locazione')
    only_in_pack = fields.Boolean('Locazione solo con pacchi',default=False,help='Si accettano solo pacchi verso questa locazione')
    with_corrier_validate = fields.Boolean('Con Corriere',default=False,help='Si accettano solo pacchi con corriere verso questa locazione')
    show_for_reserve = fields.Boolean('Show on Reserve',default=False,help="Le quantità effettuate in questa locazione vengono contate come riservate nell'ordine")
    cannot_put_in_pack = fields.Boolean('Cannot put in pack',default=False,help="Movimentazioni verso questa ubicazione non possono essere messe in pacchi")
    stock_ubication = fields.Boolean('Is a Stock Ubication',help="Ubicazione per il calcolo delle in Stock, free to use, e virtual availability",default=False)
    
    @api.constrains('location_id')
    def _location_id(self):
        for a in self:
            if a.location_id:
                a.write({
                         'stock_ubication':a.location_id.stock_ubication,
                         'cannot_put_in_pack':a.location_id.cannot_put_in_pack,
                         'group_same_origin':a.location_id.group_same_origin,
                         'auto_backorder':a.location_id.auto_backorder,
                         'partner_group':a.location_id.partner_group,
                         'no_group':a.location_id.no_group
                         })
    
    def should_bypass_reservation(self):
        self.ensure_one()
        return self.usage in ('supplier', 'customer', 'inventory', 'production') or (self.scrap_location and not self.not_bypass_reservation_for_scrap)

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    
    default_return_location_id = fields.Many2one(
        'stock.location',string='Default Return Location', domain="[('return_location', '=', True),'|',('company_id', '=', False), ('company_id', '=',id)]")
    default_scrap_location_id = fields.Many2one(
        'stock.location',string='Default Scrap Location', domain="[('scrap_location', '=', True),'|',('company_id', '=', False), ('company_id', '=',id)]")
    
class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'
    
    def _get_default_return_location_id(self):
        company_id = self.env.company
        return company_id.default_return_location_id.id
    
    location_id = fields.Many2one(
        'stock.location', 'Return Location',default=_get_default_return_location_id,
        domain="['|', ('id', '=', original_location_id), '|', '&', ('return_location', '=', True), ('company_id', '=', False), '&', ('return_location', '=', True), ('company_id', '=', company_id)]")

    
    
class Picking(models.Model):
    _inherit = "stock.picking"
    
    picking_assignation_id = fields.Many2one('stock.picking_assignation',string="Assignation",compute="_assignation",store=True)

    picking_accepted = fields.Boolean('Picking Accepted',default=False,tracking=True)
    
    origin_picking_id = fields.Many2one('stock.picking',string="Trasferimento Precedente",compute="_origin_picking")
    origin_date_done = fields.Date('Data Completamento precedente',compute="_origin_picking")
    show_validate = fields.Boolean(
        compute='_compute_show_validate',
        help='Technical field used to compute whether the validate should be shown.')
    cannot_put_in_pack = fields.Boolean(
        compute='_compute_cannot_put_in_pack',
        help='Technical field used to compute whether the validate should be shown.',store=True)
    origin_purchase_id = fields.Many2one('purchase.order',string='Ordine',related="move_lines.origin_purchase_id",store=True)
    origin_vendor_id = fields.Many2one('res.partner', string='Fornitore',related="origin_purchase_id.partner_id",store=True)
     
    origin_sale_id = fields.Many2one('sale.order',string='Ordine Cliente',related="move_lines.origin_sale_id",store=True)
    origin_customer_id = fields.Many2one('res.partner', string='Cliente',related="origin_sale_id.partner_id",store=True)
    product_status = fields.Selection([('none','None'),('partial','Partial'),('total','Total')],compute="_product_status",string="Product Status",help="Field for ready picking that says you if all the product are ready or only part of them")
    total_line_processed_goods = fields.Float('Total Qty Processed',compute="_totals")
    total_line_goods = fields.Float('Total Qty To Process',compute="_totals")
    total_reserved_goods = fields.Float('Total Reserved ',compute="_totals")
    percentage_reserved_goods = fields.Float('Percentage Reserved ',compute="_totals")
    percentage_processed_goods = fields.Float('Percentage Processed ',compute="_totals")
    not_correct = fields.Boolean('Not Correct',default=False,store=True,compute="_compute_done")
    number_done = fields.Float('Product Read',tracking=True,store=True,compute="_compute_done")
    
    @api.depends('move_line_ids.qty_done')
    def _compute_done(self):
        for picking in self:
            number_done=0.0
            not_correct = False
            for move in picking.move_line_ids:
                number_done += move.qty_done 
                if move.qty_done > move.product_uom_qty and picking.picking_type_id.validation_control:
                    not_correct = True
            picking.write({
                           'number_done':number_done,
                           'not_correct':not_correct
                           })
                
    def copy_next_step(self,default=False):
        return self.with_context(next_step=True).copy(default)
    
    def copy_prev_step(self,default=False):
        return self.with_context(prev_step=True).copy(default)
    
    def copy_origins(self):
        return self.with_context(clone_origins=True).copy()
    
    def copy_dests(self):
        return self.with_context(clone_dests=True).copy()
    
    def copy_origins_dests(self):
        return self.with_context(clone_dest_origins=True).copy()
    
    def _totals(self):
        for picking in self:
            
            total_line_processed_goods=0.0
            total_line_goods=0.0
            total_reserved_goods=0.0
            for move in picking.move_line_ids:
               
                    total_line_goods += move.product_uom_qty
                    total_line_processed_goods += move.quantity_done 
                    total_reserved_goods += move.reserved_availability
            percentage_reserved_goods = (total_reserved_goods / total_line_goods)*100 if total_line_goods else 0.0
            percentage_processed_goods = (total_line_processed_goods / total_reserved_goods)*100 if total_reserved_goods else 0.0
            picking.write({
                           'total_line_processed_goods':total_line_processed_goods,
                           'total_line_goods':total_line_goods,
                           'total_reserved_goods':total_reserved_goods,
                           'percentage_reserved_goods':percentage_reserved_goods,
                           'percentage_processed_goods':percentage_processed_goods
                           })
            
    def action_see_move_line_package(self):
        self.ensure_one()
        action = self.env.ref('syd_inventory_extended.action_see_move_line').read()[0]
        action['domain'] = [('picking_id', 'in', self.ids),('qty_done','>',0)]
        
        return action
    
    # da connettore prima conferma e poi applica il tracking ref
    @api.constrains('carrier_tracking_ref')
    def update_carrier_on_picking(self):
        for a in self:
            if a.state == 'done':
                for mfrom in a.move_ids_without_package:
                    for m in mfrom.move_dest_ids:
                        if a.carrier_tracking_ref:
                            m.picking_id.write({
                                     'carrier_id':a.carrier_id.id,
                                     'carrier_tracking_ref':a.carrier_tracking_ref
                                })
                        
                        
    
    def action_multiple_done(self):
        self._check_company()
        pickings = self
        if any(picking.state not in ('assigned') for picking in pickings):
            raise UserError(_('Some transfers are still waiting for goods. Please check or force their availability before setting this batch to done.'))
        picking_without_qty_done = self.env['stock.picking']
        picking_to_backorder = self.env['stock.picking']
        for picking in pickings:
            if all([x.qty_done == 0.0 for x in picking.move_line_ids]):
                # If no lots when needed, raise error
                picking_type = picking.picking_type_id
                if (picking_type.use_create_lots or picking_type.use_existing_lots):
                    for ml in picking.move_line_ids:
                        if ml.product_id.tracking != 'none':
                            raise UserError(_('Some products require lots/serial numbers.'))
                # Check if we need to set some qty done.
                picking_without_qty_done |= picking
            elif picking._check_backorder():
                picking_to_backorder |= picking
            else:
                picking.action_done()
        if picking_without_qty_done:
            view = self.env.ref('stock.view_immediate_transfer')
            wiz = self.env['stock.immediate.transfer'].create({
                'pick_ids': [(4, p.id) for p in picking_without_qty_done],
                'pick_to_backorder_ids': [(4, p.id) for p in picking_to_backorder],
            })
            return {
                'name': _('Immediate Transfer?'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'stock.immediate.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }
        if picking_to_backorder:
            return picking_to_backorder.action_generate_backorder_wizard()
        # Change the state only if there is no other action (= wizard) waiting.
        return True
    
    def _update_packing_list(self,close=False):
        for pick in self:
            packing_ids = self.env['stock.quant.package']
            for m in pick.move_line_ids:
                packing_ids |= m.result_package_id
            packing_ids._generate_packing_list()
            if close and pick.picking_type_code == 'outgoing':
                packing_ids.close_pack()
        
    
    def _product_status(self):
        for pick in self:
            if pick.state=='done':
                status = 'total'
            else:
                at_least_one_reserved = False
                status = 'none'
                for m in pick.move_lines:
                    if m.reserved_availability > 0:
                        at_least_one_reserved = True
                        status = 'total'
                for m in pick.move_lines:
                    if at_least_one_reserved and (m.product_uom_qty  - m.reserved_availability)>0:
                        status = 'partial'
            pick.product_status = status
    
    @api.constrains('state','picking_accepted')
    def _notify_picking(self):
        for a in self:
            if a.origin_purchase_id:
                a.origin_purchase_id._notify_picking()
            if a.origin_sale_id:
                a.origin_sale_id._notify_picking()
            # for picking grouped and different so or po the reference is on the move
            if not a.origin_purchase_id and not a.origin_sale_id:
                origin_purchase_id = self.env['purchase.order']
                origin_sale_id = self.env['sale.order']
                for m in a.move_lines:
                    origin_purchase_id |= m.origin_purchase_id
                    origin_sale_id |= m.origin_sale_id
                    for a in m.total_grouped_sale_ids:
                        origin_sale_id |= a
                if origin_purchase_id:
                    origin_purchase_id._notify_picking()
                if origin_sale_id:
                    origin_sale_id._notify_picking()
                    
    
    @api.depends('location_dest_id','location_dest_id.cannot_put_in_pack')
    def _compute_cannot_put_in_pack(self):
        for picking in self:
            picking.cannot_put_in_pack = picking.location_dest_id.cannot_put_in_pack
                
    @api.depends('location_id','location_dest_id','picking_accepted')
    def _assignation(self):
        for a in self:
            a.picking_assignation_id = self.env['stock.picking_assignation'].sudo()._calc_picking(a)
    
    def button_validate(self):
        self.ensure_one()
        if self.location_dest_id.only_in_pack and not self.has_packages:
            raise ValidationError(_('Per poter validare questo trasferimento devi creare un pacco'))
        if self.picking_assignation_id:
            if self.picking_assignation_id.user_ids:
                if self.env.user.id not in self.picking_assignation_id.user_ids.ids and not self.env.user.has_group('stock.group_stock_manager'):
                    raise ValidationError(_('Non sei abilitato a validare questo trasferimento'))
        return super(Picking,self).button_validate()
        
    def put_in_pack(self):
        self.ensure_one()
        if self.location_dest_id.with_corrier_validate and not (self.carrier_id or self.carrier_tracking_ref):
            raise ValidationError(_('Per poter creare un pacco in questo trasferimento è necessario inserire il corriere o il numero di tracking'))
        return super(Picking,self).put_in_pack()
    
    
    # se hai il tracking ref non chiama il corriere       
    def send_to_shipper(self):
        self.ensure_one()
        if not (self.carrier_tracking_ref):
            super(Picking,self.sudo()).send_to_shipper()

        
        
    def _get_picking_fields_to_read(self):
        """ Inject the field 'picking_accepted' in the initial state of the barcode view.
        """
        fields = super(Picking, self)._get_picking_fields_to_read()
        fields.append('not_correct')
        fields.append('picking_accepted')
        fields.append('cannot_put_in_pack')
        fields.append('product_status')
        fields.append('total_line_processed_goods')
        fields.append('total_line_goods')
        return fields

    
    def accept_picking(self,from_mobile=False):
        self.write({'picking_accepted':True})
        if from_mobile:
            action = self.env.ref('stock_barcode.stock_barcode_action_main_menu').read()[0]
            return dict(action, target='fullscreen')
    
    @api.depends('state', 'is_locked','picking_accepted')
    def _compute_show_validate(self):
        for picking in self:
            if picking.picking_accepted :
                super(Picking,self)._compute_show_validate()
            else:
                picking.show_validate = False
    
    @api.model
    def create(self,values):
        res = super(Picking,self).create(values)
        res.picking_accepted = res.location_dest_id.picking_accepted
        return res
        
        
    def _origin_picking(self):
        for a in self:
            picking_id = False
            for m in a.move_ids_without_package:
                for o in m.move_orig_ids:
                    picking_id = o.picking_id
            a.write({
                    'origin_picking_id':picking_id.id if picking_id else False,
                    'origin_date_done':picking_id.date_done if picking_id else False
                     }
                     )
    # Scrap for the other 
    def action_done(self):
        scrap_ids = []
        for pick in self:
            if pick.location_id.scrap_on_backorder:
                if pick.state != 'assigned':
                    pick.action_assign()
                    if pick.state != 'assigned':
                        raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
                for m in pick.move_lines:
                    partner_id = m.backorder_partner_id.id
                    if (m.reserved_availability - m.quantity_done)>0:
                        scrap_id_values = {
                                                        'partner_id':partner_id,
                                                        'origin':pick.origin,
                                                        'product_id':m.product_id.id,
                                                        'scrap_qty':m.reserved_availability - m.quantity_done,
                                                         'product_uom_id':m.product_uom.id,
                                                        'picking_id':pick.id,
                                                        'origin_purchase_line_id' : m.origin_purchase_line_id.id,
                                                        'origin_sale_line_id' : m.origin_sale_line_id.id,
                                                        'scrap_location_id':self.env.company.default_scrap_location_id.id
                                                        }
                        scrap_ids += [scrap_id_values]

                for move in pick.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                    for move_line in move.move_line_ids:
                        move_line.qty_done = move_line.product_uom_qty
        res =super(Picking,self).action_done()
        
        for value in scrap_ids:
            s = self.env['stock.scrap'].create(value)
            s.action_validate()
        self._update_packing_list(close=True)
        return res
        
    # Backorder automatico
    def action_generate_backorder_wizard(self):
        autobackorder = any([l.location_id.auto_backorder for l in self])
        if ( autobackorder ):
            view = self.env.ref('stock.view_backorder_confirmation')
            wiz = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, p.id) for p in self]})
            return wiz.process()
        else:
            return super(Picking,self).action_generate_backorder_wizard()
    
    

    @api.constrains('state')
    def recalculate_for_dropship(self):
        for a in self:
            if a.state == 'done' and a.origin_purchase_id:
                a.origin_purchase_id.order_line._compute_qty_received()

   
              
class StockMove(models.Model):
    _inherit = 'stock.move'
    
    backorder_partner_id = fields.Many2one('res.partner','Backorder Partner',help="Technical field for the vendor owner on scrap product")
    origin_purchase_line_id = fields.Many2one('purchase.order.line','Origin Purchase Line')
    origin_purchase_id = fields.Many2one('purchase.order',string='Origin Purchase Order',related='origin_purchase_line_id.order_id',store=True)
    origin_sale_line_id = fields.Many2one('sale.order.line','Origin Sale Line')
    origin_sale_id = fields.Many2one('sale.order',related="origin_sale_line_id.order_id",store=True,string='Origin Sale Order')
    total_grouped_sale_ids= fields.Many2many('sale.order',relation="sale_order_stock_move")
    total_grouped_sale_line_ids= fields.Many2many('sale.order.line',relation="sale_order_line_stock_move")
    custom_value = fields.Char('Custom Value')
    
    @api.constrains('custom_value')
    def _custom_value(self):
        for a in self:
            if a.custom_value:
                a.name += " Personalized: " + a.custom_value
    
    @api.returns(None, lambda value: value[0])
    def copy_data(self, default=None):
        if self.env.context.get('next_step'):
            default = dict(default or [])
            default['move_orig_ids'] = [(4, self.id)]
        if self.env.context.get('prev_step'):
            default = dict(default or [])
            default['move_dest_ids'] = [(4, self.id)]
        if self.env.context.get('clone_origins'):
            default = dict(default or [])
            default['move_orig_ids'] = [(4, a.id) for a in self.move_orig_ids]
        if self.env.context.get('clone_dest'):
            default = dict(default or [])
            default['move_dest_ids'] = [(4, a.id) for a in self.move_dest_ids]
        if self.env.context.get('clone_dest_origins'):
            default = dict(default or [])
            default['move_dest_ids'] = [(4, a.id) for a in self.move_dest_ids]
            default['move_orig_ids'] = [(4, a.id) for a in self.move_orig_ids]
        
        return super(StockMove,self).copy_data(default)
    
    # for merged move save the origin sale and origin sale line (for example PacK) 
    def _merge_moves_fields(self):
        vals = super(StockMove,self)._merge_moves_fields()
        vals['total_grouped_sale_ids']= [(4, m.id) for m in self.mapped('origin_sale_id')]
        vals['total_grouped_sale_line_ids']= [(4, m.id) for m in self.mapped('origin_sale_line_id')]
        return vals
        
        
    def _prepare_procurement_values(self):
        values = super(StockMove,self)._prepare_procurement_values()
        values['origin_sale_line_id']= self.origin_sale_line_id.id
        values['origin_purchase_line_id']= self.origin_purchase_line_id.id
        values['custom_value']= self.custom_value
        return values
    
    
    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super(StockMove, self)._prepare_merge_moves_distinct_fields()
        distinct_fields.append('custom_value')
        return distinct_fields
    
    
                
    @api.constrains('state')
    def update_carrier_on_picking(self):
        for a in self:
            if a.state == 'done':
                for m in a.move_dest_ids:
                    if a.picking_id.carrier_tracking_ref:
                        m.picking_id.write({
                                 'carrier_id':a.picking_id.carrier_id.id,
                                 'carrier_tracking_ref':a.picking_id.carrier_tracking_ref
                            })
#     # for grouped picking if the origin have the same partner leave the partner and concat origin
    def _assign_picking(self):
        """ Try to assign the moves to an existing picking that has not been
        reserved yet and has the same procurement group, locations and picking
        type (moves should already have them identical). Otherwise, create a new
        picking to assign them to. """
        Picking = self.env['stock.picking']
        grouped_moves = groupby(sorted(self, key=lambda m: [f.id for f in m._key_assign_picking()]), key=lambda m: [m._key_assign_picking()])
        for group, moves in grouped_moves:
            moves = self.env['stock.move'].concat(*list(moves))
            new_picking = False
            # Could pass the arguments contained in group but they are the same
            # for each move that why moves[0] is acceptable
            if not moves[0].location_dest_id.partner_group:
                return super(StockMove,self)._assign_picking()
            picking = moves[0]._search_picking_for_assignation()
            if picking:
                partner_id = False
                origin = ''
                if any(picking.partner_id.id == m.partner_id.id for m in moves):
                    partner_id = picking.partner_id.id
                origin_set = set()
                origin_set.add(picking.origin)
                for m in moves:
                    if m.origin:
                        origin_set.add(m.origin)
                for o in origin_set:
                    origin += (',' + (o if o else '')) if origin else (o if o else '')
                    # If a picking is found, we'll append `move` to its move list and thus its
                    # `partner_id` and `ref` field will refer to multiple records. In this
                    # case, we chose to  wipe them.
                picking.write({
                        'partner_id': partner_id,
                        'origin': origin,
                    })
                     
            else:
                new_picking = True
                picking = Picking.create(moves._get_new_picking_values())
 
            moves.write({'picking_id': picking.id})
            moves._assign_picking_post_process(new=new_picking)
        return True
     
    # manage the group by partner or no group
    def _search_picking_for_assignation(self):
        self.ensure_one()
        if self.location_dest_id.no_group or self.partner_id.commercial_partner_id.no_group_picking:
            return False
        elif self.location_dest_id.group_same_origin:
            picking = self.env['stock.picking'].search([
                    ('partner_id', '=', self.partner_id.id),
                    ('location_id', '=', self.location_id.id),
                    ('location_dest_id', '=', self.location_dest_id.id),
                    ('picking_type_id', '=', self.picking_type_id.id),
                    ('printed', '=', False),
                    ('origin','=',self.origin),
                    ('immediate_transfer', '=', False),
                    ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])], limit=1)
            return picking
        elif self.location_dest_id.partner_group:
            picking = self.env['stock.picking'].search([
                    ('partner_id', '=', self.partner_id.id),
                    ('location_id', '=', self.location_id.id),
                    ('location_dest_id', '=', self.location_dest_id.id),
                    ('picking_type_id', '=', self.picking_type_id.id),
                    ('printed', '=', False),
                    ('immediate_transfer', '=', False),
                    ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])], limit=1)
            return picking
        else:
            return super(StockMove,self)._search_picking_for_assignation()

class StockRule(models.Model):
    """ A rule describe what a procurement should do; produce, buy, move, ... """
    _inherit = 'stock.rule'

    propagate_contact_id = fields.Boolean('Propagate Contact as Owner',default=False)
    
    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, po):
        res = super(StockRule,self)._prepare_purchase_order_line(product_id, product_qty, product_uom, company_id, values, po)
        custom_value = False
        for a in values['move_dest_ids']:
            custom_value = a.custom_value if custom_value == False or a.custom_value == custom_value else False
        res['custom_value'] = custom_value
        return res
    
    @api.model
    def _get_procurements_to_merge_groupby(self, procurement):
        res = super(StockRule,self)._get_procurements_to_merge_groupby(procurement)
        move_dest_ids = procurement.values.get('move_dest_ids')
        if move_dest_ids:
            custom_value = False
            for a in move_dest_ids:
                custom_value = a.custom_value if custom_value == False or a.custom_value == custom_value else False
            res += (custom_value,)
        return res

    
    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        val = super(StockRule,self)._push_prepare_move_copy_values(move_to_copy,new_date)
        val['origin_purchase_line_id']=move_to_copy.origin_purchase_line_id.id
        val['origin_sale_line_id']=move_to_copy.origin_sale_line_id.id
        val['custom_value']= move_to_copy.custom_value
        if self.propagate_contact_id:
            val['backorder_partner_id']=move_to_copy.backorder_partner_id.id or move_to_copy.picking_id.partner_id.id
        return val
    
    def _get_custom_move_fields(self):
        values = super(StockRule,self)._get_custom_move_fields()
        values+= ['origin_purchase_line_id','origin_sale_line_id','custom_value']
        return values
    
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    qty_reserved = fields.Float('Packed',compute='_compute_qty_reserved')
    total_grouped_move_ids= fields.Many2many('stock.move',relation="sale_order_line_stock_move",copy=False)
    origin_move_ids = fields.One2many('stock.move','origin_sale_line_id')
    custom_value = fields.Char('Custom Value',store=True)
    product_note = fields.Char('Product note')
    
    @api.depends('product_custom_attribute_value_ids', 'product_custom_attribute_value_ids.custom_value')
    def _custom_value(self):
        for a in self:
            a.custom_value = a.product_custom_attribute_value_ids and a.product_custom_attribute_value_ids.custom_value or a.custom_value
        
    def _prepare_procurement_values(self, group_id=False):
        values = super(SaleOrderLine,self)._prepare_procurement_values(group_id)
        values['origin_sale_line_id']= self.id
        values['custom_value']= self.custom_value
        return values
    
    
    @api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_reserved(self):
        for line in self:  # TODO: maybe one day, this should be done in SQL for performance sake
            if line.qty_delivered_method == 'stock_move':
                qty = 0.0
                outgoing_moves = line._get_reserved_outgoing_moves()
                for move in outgoing_moves:
                    qty += move.product_uom._compute_quantity(move.reserved_availability, line.product_uom, rounding_method='HALF-UP')
                    if qty == 0 and move.move_orig_ids:
                        for m in move.move_orig_ids:
                            qty += m.product_uom._compute_quantity(move.quantity_done, line.product_uom, rounding_method='HALF-UP')
    
                line.qty_reserved = qty
            else:
                line.qty_reserved = 0
                
    def _get_reserved_outgoing_moves(self):
        outgoing_moves = self.env['stock.move']
        for move in self.move_ids.filtered(lambda r: r.state != 'cancel' and not r.scrapped and self.product_id == r.product_id):
            if move.location_id.show_for_reserve:
                if not move.origin_returned_move_id or (move.origin_returned_move_id and move.to_refund):
                    outgoing_moves |= move
        
        return outgoing_moves

class SaleOrder(models.Model):
    _inherit = 'sale.order'   
    
    message_state = fields.Char('Internal Field for Notify',store=True,compute='_notify_picking',copy=False)
    total_picking_ids = fields.Many2many('stock.picking','sale_total_picking',string='Total Picking',compute="_total_picking")
    total_move_ids = fields.One2many('stock.move','origin_sale_id')
    total_grouped_move_ids= fields.Many2many('stock.move',relation="sale_order_stock_move",copy=False)
    total_picking_count = fields.Integer('Total transfer count',compute="_total_picking")
    has_packages = fields.Boolean(
        'Has Packages', compute='_compute_has_packages',
        help='Check the existence of destination packages on move lines')
    
    @api.model
    def _prepare_purchase_order_line_data(self, so_line, date_order, purchase_id, company):
        res = super(SaleOrder,self)._prepare_purchase_order_line_data( so_line, date_order, purchase_id, company)
        res['custom_value']= so_line.custom_value
        return res
    
    def action_view_total_picking(self):
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]
        # override the context to get rid of the default filtering on operation type
        result['context'] = {'default_partner_id': self.partner_id.id, 'default_origin': self.name}
        pick_ids = self.mapped('total_picking_ids')
        # choose the view_mode accordingly
        if not pick_ids or len(pick_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (pick_ids.ids)
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state,view) for state,view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = pick_ids.id
        return result
    
    def _compute_has_packages(self):
        for order in self:
            order.has_packages = any([p.has_packages for p in order.total_picking_ids])
    
    def action_see_packages(self):
        self.ensure_one()
        action = self.env.ref('stock.action_package_view').read()[0]
        packages = self.total_picking_ids.move_line_ids.mapped('result_package_id')
        action['domain'] = [('id', 'in', packages.ids)]
        return action
            

    def _total_picking(self):
        for a in self:
            picking_ids = set()
            for m in a.total_move_ids:
                if m.picking_id.id:
                    picking_ids.add(m.picking_id.id)
            for m in a.total_grouped_move_ids:
                if m.picking_id.id:
                    picking_ids.add(m.picking_id.id)
            a.write({
                    'total_picking_ids' : [(6,0,list(picking_ids))],
                    'total_picking_count':len(picking_ids)
                    }
                    )

        
    def _notify_picking(self):
        for a in self:
            body = '<ul>'
            for p in a.total_picking_ids:
                body += '<li>%s: %s - %s</li>' %(p.picking_assignation_id.name,p.name,p.state)
            body += '</ul>'
            if a.message_state != body:
                a.message_post(body=body)
            a.message_state = body
            
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    
    custom_value = fields.Char('Custom Value')
    
    @api.constrains('custom_value')
    def _custom_value(self):
        for a in self:
            if a.custom_value:
                a.name += " Personalized: " + a.custom_value
    
    def _find_candidate(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        """ Return the record in self where the procument with values passed as
        args can be merged. If it returns an empty record then a new line will
        be created.
        """
        custom_value = False
        for a in values['move_dest_ids']:
            custom_value = a.custom_value if custom_value == False or a.custom_value == custom_value else False
        lines = self.filtered(lambda po_line: po_line.custom_value == custom_value)
        return  super(PurchaseOrderLine,lines)._find_candidate( product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
    
    
    def _prepare_stock_moves(self,picking):
        res = super(PurchaseOrderLine,self)._prepare_stock_moves(picking)
        for r in res:
            r['origin_purchase_line_id']=self.id
            r['custom_value']=self.custom_value
        return res        
    
    @api.depends('move_ids.state', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_received(self):
        super(PurchaseOrderLine, self)._compute_qty_received()
        for line in self:
            
            if line.qty_received_method == 'stock_moves' and line.order_id.picking_type_id.dropship_steps:
                total = 0.0
                for m in line.move_ids.filtered(lambda m: m.product_id == line.product_id):
                        i = line.order_id.picking_type_id.dropship_steps
                        moves = movefinals = m
                        while i>0:
                            for move in moves:
                                movefinals |= move.move_dest_ids
                            i-=1
                            if i!=0:
                                moves = movefinals
                                movefinals = self.env['stock.move']
                        for move in movefinals:
                                if move.state == 'done':
                                    if move.location_dest_id.usage == "supplier":
                                        if move.to_refund:
                                            total -= move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                                    elif move.origin_returned_move_id and move.origin_returned_move_id._is_dropshipped() and not move._is_dropshipped_returned():
                                        # Edge case: the dropship is returned to the stock, no to the supplier.
                                        # In this case, the received quantity on the PO is set although we didn't
                                        # receive the product physically in our stock. To avoid counting the
                                        # quantity twice, we do nothing.
                                        pass
                                    elif (
                                        move.location_dest_id.usage == "internal"
                                        and move.to_refund
                                        and move.location_dest_id
                                        not in self.env["stock.location"].search(
                                            [("id", "child_of", move.warehouse_id.view_location_id.id)]
                                        )
                                    ):
                                        total -= move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                                    else:
                                        total += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                line.qty_received = total
             
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    

    has_scrap= fields.Boolean('Has Scrap',compute="_scrap")
    message_state = fields.Char('Internal Field for Notify',store=True,compute='_notify_picking')
    total_picking_ids = fields.Many2many('stock.picking','purchase_total_picking',string='Total Picking',compute="_total_picking")
    total_move_ids = fields.One2many('stock.move','origin_purchase_id')
    total_picking_count = fields.Integer('Total transfer count',compute="_total_picking")
    dropship_steps = fields.Integer('Dropship steps',related="picking_type_id.dropship_steps")
    
    @api.model
    def _prepare_sale_order_line_data(self, line, company, sale_id):
        res = super(PurchaseOrder,self)._prepare_sale_order_line_data(line, company, sale_id)
        res['custom_value']= line.custom_value
        return res
    
    def action_view_total_picking(self):
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]
        # override the context to get rid of the default filtering on operation type
        result['context'] = {'default_partner_id': self.partner_id.id, 'default_origin': self.name, 'default_picking_type_id': self.picking_type_id.id}
        pick_ids = self.mapped('total_picking_ids')
        # choose the view_mode accordingly
        if not pick_ids or len(pick_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (pick_ids.ids)
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state,view) for state,view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = pick_ids.id
        return result
    
    
    def _total_picking(self):
        for a in self:
            picking_ids = set()
            for m in a.total_move_ids:
                if m.picking_id.id:
                    picking_ids.add(m.picking_id.id)
            a.write({
                    'total_picking_ids' : [(6,0,list(picking_ids))],
                    'total_picking_count':len(picking_ids)
                    }
                    )

            
    
    def _notify_picking(self):
        for a in self:
            body = '<ul>'
            for p in a.total_picking_ids:
                body += '<li>%s: %s - %s</li>' %(p.picking_assignation_id.name,p.name,p.state)
            body += '</ul>'
            if a.message_state != body:
                a.message_post(body=body)
            a.message_state = body
            
    def _scrap(self):
        for a in self:
            scraps = self.env['stock.scrap'].search([('origin', '=', a.name)]).ids
            a.write({
                     'has_scrap':bool(scraps)
                     })
            
    def action_see_move_scrap(self):
        self.ensure_one()
        action = self.env.ref('stock.action_stock_scrap').read()[0]
        scraps = self.env['stock.scrap'].search([('origin', '=', self.name)])
        action['domain'] = [('id', 'in', scraps.ids)]
        action['context'] = dict(self._context, create=False)
        return action      

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"
    
    result_package_id = fields.Many2one(
        'stock.quant.package', 'Destination Package',
        ondelete='restrict', required=False, check_company=True,
        domain="[('state','=','open'),'|', '|', ('location_id', '=', False), ('location_id', '=', location_dest_id), ('id', '=', package_id),]",
        help="If set, the operations are packed into this package")
    

    
    @api.constrains('result_package_id')
    def _generate_packing_list(self):
        for a in self:
            if a.result_package_id and a.result_package_id.state=='closed':
                raise ValidationError('You cannot add product on a package closed')
            
            
class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"
    
    package_id = fields.Many2one(
        'stock.quant.package', 'Pack', index=True, check_company=True,
        domain="[('location_id', '=', location_id),('state','=','open')]",
    )  

    
    
    
class StockQuant(models.Model):
    _inherit = "stock.quant"
    package_id = fields.Many2one(
        'stock.quant.package', 'Package',
        domain="[('location_id', '=', location_id),('state','=','open')]",
        help='The package containing this quant', readonly=True, ondelete='restrict', check_company=True)  
             
class PackingList(models.Model):
    _name = 'stock.quant.packing_list'
    _description = 'Packing List'
    
    packing_product_id = fields.Many2one('product.product','Product')
    qty = fields.Float('Quantity')
    origin = fields.Char('Origin')
    stock_quant_package_id = fields.Many2one('stock.quant.package',string="Package")
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number')
    stock_move_line_id = fields.Many2one('stock.move.line','Move Line')
    origin_purchase_line_id = fields.Many2one('purchase.order.line','Origin Purchase Line')
    origin_purchase_id = fields.Many2one('purchase.order',string='Origin Purchase Order',related='origin_purchase_line_id.order_id',store=True)
    origin_sale_line_id = fields.Many2one('sale.order.line','Origin Sale Line')
    origin_sale_id = fields.Many2one('sale.order',related="origin_sale_line_id.order_id",store=True,string='Origin Sale Order')
    
class QuantPackage(models.Model):
    _inherit = "stock.quant.package"
   
    stock_quant_packing_list_ids = fields.One2many('stock.quant.packing_list','stock_quant_package_id',string="Confirmed Content")
    stock_quant_not_confirmed_move_ids = fields.Many2many('stock.move.line',compute="_temporary_packing",string="Temporary Content")
    state = fields.Selection([('open','Open'),('closed','Closed')],string="State",default="open")
    
    def _temporary_packing(self):
        for a in self:
            lines = self.env['stock.move.line'].search([('result_package_id','=',a.id),('package_id','!=',a.id)])
            a.stock_quant_not_confirmed_move_ids = lines.ids
            
    def open_pack(self):
        self.state = 'open'
        
    def close_pack(self):
        self.state = 'closed'
    
    

        
    def _generate_packing_list(self):
        for pack in self:
            if pack.state=='open':
                pack.stock_quant_packing_list_ids= [(5,0,0)]
                domain = [('result_package_id', 'in', pack.ids),('package_id','not in',pack.ids)]
                moves = self.env['stock.move.line'].search(domain)
                for m in moves :
                    if m.qty_done:
                        self.env['stock.quant.packing_list'].create({
                                                                 'packing_product_id':m.product_id.id,
                                                                 'qty':m.qty_done,
                                                                 'stock_quant_package_id':pack.id,
                                                                 'origin':m.origin,
                                                                 'origin_purchase_line_id':m.move_id.origin_purchase_line_id.id,
                                                                 'origin_sale_line_id':m.move_id.origin_sale_line_id.id,
                                                                 'product_uom_id':m.product_uom_id.id,
                                                                 'lot_id':m.lot_id.id,
                                                                 'origin_sale_line_id':m.move_id.origin_sale_line_id.id,
                                                                 'origin_purchase_line_id':m.move_id.origin_purchase_line_id.id,
                                                                 'stock_move_line_id':m.id
                                                                 })
   
        
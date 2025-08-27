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
from odoo.osv import expression 
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
from collections import defaultdict
import logging
from odoo.tools import groupby as groupbyelem
from operator import itemgetter
import tempfile
import base64
import os 
import xlsxwriter

_logger = logging.getLogger(__name__)


class ProductDis(models.Model):
    _name = "product.dis"
    
    name=fields.Char('Code')
    file_id = fields.Binary('File',attachment=True)
    product_id = fields.Many2one('product.product',string="Product",domain="[('product_tmpl_id','=',product_tmpl_id)]")
    product_tmpl_id = fields.Many2one('product.template',string="Product Template")
    dis_type = fields.Char('Tipo Dis')
    dis_creation_date = fields.Date('Data Creazione')
    dis_user = fields.Char('Dis User')
    dis_material = fields.Char('Dis Material')
    attachment_id = fields.Many2one('ir.attachment',compute="_ir_attachment",store=True)
    
    @api.depends('file_id')
    def _ir_attachment(self):
        for a in self:
            qry = """select id from ir_attachment where res_model = 'product.dis' and res_field = 'file_id' and res_id = %d """ % a.id
            self._cr.execute(qry)
            id = self._cr.dictfetchall()
            a.attachment_id = id[0]['id'] if id else False
    
class ImLiveChatChannel(models.Model):
    _inherit = "im_livechat.channel"
    
    button_text = fields.Char('Text of the Button',translate=True)
    default_message = fields.Char('Default Message',translate=True)
    
class CommonProductBrandEpt(models.Model):
    _inherit = 'common.product.brand.ept'
    
    barcode_text = fields.Char('Barcode Text')

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    default_service_product_id = fields.Many2one('product.product','Default Service Product Id')
    price_anomaly_id = fields.Many2one('syd_anomaly.anomaly',string="Price Anomaly")
    price_anomaly_partner_id = fields.Many2one('res.partner',string="Partner for Price Anomaly")
    
class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
       
        if operator == 'ilike' and not (name or '').strip():
                domain = []
        elif operator in ('ilike', 'like', '=', '=like', '=ilike'):
                domain = expression.AND([
                    args or [],
                    ['|', ('name', operator, name), ('barcode', operator, name)]
                ])
        partner_ids = self._search(domain, limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(partner_ids).with_user(name_get_uid))


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'
    
    
    def name_get(self):
        result = []
        for bank in self:
            result.append((bank.id, ("%s: %s")%(bank.bank_name,bank.acc_number)))
        return result
    
class ProductCategory(models.Model):
    _inherit="product.category"
    
    product_label_width=fields.Char('Label Width Milor Print (ex 100px, 2cm)',default="32%")
    product_label_height=fields.Char('Label Height Milor Print (ex 100px, 2cm)',default="10rem")
    product_barcode_width=fields.Char('Label Width Plateau (ex 100px, 2cm)',default="32%")
    product_barcode_height=fields.Char('Label Height Plateau (ex 100px, 2cm)',default="10rem")
    no_print_label = fields.Boolean('No Print on Order',boolean="False")
    name = fields.Char('Name', index=True, required=True, translate=True)
    complete_name = fields.Char(
        'Complete Name', compute='_compute_complete_name',
        store=True,translate=True)
    
    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for lang in ['it_IT','en_US']:
            for category in self.with_context(lang=lang):
                if category.parent_id:
                    category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
                else:
                    category.complete_name = category.name
    
class ProductTemplate(models.Model):
    _inherit="product.template"
    
    product_label_width=fields.Char('Label Width Milor Print (ex 100px, 2cm)',related="categ_id.product_label_width")
    product_label_height=fields.Char('Label Height Milor Print (ex 100px, 2cm)',related="categ_id.product_label_height")
    product_barcode_width=fields.Char('Label Width Plateau  (ex 100px, 2cm)',related="categ_id.product_barcode_width")
    product_barcode_height=fields.Char('Label Height Plateau  (ex 100px, 2cm)',related="categ_id.product_barcode_height")
    no_print_label = fields.Boolean('No Print Label on Order',related="categ_id.no_print_label")
    tag_product_ids = fields.Many2many("product.tags","product_tags_rel","product_tmpl_id","tag_id",string="Product Tags")      
    thron_message = fields.Char('Thron Message',compute="_thron_message",store=True) 
#     template_fixed_qty_available = fields.Float(
#         'Yesterday Quantity On Hand ',compute="_fixed_quantity",store=True)
    template_fixed_virtual_available = fields.Float(
        'Yesterday Forecast Quantity (Parent)',compute="_fixed_quantity",store=True)
    
    template_dis_ids = fields.One2many('product.dis','product_tmpl_id',string='Dis')
    date_new_category = fields.Date("New Category Assignation Date",readonly=True)
    last_cost_update = fields.Datetime("Last Cost Update")
    dotcom_qvc = fields.Boolean(string="DOTCOM QVC")
    
    def set_alternative_product_ids(self):
        for a in self:
            collection = a.collection_id
            brand = a.product_brand_id
            if bool(collection):
                a.alternative_product_ids = a.search([('collection_id','=',collection.id),('categ_id','!=',a.categ_id.id),('is_published','=',True)], limit=8)
            elif bool(brand):
                a.alternative_product_ids = a.search([('product_brand_id','=',brand.id),('categ_id','!=',a.categ_id.id),('is_published','=',True)], limit=8)
               
#     template_fixed_free_qty = fields.Float(
#         'Yesterday Free To Use Quantity ',compute="_fixed_quantity",store=True)
#     
    def archive_and_delete_reordering(self):
        for a in self:
            if a.orderpoint_ids:
                if a.free_qty >0 :
                    raise ValidationError(_('Product with positive stock!!'))
                a.orderpoint_ids.unlink()
            a.write({'active':False})
                
    
    
    @api.depends('product_variant_ids.fixed_virtual_available')
    def _fixed_quantity(self):
        for a in self:
#             template_fixed_qty_available = sum(v.fixed_qty_available for v in a.product_variant_ids)
            template_fixed_virtual_available = sum(v.fixed_virtual_available for v in a.product_variant_ids)
#             template_fixed_free_qty = sum(v.fixed_free_qty for v in a.product_variant_ids)
#             a.template_fixed_qty_available = template_fixed_qty_available
            a.template_fixed_virtual_available = template_fixed_virtual_available
#             a.template_fixed_free_qty = template_fixed_free_qty

    @api.depends('name_lang','technical_description','plating_description','ept_image_ids')
    def _thron_message(self):
        
        for t in self:
            thron_message = ''
            
            if not t.name_lang:
                    thron_message += 'No-Name,'
            if not t.technical_description:
                    thron_message += 'No-IT-Des,'
            if not t.plating_description:
                    thron_message += 'No-EN-Des,'
            
            if not t.ept_image_ids:
                    thron_message += 'No-IMGS,'
            t.thron_message = thron_message
    
    def _get_images(self):
        """Return a list of records implementing `image.mixin` to
        display on the carousel on the website for this template.
        This returns a list and not a recordset because the records might be
        from different models (template and image).
        It contains in this order: the main image of the template and the
        Template Extra Images.
        """
        self.ensure_one()
        res= {}
        for p in self.product_template_image_ids:
            res[p.name]= p
        return list(res.values())

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    product_brand_ids = fields.Many2many('common.product.brand.ept',string='Brand per eCommerce')
    group_picking = fields.Boolean('Raggruppamento Indipendentemente dal Brand',default=False,help='Permetti raggruppamento indipendente dal brand')
    big_customer = fields.Boolean(string="Big Customer", default=False) 
    prodotti_collegati = fields.One2many("related.products.line","related_id",string="Prodotti Collegati")
    
    def set_prodotti_collegati(self):
        """
            Set all related products, price and mean price
        """
        if self.big_customer:
            calc_products = self.env['sale.order'].search([('partner_id','=',self.id),('state','in',['sale','sent','done'])]).order_line.product_id.filtered(lambda x: x not in self.prodotti_collegati.products_id)
            if bool(calc_products):
                pr = [[0,0,{'products_id':product.id}] for product in calc_products]
                self.prodotti_collegati = pr
                
            for line in self.prodotti_collegati:
                prices = self.env['sale.order.line'].search([('order_id.partner_id','=',self.id),('product_id','=',line.products_id.id),('state','in',['sale','sent','done'])])
                line.update({'last_price':self.env['sale.order.line'].search([('order_id.partner_id','=',self.id),('product_id','=',line.products_id.id),('state','in',['sale','sent','done'])], order='write_date desc',limit=1).price_unit,
                             'mean_price':sum(a.price_unit for a in prices)/len(prices) 
                             })

class RelatedProductsLine(models.Model):
    _name = 'related.products.line'
    _description = 'Related Products Line'

    related_id = fields.Many2one('res.partner', string='Big Customer')
    products_id = fields.Many2one('product.product', string='Related Products')
    last_price = fields.Float('Last Price')
    mean_price = fields.Float('Mean Price')
    
class StockMoveLine(models.Model):
    _inherit = "stock.move.line"
    

    currency_id = fields.Many2one('res.currency',related="picking_id.currency_id",store=True)
    pricelist_id = fields.Many2one('product.pricelist',related="picking_id.pricelist_id",store=True)
    price = fields.Monetary('Price',compute="_compute_price")
    milor_plateau = fields.Char('Milor Plateau',related="product_id.milor_plateau",store=True)
    
    def _compute_price(self):
        for a in self:
            res = {}
            res = a.pricelist_id.price_get(a.product_id.id,1)
            if a.pricelist_id.item_ids:
                if a.pricelist_id.item_ids[0].base_pricelist_id:
                        res = a.pricelist_id.item_ids[0].base_pricelist_id.price_get(a.product_id.id,1)
                        a.price = res.get(a.pricelist_id.item_ids[0].base_pricelist_id.id,0)
                else:
                        a.price = res.get(a.pricelist_id.id,0)
            else:
                a.price = res.get(a.pricelist_id.id,0)
            
class Location(models.Model):
    _inherit = "stock.location"
    
    
    partner_and_brand_group = fields.Boolean('Raggruppa per partner e brand',default=False)
    
class StockMove(models.Model):
    _inherit = "stock.move"
    _order = 'origin, milor_plateau desc'
    
    date_deadline_from = fields.Date('Date Deadline From')
    date_deadline_to = fields.Date('Date Deadline To')
    currency_id = fields.Many2one('res.currency',related="picking_id.currency_id",store=True,string="Partner Currency")
    pricelist_id = fields.Many2one('product.pricelist',related="picking_id.pricelist_id",store=True)
    price = fields.Monetary('Price',compute="_compute_price")
    purchase_price  = fields.Float('Purchase Price',related="origin_purchase_line_id.price_unit")
    purchase_currency_id = fields.Many2one('res.currency',string="Purchase Currency",related="origin_purchase_id.currency_id")
    sale_price  = fields.Float('Sale Price',compute="_sale_price_and_currency")
    sale_currency_id = fields.Many2one('res.currency',string=" Currency",compute="_sale_price_and_currency")
    product_category_id = fields.Many2one('product.category',string='Product Category',related="product_id.categ_id",store=True) 
    milor_plateau = fields.Char('Milor Plateau',related="product_id.milor_plateau",store=True)
    purchase_price_inserted = fields.Float('DDT Price',compute="_get_purchase_price_logic",inverse="_set_purchase_price_logic")
    raw_purchase_price_inserted = fields.Float('')

    def _get_purchase_price_logic(self):
        for a in self:
            if a.raw_purchase_price_inserted != a.purchase_price and a.raw_purchase_price_inserted != 0:
                a.purchase_price_inserted = a.raw_purchase_price_inserted
            else:
                a.purchase_price_inserted = a.purchase_price


    def _set_purchase_price_logic(self):
        for a in self:
            a.raw_purchase_price_inserted = a.purchase_price_inserted
            
                   
    
    def _action_done(self, cancel_backorder=False):
        self.filtered(lambda move: move.state == 'draft')._action_confirm()  # MRP allows scrapping draft moves
        moves = self.exists().filtered(lambda x: x.state not in ('done', 'cancel'))
        moves_todo = self.env['stock.move']

        # Cancel moves where necessary ; we should do it before creating the extra moves because
        # this operation could trigger a merge of moves.
        for move in moves:
            if move.quantity_done <= 0:
                if float_compare(move.product_uom_qty, 0.0, precision_rounding=move.product_uom.rounding) == 0 or cancel_backorder:
                    move._action_cancel()

        # Create extra moves where necessary
        for move in moves:
            if move.state == 'cancel' or move.quantity_done <= 0:
                continue

            moves_todo |= move._create_extra_move()

        moves_todo._check_company()
        # Split moves where necessary and move quants
        for move in moves_todo:
            # To know whether we need to create a backorder or not, round to the general product's
            # decimal precision and not the product's UOM.
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(move.quantity_done, move.product_uom_qty, precision_digits=rounding) < 0:
                # Need to do some kind of conversion here
                qty_split = move.product_uom._compute_quantity(move.product_uom_qty - move.quantity_done, move.product_id.uom_id, rounding_method='HALF-UP')
                new_move = move._split(qty_split)
                move._unreserve_initial_demand(new_move)
                if cancel_backorder:
                    self.env['stock.move'].browse(new_move).with_context(moves_todo=moves_todo)._action_cancel()
        moves_todo.mapped('move_line_ids').sorted()._action_done()
        # Check the consistency of the result packages; there should be an unique location across
        # the contained quants.
#         for result_package in moves_todo\
#                 .mapped('move_line_ids.result_package_id')\
#                 .filtered(lambda p: p.quant_ids and len(p.quant_ids) > 1):
#             if len(result_package.quant_ids.filtered(lambda q: not float_is_zero(abs(q.quantity) + abs(q.reserved_quantity), precision_rounding=q.product_uom_id.rounding)).mapped('location_id')) > 1:
#                 raise UserError(_('You cannot move the same package content more than once in the same transfer or split the same package into two location.'))
        picking = moves_todo.mapped('picking_id')
        moves_todo.write({'state': 'done', 'date': fields.Datetime.now()})

        move_dests_per_company = defaultdict(lambda: self.env['stock.move'])
        for move_dest in moves_todo.move_dest_ids:
            move_dests_per_company[move_dest.company_id.id] |= move_dest
        for company_id, move_dests in move_dests_per_company.items():
            move_dests.sudo().with_context(force_company=company_id)._action_assign()

        # We don't want to create back order for scrap moves
        # Replace by a kwarg in master
        if self.env.context.get('is_scrap'):
            return moves_todo

        if picking and not cancel_backorder:
            picking._create_backorder()
        return moves_todo
    
    def _sale_price_and_currency(self):
        for a in self:
            if a.origin_sale_line_id:
                a.write({
                         'sale_price':a.origin_sale_line_id.price_unit,
                         'sale_currency_id':a.origin_sale_line_id.currency_id.id
                         
                         })
            elif a.total_grouped_sale_line_ids:
                a.write({
                         'sale_price':a.total_grouped_sale_line_ids[0].price_unit,
                         'sale_currency_id':a.total_grouped_sale_line_ids[0].currency_id.id
                         
                         })
            else:
                a.write({
                         'sale_price':False,
                         'sale_currency_id':False
                         
                         }
                        
                        )
    
    def _compute_price(self):
        for rec in self:
            # INFO: checks if pricelist_retail_id is set on the main picking_id, if so use that as main pricelist.
            pl = rec.picking_id.pricelist_retail_id or rec.pricelist_id
            res = pl.price_get(rec.product_id.id, 1)
            if pl.item_ids:
                if pl.item_ids[0].base_pricelist_id:
                    res = pl.item_ids[0].base_pricelist_id.price_get(rec.product_id.id, 1)
                    rec.price = res.get(pl.item_ids[0].base_pricelist_id.id, 0)
                else:
                    rec.price = res.get(pl.id, 0)
            else:
                rec.price = res.get(pl.id, 0)
            
            
    # manage the group by partner or no group
    def _search_picking_for_assignation(self):
        _logger.info('BRAND: %d',self.product_id.product_brand_id.id)
        if self.partner_id.commercial_partner_id.no_group_picking:
            return False
        if self.location_dest_id.partner_and_brand_group and self.partner_id.commercial_partner_id.group_picking:
            picking = self.env['stock.picking'].search([
                    ('partner_id', '=', self.partner_id.id),
                    ('location_id', '=', self.location_id.id),
                    ('location_dest_id', '=', self.location_dest_id.id),
                    ('picking_type_id', '=', self.picking_type_id.id),
                    ('printed', '=', False),
                    ('immediate_transfer', '=', False),
                    ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])], limit=1)
            return picking
        if self.location_dest_id.partner_and_brand_group:
            picking = self.env['stock.picking'].search([
                    ('partner_id', '=', self.partner_id.id),
                    ('origin_payment_term_id','=',self.origin_sale_id.payment_term_id.id),
                    ('location_id', '=', self.location_id.id),
                    ('location_dest_id', '=', self.location_dest_id.id),
                    ('picking_type_id', '=', self.picking_type_id.id),
                    ('product_brand_id', '=', self.product_id.product_brand_id.id),
                    ('printed', '=', False),
                    ('immediate_transfer', '=', False),
                    ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])], limit=1)
            return picking
        return super(StockMove,self)._search_picking_for_assignation()
    
class Picking(models.Model):
    _inherit = "stock.picking"
    
    
    child_po_id = fields.Many2one('purchase.order',string="Child PO",compute="_child_po",store=True)
    date_deadline_from = fields.Date('Date Deadline From',compute="_date_deadline")
    date_deadline_to = fields.Date('Date Deadline To',compute="_date_deadline")
    
    image_1920 = fields.Image("Image", related="product_id.image_1920",max_width=1920, max_height=1920)
    # resized fields stored (as attachment) for performance
    image_1024 = fields.Image("Image 1024", related="product_id.image_1024", max_width=1024, max_height=1024)
    image_512 = fields.Image("Image 512", related="product_id.image_512", max_width=512, max_height=512)
    image_256 = fields.Image("Image 256", related="product_id.image_256", max_width=256, max_height=256)
    image_128 = fields.Image("Image 128", related="product_id.image_128", max_width=128, max_height=128)    
    
    
    
    confirmable = fields.Boolean('Confirmable',compute="_is_confirmable",store=True)
    pricelist_id = fields.Many2one('product.pricelist',related="partner_id.commercial_partner_id.property_product_pricelist",store=True)
    pricelist_retail_id = fields.Many2one('product.pricelist',compute="_compute_pricelist_retail_id",string="Retail Pricelist")
    currency_id = fields.Many2one('res.currency',related="pricelist_id.currency_id",store=True)
    origin_payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Terms', compute="_origin_payment_term_id",store=True)
    product_brand_id = fields.Many2one('common.product.brand.ept', string="Brand", compute="_first_product_brand",store=True,
                                       help='Select a brand for this product.')
    
    origin_source_id = fields.Many2one('utm.source',string='Fonte Ordine',compute="_origin_source_id",store=True)
    origin_purchase_user_id = fields.Many2one('res.users',string='Referente Acquisto',compute="_purchase_partner",store=True)
    salesman_partner_id = fields.Many2one('res.partner',compute="_salesman_partner",string="Salesman",store=True)
    
    category_summary = fields.Text('Summary',compute="_category_summary")
    origin_sales_note = fields.Text('Origin note',compute="_origin_sales_note")
    amount_total = fields.Monetary('Amount Total Complete',compute="_totals")
    quantity_total = fields.Float('Quantity Total Complete',compute="_totals")
    total_goods = fields.Float('Total Qty',compute="_totals")
    total_line_goods = fields.Float('Total Qty To Process',compute="_totals")
    total_line_processed_goods = fields.Float('Total Qty Processed',compute="_totals")
    date_printed = fields.Datetime('Print Date',copy=False)
    user_printed_id = fields.Many2one('res.users',string="User Printed",copy=False)
    web_customer = fields.Boolean('From Web Order',related="partner_id.web_customer",store=True)

    vendor_date_ddt = fields.Date('Data DDT Fornitore')
    vendor_number_ddt = fields.Char('Numero DDT Fornitore')
    
    
    
    def action_done(self):
        self._automatic_anomaly()
        return super(Picking,self).action_done()
    
    def _automatic_anomaly(self):
        for a in self.filtered(lambda x:x.vendor_number_ddt):
            description = 'In riferimento al vostro documento del %s n° %s riportiamo di seguito le anomalie riscontrate: <br />'%(self.vendor_date_ddt,self.vendor_number_ddt)
            anomaly = False
            for move in a.move_ids_without_package.filtered(lambda x : x.purchase_price_inserted != x.purchase_price or x.product_uom_qty != x.quantity_done):
                description += '<strong>Prodotto</strong>: %s <strong>Prezzo Indicato su Ordine</strong>: %f <strong>Prezzo Indicato su DDT</strong>: %f  <strong>Quantita indicata su Ordine</strong>: %d <strong>Quantita indicata su DDT</strong>: %d <br />'%(move.product_id.display_name,move.purchase_price,move.purchase_price_inserted,move.product_uom_qty,move.quantity_done)
                anomaly = True
            if a.company_id.price_anomaly_id and anomaly:
                    self.env['syd_anomaly.anomaly_picking'].with_context(add_partner_id=a.company_id.price_anomaly_partner_id).create({
                                                                'anomaly_id':a.company_id.price_anomaly_id.id,
                                                                'description':description,
                                                                'send_to_partner':True,
                                                                'picking_id':a.id
                                                                })
    
    def action_multiple_done(self):
        for pick in self:
            if pick.picking_type_code != 'outgoing':
                raise ValidationError(_('Cannot validate internal or receive transfers'))
        return super(Picking,self).action_multiple_done()
        
    def _totals(self):
        for picking in self:
            amount_total = 0.0
            quantity = 0.0
            total_goods=0.0
            total_line_goods=0.0
            total_line_processed_goods=0.0
            total_all_goods = 0.0
            total_all_processed_goods = 0.0
            total_reserved_goods = 0.0
            for move in picking.move_line_ids:
                
                if not move.product_id.is_packaging:
                    total_line_goods += move.product_uom_qty
                    total_line_processed_goods += move.qty_done 
                    
                if move.move_id.origin_sale_line_id:
                    amount_total += (move.qty_done * move.move_id.origin_sale_line_id.price_unit)
                    quantity += move.qty_done
                elif move.move_id.total_grouped_sale_line_ids:
                    amount_total += (move.qty_done * move.move_id.total_grouped_sale_line_ids[0].price_unit)
                    quantity += move.qty_done
            
            for a in picking.move_ids_without_package:
                if not a.product_id.is_packaging:
                    total_goods += a.product_uom_qty
                total_all_goods += a.product_uom_qty
                total_reserved_goods += a.reserved_availability
                total_all_processed_goods += a.quantity_done
            percentage_reserved_goods = (total_reserved_goods / total_all_goods)*100 if total_all_goods else 0.0
            percentage_processed_goods = (total_all_processed_goods / total_reserved_goods)*100 if total_reserved_goods else 0.0
            picking.write({
                           'amount_total':amount_total,
                           'quantity_total':quantity,
                           'total_goods':total_goods,
                           'total_line_goods':total_line_goods,
                           'total_line_processed_goods':total_line_processed_goods,
                           'total_reserved_goods':total_reserved_goods,
                           'percentage_reserved_goods':percentage_reserved_goods,
                           'percentage_processed_goods':percentage_processed_goods
                           })
            
    @api.depends('pricelist_id')
    def _compute_pricelist_retail_id(self):
        for rec in self:
            rec.pricelist_retail_id = rec.pricelist_id and rec.pricelist_id.retail_pricelist_id or rec.pricelist_id

    @api.depends('origin_purchase_id','origin_purchase_id.child_po_ids')
    def _child_po(self):
        for pick in self:
            if pick.origin_purchase_id and pick.origin_purchase_id.child_po_ids:
                pick.child_po_id = pick.origin_purchase_id.child_po_ids[0].id
            
    def _category_summary(self):
        for pick in self:
            categories = {}
            for a in pick.move_ids_without_package:
                if a.product_id.categ_id.display_name in categories:
                    categories[a.product_id.categ_id.display_name] += a.product_uom_qty
                else :
                    categories[a.product_id.categ_id.display_name] = a.product_uom_qty
            summary = '<table class="table table-bordered" ><tr><th>Category</th><th>#</th></tr>'
            for key, value in categories.items():
                summary += "<tr><td>%s</td><td>%d</td></tr>" %(key,value)
            summary += '</table>'     
            pick.category_summary = summary
            
            
    def assign_box(self):
        for picking in self:
            for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel'] and (m.product_id.is_packaging or m.product_id.is_accessory)):
               
                move._action_assign()
#                 if move.origin_sale_line_id.product_of_package_ids:
#                     total_package = 0
#                     for mproduct in picking.move_lines.filtered(lambda m: not m.product_id.is_packaging):
#                         if mproduct.product_id.product_tmpl_id.id in move.product_id.product_of_this_package_ids.ids:
#                             total_package += mproduct.reserved_availability
#                     if move.move_line_ids:
#                         move.move_line_ids[0].product_uom_qty = total_package if total_package<move.reserved_availability else move.move_line_ids[0].product_uom_qty
            for move in picking.move_lines.filtered(lambda m: m.reserved_availability > m.quantity_done and (m.product_id.is_packaging or m.product_id.is_accessory)):
                for move_line in move.move_line_ids:
                    move_line.qty_done = move_line.product_uom_qty
        return True

    def do_print_report_picking_summary(self):
        self.write({'printed': True, 'date_printed': fields.Datetime.now(), 'user_printed_id': self.env.user.id})
        return self.env.ref('syd_custom.action_report_picking_summary').report_action(self)

    def do_print_report_picking_complete(self):
        self.write({'printed': True,'date_printed':fields.Datetime.now(),'user_printed_id':self.env.user.id})
        return self.env.ref('syd_custom.action_report_picking_complete').report_action(self)

    ## For view of stock and forecast quantity in barcode view
    def get_barcode_view_state(self):
        """ Return the initial state of the barcode view as a dict.
        """
        pickings = super(Picking,self).get_barcode_view_state()
        for picking in pickings:
#             for move_line_id in picking['move_line_ids']:
#                 move_line_id['product_id'] = self.env['product.product'].browse(move_line_id['product_id']['id']).read([
#                     'id',
#                     'tracking',
#                     'barcode',
#                     'qty_available',
#                     'virtual_available'
#                 ])[0]
            #Report da modificare per la stampa da visualizzazione app   
            picking['actionReportDeliverySlipId'] = self.env.ref('stock.action_report_delivery').id
            picking['actionReportBarcodesZplId'] = self.env.ref('syd_custom.report_picking_label_barcode_zpl').id
            picking['actionReportBarcodesPdfId'] = self.env.ref('syd_custom.report_product_picking_product_barcode_zpl').id
            picking['actionReportBarcodesQVCZplId'] = self.env.ref('syd_custom.label_product_picking_qvc_code_zpl').id
        return pickings
    
    
    @api.depends('move_lines.total_grouped_sale_ids.salesman_partner_id',"move_lines.total_grouped_sale_ids","move_lines.origin_sale_id.salesman_partner_id","move_lines.origin_sale_id")
    def _salesman_partner(self):
        for pick in self:
            partner_ids = []
            for m in pick.move_lines:
                partner_ids += [o.salesman_partner_id.id for o in m.total_grouped_sale_ids]
                partner_ids += [m.origin_sale_id.salesman_partner_id.id]
            if len(list(set(partner_ids)))==1:
                pick.salesman_partner_id = partner_ids[0]
            else:
                pick.salesman_partner_id = False
    
    @api.depends('move_lines.product_id')
    def _first_product_brand(self):
        for a in self:
            if a.move_lines:
                a.product_brand_id = a.move_lines[0].product_id.product_brand_id.id
                
    @api.depends('move_lines.origin_sale_id')
    def _origin_sales_note(self):
        for a in self:
            if a.move_lines:
                a.origin_sales_note = (a.move_lines[0].origin_sale_id.note if a.move_lines[0].origin_sale_id.note else '')
            else:
                a.origin_sales_note = False   
    
    @api.depends('move_lines.origin_sale_id')
    def _origin_source_id(self):
        for a in self:
            if a.move_lines:
                a.origin_source_id = a.move_lines[0].origin_sale_id.source_id.id
    
    @api.depends('move_lines.origin_sale_id')
    def _origin_payment_term_id(self):
        for a in self:
            if a.move_lines:
                a.origin_payment_term_id = a.move_lines[0].origin_sale_id.payment_term_id.id
                
    @api.depends('move_lines.origin_purchase_id')
    def _purchase_partner(self):
        for a in self:
            if a.move_lines:
                a.origin_purchase_user_id = a.move_lines[0].origin_purchase_id.user_id.id
        
    def _date_deadline(self):
        for a in self:
            date_deadline_from = False
            date_deadline_to = False
            for m in a.move_lines:
                date_deadline_from = m.date_deadline_from if not date_deadline_from else (m.date_deadline_from if m.date_deadline_from < date_deadline_from else date_deadline_from)
                date_deadline_to = m.date_deadline_to if not date_deadline_to else (m.date_deadline_to if m.date_deadline_to > date_deadline_to else date_deadline_from)
            a.write(
                    {
                     'date_deadline_from':date_deadline_from,
                     'date_deadline_to':date_deadline_to
                     }
                    )
            
#     def action_assign(self):
#         res = super(Picking,self).action_assign()
# #         self.assign_box()
            
    @api.depends('move_lines.product_id','move_lines.state')      
    def _is_confirmable(self):
        for a in self:
            confirmable = True
            for m in a.move_lines:
                if m.product_id.milor_type == 'mts' and confirmable:
                    confirmable = True
                else :
                    confirmable= False
            a.confirmable=confirmable
            
                
class PurchaseLine(models.Model):
    _inherit = "purchase.order.line"
    
    image_1920 = fields.Image("Image", related="product_id.image_1920",max_width=1920, max_height=1920)

    # resized fields stored (as attachment) for performance
    image_1024 = fields.Image("Image 1024", related="product_id.image_1024", max_width=1024, max_height=1024)
    image_512 = fields.Image("Image 512", related="product_id.image_512", max_width=512, max_height=512)
    image_256 = fields.Image("Image 256", related="product_id.image_256", max_width=256, max_height=256)
    image_128 = fields.Image("Image 128", related="product_id.image_128", max_width=128, max_height=128)
    sample = fields.Boolean('Sample')
    product_of_service_id = fields.Many2one('product.product',string="Prodotto del Parent PO")
    image_pos_1024 = fields.Image("Image Pos 1024", related="product_of_service_id.image_1024", max_width=1024, max_height=1024)
    image_pos_512 = fields.Image("Image Pos 512", related="product_of_service_id.image_512", max_width=512, max_height=512)
    image_pos_256 = fields.Image("Image Pos 256", related="product_of_service_id.image_256", max_width=256, max_height=256)
    image_pos_128 = fields.Image("Image Pos 128", related="product_of_service_id.image_128", max_width=128, max_height=128)
    retail_price = fields.Monetary('Retail Price',compute="_compute_price",currency="retail_currency_id")
    ret_pricelist_id = fields.Many2one('product.pricelist',related="partner_id.commercial_partner_id.property_product_pricelist",store=True)
    retail_currency_id = fields.Many2one('res.currency',related="ret_pricelist_id.currency_id",store=True)
    
    image_links = fields.Text('Image Links',compute="_image_links")
    milor_code = fields.Char('Milor Code',compute="_milor_code",store=True)


    product_metallo = fields.Selection([('bronze','Bronze'),
                                         ('silver', 'Silver'),
                                         ('gold', 'Gold')], string='Metallo',compute="get_details_line",store=True)
    product_taglia = fields.Char(string='Taglia',compute="get_details_line",store=True)
    product_pietra = fields.Char(string='Pietra',compute="get_details_line",store=True)
    product_placcatura = fields.Char(string='Placcatura',compute="get_details_line",store=True)
    plating_id = fields.Many2one("product.plating",string="Galvanica",compute="get_details_line",store=True)
    plating_depth = fields.Float(string="Depth",compute="get_details_line",store=True)
    stamp_id = fields.Many2one("product.stamp",string="Marchio",compute="get_details_line",store=True)
    product_po_id = fields.Many2one('product.product',compute="_product_po_id")
    
    def _product_po_id(self):
        for line in self:
            line.product_po_id = line.product_of_service_id.id or line.product_id.id
    

    @api.model
    def create(self,values):
        res = super(PurchaseLine,self).create(values)
        ## Add notes after the product line
        if not  res.display_type:
            supplier_info = self.env['product.supplierinfo'].sudo().search([
                    ('name', '=', res.order_id.partner_id.id),
                    '|',
                    ('product_tmpl_id', '=', res.product_id.product_tmpl_id.id),
                    ('product_id', '=', res.product_id.id),
                    
                ],limit=1)
            if supplier_info and supplier_info.note_vendor:
                self.env['purchase.order.line'].create({
                                                'sequence':res.sequence+1,
                                                'order_id':res.order_id.id,
                                                'display_type':'line_note',
                                                'name':supplier_info.note_vendor,
                                                'product_qty':0
                                                })
            ## Add notes on the PO
            if not res.order_id.notes:
                res.order_id.notes = res.product_id.description
        return res
        
        
    @api.depends('product_of_service_id','product_id')
    def get_details_line(self):
        for line in self:
            product = line.product_of_service_id or line.product_id
            if product:
                attrs = product.product_template_attribute_value_ids.product_attribute_value_id
                product_taglia = attrs.filtered(lambda x: x.attribute_id.po_column == 'taglia').name
                product_pietra = attrs.filtered(lambda x: x.attribute_id.po_column == 'pietra').name
                product_placcatura = attrs.filtered(lambda x: x.attribute_id.po_column == 'placcatura').name
                product_metallo = False
                if product.product_tmpl_id.milor_unit_id.name == 'B':
                    product_metallo = 'bronze' 
                elif product.product_tmpl_id.milor_unit_id.name == 'S':
                    product_metallo = 'silver'
                elif product.product_tmpl_id.milor_unit_id.name == 'G':
                    product_metallo = 'gold'
                plating_id = product.plating_id.id
                plating_depth = product.plating_depth
                stamp_id = product.stamp_id.id
                line.write(
                             {
                              'product_taglia':product_taglia,
                              'product_pietra':product_pietra,
                              'product_placcatura':product_placcatura,
                              'product_metallo':product_metallo,
                              'plating_id':plating_id,
                              'plating_depth':plating_depth,
                              'stamp_id':stamp_id
                              
                              })
                              


    

    @api.depends('product_of_service_id','product_of_service_id.milor_code','product_id','product_id.milor_code')
    def _milor_code(self):
        for a in self:
            milor_code= ''
            if a.product_of_service_id and a.product_of_service_id.milor_code:
                milor_code += a.product_of_service_id.milor_code
            if a.product_id and a.product_id.milor_code:
                if milor_code != '':
                    milor_code += ','
                milor_code += a.product_id.milor_code
            a.milor_code = milor_code
                    
    def _image_links(self):
        for a in self:
            image_links = '';
            for i in a.product_id.ept_image_ids.filtered(lambda self: bool(self.url)):
                image_links += '<a href="%s" target="_blank"><img width="50" height="50" src="%s" /></a>&nbsp;'%(i.url,i.url)
            a.image_links = image_links
                
    def _compute_price(self):
        for a in self:
            res = {}
            res = a.ret_pricelist_id.price_get(a.product_id.id,1)
            if a.ret_pricelist_id.item_ids:
                if a.ret_pricelist_id.item_ids[0].base_pricelist_id:
                        res = a.ret_pricelist_id.item_ids[0].base_pricelist_id.price_get(a.product_id.id,1)
                        a.retail_price = res.get(a.ret_pricelist_id.item_ids[0].base_pricelist_id.id,0)
                else:
                        a.retail_price = res.get(a.ret_pricelist_id.id,0)
            else:
                a.retail_price = res.get(a.ret_pricelist_id.id,0)
    
    def _get_wizard_values(self):
        vals = super(PurchaseLine,self)._get_wizard_values()
        if self.product_of_service_id:
            vals['product_id'] = self.product_of_service_id.id
            vals['product_uom'] = self.product_of_service_id.uom_id.id
        return vals
    
READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }
         
class Purchase(models.Model):
    _inherit = "purchase.order"
    
    
    image_1920 = fields.Image("Image", related="product_id.image_1920",max_width=1920, max_height=1920)

    # resized fields stored (as attachment) for performance
    image_1024 = fields.Image("Image 1024", related="product_id.image_1024", max_width=1024, max_height=1024)
    image_512 = fields.Image("Image 512", related="product_id.image_512", max_width=512, max_height=512)
    image_256 = fields.Image("Image 256", related="product_id.image_256", max_width=256, max_height=256)
    image_128 = fields.Image("Image 128", related="product_id.image_128", max_width=128, max_height=128)
    
    received_product_amount = fields.Float('# ricevuti',compute="_compute_products",help="Prodotti ricevuti in questo ordine")
    order_product_amount = fields.Float('# in ordine',compute="_compute_products",help="Prodotti in questo ordine")
    pending_product_amount = fields.Float('# non consegnati totali',compute="_compute_products",help="Prodotti non ancora consegnati da questo fornitore")
    product_virtual_availability = fields.Float('# forecasted',compute="_compute_products",help="Prodotti previsti in magazzino")
    product_availability = fields.Float('# in stock',compute="_compute_products",help="Prodotti in magazzino")
    picking_name = fields.Char('Picking Name',compute="_picking_name")
    
    product_tmpl_id = fields.Many2one('product.template',related="product_id.product_tmpl_id")
    service_po = fields.Boolean('Service/Component PO')
    parent_po_id = fields.Many2one('purchase.order',string='Parent Purchase Order')
    child_po_ids = fields.One2many('purchase.order','parent_po_id',string="Child Purchase Orders")
    dest_address_id = fields.Many2one('res.partner', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", string='Drop Ship Address',
        help="Put an address if you want to deliver directly from the vendor to the customer. "
             "Otherwise, keep empty to deliver to your own company.",states={
        'purchase': [('readonly', False)],
        'done': [('readonly', False)],
        'cancel': [('readonly', False)],
    })
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, states=READONLY_STATES, change_default=True, tracking=True, domain="[('partner_rank','>',0),'|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="You can find a vendor by its Name, TIN, Email or Internal Reference.")
    category_summary = fields.Text('Summary',compute="_category_summary")
    milor_codes = fields.Char('Milor Codes',compute="_milor_codes",search="_search_milor_codes")
    image_links = fields.Text('Image Links',compute="_image_links")
    product_of_service_id = fields.Many2one('product.product',related="order_line.product_of_service_id")
    next_po_id= fields.Many2one('purchase.order','Next PO',copy=False)
    has_dis = fields.Boolean('Has Dis',default=False)
    
    po_status = fields.Selection([('new','New'),
                                  ('in_charge','In Charge'),
                                  ('partial','Partially Delivered'),
                                  ('spedito','Spedito'),
                                  ('galvanica','Spedito in Galvanica'),     
                                  ('downloaded_txt','TXT Scaricato'),
                                  ('downloaded_stl','STL Scaricato'),
                                  ('delivered','Delivered')],string='PO Status',compute="_po_status")
    
    in_charge = fields.Boolean('In Charge',default=False,tracking=True)
    anomaly_ids = fields.One2many("syd_anomaly.anomaly_picking",'origin_purchase_id')
    purchase_order_type = fields.Selection([('new','New'),
                                           ('qa', 'QA'),
                                           ('ro', 'R/O'),
                                           ('personalized','Personalized'),
                                           ('rework_one','Rework 1'),
                                           ('rework_two', 'Rework 2')], string="Order Type")   
    spedito_da_fornitore = fields.Boolean('Spedito da Fornitore',tracking=True)
    spedito_in_galvanica = fields.Boolean('Spedito in Galvanica',tracking=True)
    qty_total_received = fields.Integer(string="# total received", compute="_compute_total_received", store=True)
    downloaded_txt = fields.Boolean('TXT Scaricato',tracking=True)
    downloaded_stl = fields.Boolean('STL Scaricato',tracking=True)
    delay_days = fields.Integer(string="Delay (in Days)", compute='_set_delay_days')
    purchase_typology = fields.Selection([('mto','Make to Order'),
                                          ('mts', 'Make to Stock')], string="Tipologia")
    
    def _set_delay_days(self):
        for po in self:
            if po.date_approve and po.received_status in ('to_receive','partial'):
                po.delay_days = int((datetime.datetime.now() - po.date_approve).days)
            else:
                po.delay_days = False
                
    @api.depends('picking_ids.move_line_ids_without_package.qty_done')
    def _compute_total_received(self):
        for po in self:
            po.qty_total_received = sum(po.picking_ids.move_line_ids_without_package.mapped('qty_done')) or 0

    def action_close(self):
        for a in self:
            a.child_po_ids.action_close()
        super(Purchase,self).action_close()
    
    def _po_status(self):
        for a in self:
            po_status = 'new'
            if a.received_status == 'to_receive' :
                if a.in_charge :
                    po_status = 'in_charge'
                if a.spedito_da_fornitore:
                    po_status = 'spedito'
                if a.spedito_in_galvanica:
                    po_status = 'galvanica'
                if a.downloaded_txt:
                    po_status = 'downloaded_txt'
                if a.downloaded_stl:
                    po_status = 'downloaded_stl'                
            if a.received_status == 'partial':
                po_status = 'partial'
            if a.received_status == 'received':
                po_status = 'delivered'
            a.po_status = po_status


    def action_launch_sequence(self):
        res = super(Purchase,self).action_launch_sequence()
        self.published_in_portal = False
        return res    
                
            
    def message_delivery(self,message):
        for a in self:
            body = ("Delivery from %s"%self.env.user.partner_id.name) + message
            a.message_post(body=body, subject="Message from %s "%self.env.user.partner_id.name,message_type='comment',subtype='mail.mt_comment',partner_ids=[a.partner_id.id]+a.message_partner_ids.ids)
            if a.next_po_id:
                a.next_po_id.message_post(body=body, subject="Message from %s "%self.env.user.partner_id.name,message_type='comment',subtype='mail.mt_comment',partner_ids=[a.next_po_id.partner_id.id]+a.next_po_id.message_partner_ids.ids)
    
    
    def _image_links(self):
        for a in self:
            image_links = ''
            for p in a.order_line:
                image_links += p.image_links
            a.image_links = image_links

    def _search_milor_codes(self,operator, value):
        recs = self.env['purchase.order.line'].search([('milor_code',operator,value)])
        po_ids = [r.order_id.id for r in recs]
        
        return [('id', 'in', po_ids)]
        

    def _milor_codes(self):
        for order in self.sudo():
            milor_codes = ''
            if not order.service_po:
                for a in order.order_line.filtered(lambda l: not l.display_type):
                    if milor_codes != '':
                        milor_codes +=","
                    milor_codes += a.product_id.milor_code if a.product_id.milor_code else ''
            else:
                for a in order.order_line.filtered(lambda l: not l.display_type):
                    if milor_codes != '':
                        milor_codes +=","
                    milor_codes += a.product_of_service_id.milor_code if a.product_of_service_id.milor_code else ''
            milor_codes += ''
            order.milor_codes = milor_codes
                
    def _category_summary(self):
        for order in self:
            categories = {}
            for a in order.order_line.filtered(lambda l: not l.display_type):
                if a.product_id.categ_id.display_name in categories:
                    categories[a.product_id.categ_id.display_name] += a.product_uom_qty
                else :
                    categories[a.product_id.categ_id.display_name] = a.product_uom_qty
            summary = '<table class="table table-bordered" ><tr><th>Category</th><th>#</th></tr>'
            for key, value in categories.items():
                summary += "<tr><td>%s</td><td>%d</td></tr>" %(key,value)
            summary += '</table>'     
            order.category_summary = summary
            
            
    @api.constrains('order_line','product_tmpl_id','product_of_service_id')
    def _get_purchase_description(self):
        for a in self:
            notes = ''
            if a.product_tmpl_id.description_purchase:
                notes += a.product_tmpl_id.description_purchase or ''
            if a.product_tmpl_id.description:
                if notes :
                    notes += '<br />'
                notes += a.product_tmpl_id.description or ''
            if a.product_of_service_id:
                if notes :
                    notes += '<br />'
                notes += a.product_of_service_id.description or ''
            a.notes =  notes 
            
    @api.onchange('parent_po_id')
    def _autopopolate(self):
        for a in self:
            if a.company_id.default_service_product_id and not a.order_line:
                lines = []
                for line in a.parent_po_id.order_line:
                    lines += [(0, 0, {
                             'product_id':a.company_id.default_service_product_id.id,
                             'product_qty':line.product_qty,
                             'product_of_service_id':line.product_id.id
                             
                             })]
                a.order_line = lines
                
                
    def _get_destination_location(self):
        self.ensure_one()
        return self.picking_type_id.default_location_dest_id.id
    
    @api.onchange('product_id')
    def _change_vendor(self):
            partner_id = False
            if not self.partner_id :
                for s in self.product_id.seller_ids:
                    if not s.date_end or s.date_end < fields.Date.today():
                        partner_id = s.name
                if partner_id:
                    self.partner_id = partner_id.id  
            if not self.partner_id and self.supplier_info_sequence_ids:
                self.partner_id = self.supplier_info_sequence_ids[len(self.supplier_info_sequence_ids)-1].partner_id.id

        
    def _picking_name(self):
        for a in self:
            for p in a.picking_ids:
                a.write({'picking_name':p.name})
                return
                
    def _compute_products(self):
        for a in self:
            order_product_amount = sum(l.product_qty for l in a.order_line)
            
            pending_product_amount = 0.0
            virtual_available= sum(l.product_id.virtual_available for l in a.order_line)
            qty_received= sum(l.qty_received for l in a.order_line)
            qty_available= sum(l.product_id.qty_available for l in a.order_line)
            po_partner = self.search([('partner_id','=',a.partner_id.id),('state','=','purchase')])
            for c in po_partner:
                pending_product_amount += sum((l.product_qty-l.qty_received) for l in c.order_line)
            a.write({
                     'order_product_amount':order_product_amount,
                     'pending_product_amount':pending_product_amount,
                     'product_virtual_availability':virtual_available,
                     'product_availability':qty_available,
                     'received_product_amount':qty_received
                     })

    def send_mail_to_vendors(self):
        for purchases in [self.browse().concat(*g) for k, g in groupbyelem(self.search([('state','=','purchase'),('received_status', 'in', ('to_receive','partial')),('date_approve','!=',False),('commercehub_co','!=',False),('company_id','=',1)]), itemgetter('partner_id'))]:
            try:        
                purchases_order = purchases.sorted(key = lambda r: r.delay_days, reverse=True)
                vendor = purchases.partner_id
                if vendor and purchases_order:
                    data_id = self.create_excel_attachment(purchases_order)
                    template_id = self.env.ref('syd_custom.email_template_test_send').id
                    template = self.env['mail.template'].browse(template_id)
                    template.attachment_ids = [(6,0, [data_id.id])]
                    template.send_mail(vendor.id, force_send=True)
                    template.attachment_ids = [(3, data_id.id)]
            except Exception as ex:
                _logger.info('While sending mail to vendor: %s',str(ex))
                pass

    def create_excel_attachment(self, purchases=False):
        """
            Create Custom Excel Attachment to add into an email template.
        """
        filename = '{}{}{}'.format('purchase_orders_',datetime.datetime.now().strftime('_%Y-%m-%d_%H-%M-%S'),'.xlsx')
        path = os.path.join(tempfile.gettempdir(), filename)
        workbook = xlsxwriter.Workbook(path)
        worksheet = workbook.add_worksheet('Proposal')
        worksheet = self._generate_excel_vendor(worksheet,purchases,workbook)
        workbook.close()
        
        file = open(path,'rb')
        vals = {'name':filename,
                'type':'binary',
                'public':True,
                'datas':base64.b64encode(file.read())
                }
        attachment_id = self.env['ir.attachment'].sudo().create(vals)
        file.close()
        return attachment_id
    
    def _generate_excel_vendor(self,worksheet=False,purchases=False,workbook=False):
        field_labels = [
"Confirmation Date",
"DELAY (Days)",
"Order Reference",
"Vendor",
"Received Status",
"Order Lines/CommerceHub PO",
"Order Lines/Product/Codice Completo QVC",
"Order Lines/Product/Brand",
"Description",
"Order Lines/Custom Value",
"Order Lines/Product/Placcatura",
"Order Lines/Product/Size"
 ]
        
        bold = workbook.add_format({'bold': True})
        bold.set_align('center')
        
        worksheet.set_column(0, len(field_labels), 30)

        row = 0
        col = 0
        
        for label in field_labels:
            worksheet.write(row, col, label, bold)
            col += 1

        row = 1
        col = 0

        fields = []
        # Update Excel sheet for sorting data by QVC complete code, Delay
        purchase_order_list = []
        for po in purchases:
            for line in po.order_line.filtered(lambda x: x.product_po_id):
                size = line.product_po_id.product_template_attribute_value_ids.filtered(
                    lambda x: "SIZE" in x.attribute_id.with_context(lang=u'en_US').name.upper())
                purchase_order_list.append({'confirmation_date': po.date_approve, 'delay': po.delay_days,
                                            'reference': po.name, 'vendor': po.partner_id.display_name,
                                            'received_state': dict(self._fields['received_status'].selection).get(
                                                po.received_status),
                                            'commercehub_po': po.commercehub_po or '',
                                            'qvc_complete_code': line.product_po_id.qvc_complete_code or '',
                                            'product_brand': line.product_po_id.product_tmpl_id.product_brand_id.name,
                                            'description': line.product_po_id.name or '',
                                            'custom_value': line.custom_value or '',
                                            'placcatura': line.product_po_id.plating_id.name or '',
                                            'size': size[0].name if size else ''})
        sorted_purchase_order_list = sorted(purchase_order_list,
                                            key=lambda x: (x.get('qvc_complete_code'), x.get('delay')), reverse=True)
        for purchase_order_dict in sorted_purchase_order_list:
            worksheet.set_row(row, 98)
            worksheet.write(row, 0, '{}'.format(purchase_order_dict.get('confirmation_date')))
            worksheet.write(row, 1, '{}'.format(purchase_order_dict.get('delay')))
            worksheet.write(row, 2, '{}'.format(purchase_order_dict.get('reference')))
            worksheet.write(row, 3, '{}'.format(purchase_order_dict.get('vendor')))
            worksheet.write(row, 4, purchase_order_dict.get('received_state'))
            worksheet.write(row, 5, '{}'.format(purchase_order_dict.get('commercehub_po')))
            worksheet.write(row, 6, purchase_order_dict.get('qvc_complete_code'))
            worksheet.write(row, 7, purchase_order_dict.get('product_brand'))
            worksheet.write(row, 8, purchase_order_dict.get('description'))
            worksheet.write(row, 9, purchase_order_dict.get('custom_value'))
            worksheet.write(row, 10, purchase_order_dict.get('placcatura'))
            worksheet.write(row, 11, purchase_order_dict.get('size'))

            row += 1
        return worksheet
        # for po in purchases:
        #     for line in po.order_line.filtered(lambda x: x.product_po_id):
        #         worksheet.set_row(row, 98)
        #         worksheet.write(row, 0, '{}'.format(po.date_approve))
        #         worksheet.write(row, 1, '{}'.format(po.delay_days))
        #         worksheet.write(row, 2, '{}'.format(po.name))
        #         worksheet.write(row, 3, '{}'.format(po.partner_id.display_name))
        #         worksheet.write(row, 4, dict(self._fields['received_status'].selection).get(po.received_status))
        #         worksheet.write(row, 5, '{}'.format(po.commercehub_po or ''))
        #         worksheet.write(row, 6, line.product_po_id.qvc_complete_code or '')
        #         worksheet.write(row, 7, line.product_po_id.product_tmpl_id.product_brand_id.name or '')
        #         worksheet.write(row, 8, line.product_po_id.name or '')
        #         worksheet.write(row, 9, line.custom_value or '')
        #         worksheet.write(row, 10, line.product_po_id.plating_id.name or '')
        #         size = line.product_po_id.product_template_attribute_value_ids.filtered(lambda x: "SIZE" in x.attribute_id.with_context(lang=u'en_US').name.upper())
        #         worksheet.write(row, 11, size[0].name if size else '')
        #
        #         row += 1
        # return worksheet
        
    def unlink(self):
        for order in self:
            if not self.env.user.has_group('base.group_system'):
                raise UserError("You do not have access to trigger this action")
        return super(Purchase, self).unlink()

    def set_custom_value_related_pickings(self):
        for purchase in self:
            for p_ol in purchase.order_line.filtered(lambda x: x.custom_value):
                for move_line in purchase.picking_ids.move_ids_without_package.filtered(lambda x: x.product_id == p_ol.product_po_id):
                    move_line.custom_value = p_ol.custom_value

class QualityCheck(models.Model):
    _inherit = "syd_quality.check"
    
    
    date_deadline_from = fields.Date('Date Deadline From',related="picking_id.date_deadline_from")
    date_deadline_to = fields.Date('Date Deadline To',related="picking_id.date_deadline_to")
    
class StockRule(models.Model):
    _inherit = 'stock.rule'
    
    
    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        val = super(StockRule,self)._get_stock_move_values( product_id, product_qty, product_uom, location_id, name, origin, company_id, values)   
        group_id = values.get('group_id', False) and values['group_id']
        move_dest_ids = values.get('move_dest_ids', False) and values['move_dest_ids']
        if group_id:
            val['date_deadline_from']=group_id.sale_id.date_deadline_from if group_id and group_id.sale_id and group_id.sale_id.date_deadline_from else False
            val['date_deadline_to']=group_id.sale_id.date_deadline_to if group_id and group_id.sale_id and group_id.sale_id.date_deadline_to else False
            if move_dest_ids:
                for m in move_dest_ids:
                    m.write({
                             'date_deadline_from':group_id and group_id.sale_id and group_id.sale_id.date_deadline_from,
                             'date_deadline_to':group_id and group_id.sale_id and group_id.sale_id.date_deadline_to
                             })
        return val
    
    
    #generate every time a new RFQ for a new product MTO (not add on existing rfq)
    def _make_po_get_domain(self, company_id, values, partner):
        domain = super(StockRule,self)._make_po_get_domain(company_id,values,partner)
#         domain += (('approval_state','=','blocked'),)
        supplier = 'supplier' in values and values['supplier']        
        order_id = 'sale_line_id' in values and values['sale_line_id'].order_id  
        if (supplier and supplier.product_tmpl_id and (not order_id or (order_id and not order_id.as2_stream_id))):
            domain +=(('product_tmpl_id','=',supplier.product_tmpl_id.id),('as2_stream_id','=',False),)
        else:
            domain +=((True,'=',False))
        return domain
    
    
class OrderLine(models.Model):
    _inherit = "sale.order.line"
    
    image_1920 = fields.Image("Image", related="product_id.image_1920",max_width=1920, max_height=1920)

    # resized fields stored (as attachment) for performance
    image_1024 = fields.Image("Image 1024", related="product_id.image_1024", max_width=1024, max_height=1024)
    image_512 = fields.Image("Image 512", related="product_id.image_512", max_width=512, max_height=512)
    image_256 = fields.Image("Image 256", related="product_id.image_256", max_width=256, max_height=256)
    image_128 = fields.Image("Image 128", related="product_id.image_128", max_width=128, max_height=128)
    display_qty_widget = fields.Boolean(compute='_display_qty_widget')
    retail_price = fields.Monetary('Retail Price', compute="_compute_retail_price")
    
    """
        For big customer
    """
    was_bought = fields.Boolean(string="Was Bought?", compute='_set_last_mean_price_bigcustomer',store=True)
    last_price = fields.Float(string='Last price', compute='_set_last_mean_price_bigcustomer',store=True)
    mean_price = fields.Float(string='Mean Price', compute='_set_last_mean_price_bigcustomer',store=True)
    product_cost = fields.Float(related="product_id.standard_price", string="Cost", store=True)
    
    @api.depends('order_id.state','order_id.partner_id','order_id.partner_id.big_customer')
    def _set_last_mean_price_bigcustomer(self):
        for i,sale_order_line_id in enumerate(self):
            if sale_order_line_id.order_id.state in ['sale','done'] and sale_order_line_id.order_id.partner_id.big_customer:
                if i == 0:
                    sale_order_line_id.order_id.partner_id.set_prodotti_collegati()
                """
                    First of all update the products table: set_prodotti_collegati
                """
                line = sale_order_line_id.order_id.partner_id.prodotti_collegati.filtered(lambda x: x.products_id == sale_order_line_id.product_id)
                sale_order_line_id.was_bought = bool(line)
                sale_order_line_id.last_price = line.last_price if bool(line) else False
                sale_order_line_id.mean_price = line.mean_price if bool(line) else False
            else:
                sale_order_line_id.was_bought = False
                sale_order_line_id.last_price = False
                sale_order_line_id.mean_price = False
    
    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        if self.order_id.split_by_brand and len(self.filtered(lambda p : p.product_id.product_brand_id.id == False))==0:
            for a in set(self.mapped('product_id.product_brand_id.id')):
                super(OrderLine,self.filtered(lambda p : p.product_id.product_brand_id.id == a))._action_launch_stock_rule(previous_product_uom_qty)
            return True
        else:
            return super(OrderLine,self)._action_launch_stock_rule(previous_product_uom_qty)

    def _compute_retail_price(self):
        for rec in self:
            pl = rec.order_id.pricelist_id and rec.order_id.pricelist_id.retail_pricelist_id or rec.order_id.pricelist_id
            res = pl.price_get(rec.product_id.id, 1)
            if pl.item_ids:
                if pl.item_ids[0].base_pricelist_id:
                    res = pl.item_ids[0].base_pricelist_id.price_get(rec.product_id.id, 1)
                    rec.retail_price = res.get(pl.item_ids[0].base_pricelist_id.id, 0)
                else:
                    rec.retail_price = res.get(pl.id, 0)
            else:
                rec.retail_price = res.get(pl.id, 0)

    def _display_qty_widget(self):
        """Compute the visibility of the inventory widget."""
        for line in self:
            if line.state in ('draft','sent') and line.product_type == 'product' and line.qty_to_deliver >0: 
                line.display_qty_widget = True
            else:
                line.display_qty_widget = False
                
    def _prepare_procurement_group_vals(self):
        res = super(OrderLine,self)._prepare_procurement_group_vals()
        res['name'] = self.order_id.display_name
        return res




class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    stone_name = fields.Char('Stone Name',compute="_stone_name")
    barcode_text = fields.Char('Barcode Text',related="product_brand_id.barcode_text")
    fixed_virtual_available = fields.Float(
        'Yesterday Forecast Quantity (Variant)')

    fixed_quantity_date = fields.Datetime('Fixed Quantity Date')
    
    dis_ids = fields.One2many('product.dis','product_id',string='Dis')
    dis_code = fields.Char('Dis Code',store=True,compute="_dis_code")
    
    last_cost_update = fields.Datetime("Last Cost Update")
    
    total_dis_ids = fields.Many2many('product.dis',compute="_total_ids")
    dotcom_qvc = fields.Boolean(string="DOTCOM QVC")
    conferma_acq_auto = fields.Boolean(string="Conferma Acquisto In Automatico")
    note_personalized = fields.Text(string="Note Personalized")
    
    def _total_ids(self):
        self.ensure_one()
        total_id = []
        for d in self.dis_ids:
            total_id.append(d.id)
        for d in self.product_tmpl_id.template_dis_ids:
            total_id.append(d.id)
        for b in self.bom_ids:
            for l in b.bom_line_ids:
                for d in l.product_id.total_dis_ids:
                    total_id.append(d.id)
        for b in self.variant_bom_ids:
            for l in b.bom_line_ids:
                for d in l.product_id.total_dis_ids:
                    total_id.append(d.id)
        self.total_dis_ids = total_id
            
    
    @api.depends('dis_ids.name','product_tmpl_id.template_dis_ids.name')
    def _dis_code(self):
        for a in self:
            a.dis_code = a.dis_ids[0].name if a.dis_ids else (a.product_tmpl_id.template_dis_ids[0].name if a.template_dis_ids else False)
            
    
    def archive_and_delete_reordering(self):
        for a in self:
            if a.orderpoint_ids:
                if a.free_qty >0 :
                    raise ValidationError(_('Product with positive stock!!'))
                a.orderpoint_ids.unlink()
            a.write({'active':False})
                
    def calculated_fixed_quantity(self):
        products = self.read(['virtual_available','id'])
        for p in products:
            self.env['product.product'].browse(p.get('id')).write({
                                                                   'fixed_virtual_available':p.get('virtual_available'),
                                                                   'fixed_quantity_date':fields.Datetime.now()
                                                                   })

    
    def _get_images(self):
        """Return a list of records implementing `image.mixin` to
        display on the carousel on the website for this template.
        This returns a list and not a recordset because the records might be
        from different models (template and image).
        It contains in this order: the main image of the template and the
        Template Extra Images.
        """
        self.ensure_one()
        res= {}
        for p in self.product_variant_image_ids:
            res[p.name]= p
        if list(res.values()):
            return list(res.values())
        else :
            return [self]
    
    def _stone_name(self):
        for a in self:
            stone_name = ''
            for s in a.stone_ids:
                if stone_name != '':
                    stone_name += ","
                stone_name += s.name
            a.stone_name = stone_name
        
    def clean_images(self):
        self.ept_image_ids.unlink()
        
    def create_order_from_products(self):
        wizard_id = self.env['syd_custom.wizard_order'].create({
                                                   'product_ids':self.ids
                                                   })
        
        action = self.env['ir.actions.act_window'].for_xml_id('syd_custom', 'action_order_creation_helper')
        action['res_id'] = wizard_id.id
        
        return action
    
    
    def create_purchase_order_from_products(self):
        partner_id = False
        if self:
            if self[0].seller_ids:
                partner_id = self[0].seller_ids[0].name.id
        wizard_id = self.env['syd_custom.wizard_purchase_order'].create({
                                                   'product_ids':self.ids,
                                                   'partner_id':partner_id
                                                   })
        
        action = self.env['ir.actions.act_window'].for_xml_id('syd_custom', 'action_purchase_order_creation_helper')
        action['res_id'] = wizard_id.id
        
        return action

    # INFO: overwrites original get_all_products_by_barcode to really speedup barcodes loading to client side.
    @api.model
    def get_all_products_by_barcode(self):
        qry = """select
                    pp.id, pp.barcode, '[' || pp.default_code || '] ' || pt.name as display_name, pt.uom_id, pt.tracking
                from
                    product_product as pp, product_template as pt
                where
                    pp.product_tmpl_id = pt.id and pp.barcode != '';"""
        self._cr.execute(qry)
        products = self._cr.dictfetchall()
        for p in products:
            uom_id  = p['uom_id']
            uom_id =  self.env['uom.uom'].browse(uom_id)
            p['uom_id'] = (uom_id.id,uom_id.name)
        packagings = self.env['product.packaging'].search_read(
            [('barcode', '!=', None), ('product_id', '!=', None)],
            ['barcode', 'product_id', 'qty']
        )
        # for each packaging, grab the corresponding product data
        to_add = []
        to_read = []
        products_by_id = {product['id']: product for product in products}
        for packaging in packagings:
            if products_by_id.get(packaging['product_id']):
                product = products_by_id[packaging['product_id']]
                to_add.append(dict(product, **{'qty': packaging['qty']}))
            # if the product doesn't have a barcode, you need to read it directly in the DB
            to_read.append((packaging, packaging['product_id'][0]))
        products_to_read = self.env['product.product'].browse(list(set(t[1] for t in to_read))).sudo().read(
            ['display_name', 'uom_id', 'tracking'])
        products_to_read = {product['id']: product for product in products_to_read}
        to_add.extend([dict(t[0], **products_to_read[t[1]]) for t in to_read])
        return {product.pop('barcode'): product for product in products + to_add}

    def activate_fuori_collezione(self):
        if not self.env.user.has_group('syd_custom.group_fuori_collezione'):
            raise ValidationError("You do not have access to trigger this action")
        else:
            for variant in self:
                variant.out_of_collection_variant = True

    def deactivate_fuori_collezione(self):
        if not self.env.user.has_group('syd_custom.group_fuori_collezione'):
            raise ValidationError("You do not have access to trigger this action")
        else:
            for variant in self:
                variant.out_of_collection_variant = False

class QuantPackage(models.Model):
    _inherit = "stock.quant.package"
    
    total_goods = fields.Float('Total Qty',compute="_totals")
    partner_id = fields.Many2one('res.partner',string='Partner',compute="_partner")
    
    @api.depends('stock_quant_packing_list_ids')
    def _partner(self):
        for a in self:
            partner_id = False
            if a.stock_quant_packing_list_ids:
                partner_id =  a.stock_quant_packing_list_ids[0].stock_move_line_id and a.stock_quant_packing_list_ids[0].stock_move_line_id.move_id and a.stock_quant_packing_list_ids[0].stock_move_line_id.move_id.partner_id.id
            a.partner_id = partner_id    
            
    def _totals(self):
        for pack in self:
            
            total_goods=0.0
            for a in pack.stock_quant_packing_list_ids:
                if not a.packing_product_id.is_packaging:
                    total_goods += a.qty
            pack.write({
                           'total_goods':total_goods
                           
                           })

class StockQuant(models.Model):
    _inherit = "stock.quant"
               
    product_category_id = fields.Many2one('product.category',string='Product Category',related="product_id.categ_id",store=True) 
    product_brand_id = fields.Many2one('common.product.brand.ept',related="product_id.product_brand_id",string='Brand',store=True)  

    quantity = fields.Float(
        'Quantity',
        help='Quantity of products in this quant, in the default unit of measure of the product',
        readonly=True,digits='Product Unit of Measure')
    inventory_quantity = fields.Float(
        'Inventoried Quantity', compute='_compute_inventory_quantity',
        inverse='_set_inventory_quantity', groups='stock.group_stock_manager',digits='Product Unit of Measure')
    reserved_quantity = fields.Float(
        'Reserved Quantity',
        default=0.0,
        help='Quantity of reserved products in this quant, in the default unit of measure of the product',
        readonly=True, required=True,digits='Product Unit of Measure')
    
    image_1024 = fields.Image("Image 1024", related="product_id.image_1024", max_width=1024, max_height=1024)
    image_512 = fields.Image("Image 512", related="product_id.image_512", max_width=512, max_height=512)
    image_256 = fields.Image("Image 256", related="product_id.image_256", max_width=256, max_height=256)
    image_128 = fields.Image("Image 128", related="product_id.image_128", max_width=128, max_height=128)
    
    virtual_available = fields.Float('Forecasted Quantity',related="product_id.virtual_available",
        digits='Product Unit of Measure')
    

    
class Order(models.Model):
    _inherit = "sale.order"
    
    
    
    
    date_deadline_from = fields.Date('Date Deadline From')
    date_deadline_to = fields.Date('Date Deadline To')
    image_1920 = fields.Image("Image", related="product_id.image_1920",max_width=1920, max_height=1920)
    product_id = fields.Many2one('product.product',related="order_line.product_id")
    # resized fields stored (as attachment) for performance
    image_1024 = fields.Image("Image 1024", related="product_id.image_1024", max_width=1024, max_height=1024)
    image_512 = fields.Image("Image 512", related="product_id.image_512", max_width=512, max_height=512)
    image_256 = fields.Image("Image 256", related="product_id.image_256", max_width=256, max_height=256)
    image_128 = fields.Image("Image 128", related="product_id.image_128", max_width=128, max_height=128)
    
    confirmed_not_payed = fields.Monetary('Confermato Non Pagato',compute="_compute_customer_status")
    invoiced_not_payed = fields.Monetary('Fatturato Non Pagato',compute="_compute_customer_status")
    dued_not_payed = fields.Monetary('Scaduto',compute="_compute_customer_status")
    partner_pricelist_id = fields.Many2one('product.pricelist','Customer Pricelist',related="partner_id.property_product_pricelist",readonly=True)
    partner_payment_term_id = fields.Many2one('account.payment.term','Customer Payment Term',related="partner_id.property_payment_term_id",readonly=True)
    commercial_warning = fields.Boolean('Commercial Warning',compute="_commercial_warning",store=True)
    inventory_warning = fields.Boolean('Inventory Warning',compute="_inventory_warning",search='_inventory_warning_search')
    category_summary = fields.Text('Summary',compute="_category_summary")
    product_brand_id = fields.Many2one('common.product.brand.ept', string="Brand", compute="_first_product_brand",store=True,
                                       help='Select a brand for this product.')
    split_by_brand = fields.Boolean('Split by Brand',default=True)
    big_customer = fields.Boolean(related='partner_id.big_customer')
    total_cost = fields.Float(compute='_compute_total_cost', string="Total Cost", store=True)
    
    @api.depends('order_line.product_cost','order_line.product_uom_qty')
    def _compute_total_cost(self):
        for sale_id in self:
            sale_id.total_cost = sum(ol.product_cost * ol.product_uom_qty for ol in sale_id.order_line)

    @api.depends('order_line.product_id')
    def _first_product_brand(self):
        for a in self:
            if a.order_line:
                a.product_brand_id = a.order_line[0].product_id.product_brand_id.id
            else:
                a.product_brand_id = False    
                
                
    def confirm_without_action(self):
        for a in self:
            a.write({
            'state': 'sale',
            'date_order': fields.Datetime.now()
        }) 
            if self.env.user.has_group('sale.group_auto_done_setting'):
                a.action_done()
        
    
    def action_recreate_transfer(self):
        for a in self:
            a.order_line.filtered(lambda l: len(l.move_ids)==0)._action_launch_stock_rule()
    
    def _category_summary(self):
        for order in self:
            categories = {}
            for a in order.order_line.filtered(lambda l: not l.display_type):
                if a.product_id.categ_id.display_name in categories:
                    categories[a.product_id.categ_id.display_name] += a.product_uom_qty
                else :
                    categories[a.product_id.categ_id.display_name] = a.product_uom_qty
            summary = '<table class="table table-bordered" ><tr><th>Category</th><th>#</th></tr>'
            for key, value in categories.items():
                summary += "<tr><td>%s</td><td>%d</td></tr>" %(key,value)
            summary += '</table>'     
            order.category_summary = summary
            
            
    @api.onchange('pricelist_id')
    def change_pricelist(self):
        for a in self:
            a.recalculate_price()
    
    def recalculate_price(self):
        for a in self:
            if a.state != 'sale':
                for line in a.order_line:
                    name = line.name
                    line.product_id_change()
                    line.name = name
    
    def _inventory_warning(self):
        for a in self:
            iw = False
            if a.state != 'sale':
                for line in a.order_line:
                     if not iw and line.product_uom_qty > line.product_id.free_qty:
                         iw=True
            a.inventory_warning = iw
                     
    def _inventory_warning_search(self,operator, value):
        recs = self.search([(True,'=',True)]).filtered(lambda x : x.inventory_warning is True )
        if recs:
            return [('id', 'in', recs.ids)]
        else:
            return []
         
    
    @api.depends('partner_id.property_product_pricelist','partner_id.property_payment_term_id','pricelist_id','payment_term_id')
    def _commercial_warning(self):
        for a in self:
            a.commercial_warning = a.partner_pricelist_id.id != a.pricelist_id.id or a.partner_payment_term_id.id != a.payment_term_id.id
            
    
    def name_get(self):
        res = []
        for order in self:
            name = '%s' % (order.name)
            if order.source_id and order.origin:
                name += ' (%s:%s)' % (order.source_id.name,order.origin)
            elif order.origin:
                name += ' (%s)' % (order.origin)
            elif order.source_id:
                name += ' (%s)' % (order.source_id.name)
            res.append((order.id, name))
        return res
    
    @api.constrains('date_deadline_from')
    def _expected_date_deadline(self):
        for a in self:
            if a.date_deadline_from and a.expected_date:
                if a.date_deadline_from > a.expected_date.date():
                     a.commitment_date = a.date_deadline_from
                 
    @api.onchange('partner_id')
    def onchange_partner_set_agent(self):
        if bool(self.partner_id):
            if bool(self.partner_id.salesman_partner_id):
                self.salesman_partner_id = self.partner_id.salesman_partner_id
            else:
                self.salesman_partner_id = False  
        
    def _compute_customer_status(self):
        for a in self:
            confirmed_not_payed= 0.0
            invoiced_not_payed= 0.0
            dued_not_payed = 0.0
            orders = self.env['sale.order'].sudo().search([('partner_id','=',a.partner_id.id),('state','=','sale')])
            for o in orders:
                payed = 0.0
                for f in o.invoice_ids:
                    payed += (f.amount_total - f.amount_residual)
                    invoiced_not_payed += f.amount_residual
                    if (f.invoice_date_due > fields.Date.today()):
                        dued_not_payed += f.amount_residual
                confirmed_not_payed += o.amount_total - payed
                
            invoices = self.env['account.move'].sudo().search([('partner_id','=',a.partner_id.commercial_partner_id.id),('type','=','out_invoice'),('amount_residual','>',0),('invoice_origin','=',False)])
            for f in invoices:
                    invoiced_not_payed += f.amount_residual
                    if (f.invoice_date_due > fields.Date.today()):
                        dued_not_payed += f.amount_residual
            a.write({
                     'confirmed_not_payed':confirmed_not_payed,
                     'invoiced_not_payed':invoiced_not_payed,
                     'dued_not_payed':dued_not_payed
                     })
            
    def unlink(self):
        for order in self:
            if not self.env.user.has_group('base.group_system'):
                raise UserError("You do not have access to trigger this action")
        return super(Order, self).unlink()            
            
class SaleReport(models.Model):
    _inherit = "sale.report"

    collection_id = fields.Many2one('product.collection',string="Collezione",readonly=True)
    product_brand_id = fields.Many2one('common.product.brand.ept', string="Brand",readonly=True)
    salesman_partner_id = fields.Many2one(comodel_name='res.partner', string='Agent',readonly=True)
    qty_to_deliver = fields.Float(string='Qty To Deliver', readonly=True)
    total_cost = fields.Float(string="Total Cost", readonly=True)
    untaxed_shipped_total = fields.Float(string="Untaxed Shipped Total", readonly=True)
    untaxed_to_deliver_total = fields.Float(string="Untaxed To Deliver Total", readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['collection_id'] = ", t.collection_id as collection_id"
        fields['product_brand_id'] = ", t.product_brand_id as product_brand_id"
        fields['salesman_partner_id'] = ", s.salesman_partner_id as salesman_partner_id"
        fields['qty_to_deliver'] = ", sum(l.product_uom_qty - l.qty_delivered) as qty_to_deliver"
        fields['total_cost'] = ", sum(l.product_cost * l.product_uom_qty) as total_cost"
        fields['untaxed_shipped_total'] = ", sum(l.qty_delivered * l.price_unit) as untaxed_shipped_total"
        fields['untaxed_to_deliver_total'] = ", sum((l.product_uom_qty - l.qty_delivered) * l.price_unit) as untaxed_to_deliver_total"
        groupby += ', t.collection_id, t.product_brand_id,s.salesman_partner_id'
        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)           
     
class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    collection_id = fields.Many2one('product.collection',string="Collezione",readonly=True)
    product_brand_id = fields.Many2one('common.product.brand.ept', string="Brand",readonly=True)

    def _select(self):
        return super(PurchaseReport, self)._select() + ", t.product_brand_id as product_brand_id, t.collection_id as collection_id"


    def _group_by(self):
        return super(PurchaseReport, self)._group_by() + ", t.product_brand_id, t.collection_id"


class StockChangeStandPrice(models.TransientModel):
    _inherit = 'stock.change.standard.price'
    
    def change_price(self):
        """ Changes the Standard Price of Product and creates an account move accordingly. """
        self.ensure_one()
        if self._context['active_model'] == 'product.template':
            products = self.env['product.template'].browse(self._context['active_id']).product_variant_ids
        else:
            products = self.env['product.product'].browse(self._context['active_id'])
        old_cost = products.standard_price
        products._change_standard_price(self.new_price, counterpart_account_id=self.counterpart_account_id.id)
        body_msg = _(
            "The cost was updated:") + """
                                            <br><span>&bull; Cost: &nbsp; %s <span class='fa fa-long-arrow-right'/>&nbsp; %s </span>
                                            <br><span>&bull; Update date: &nbsp; %s</span>
                                          """ % (
                                            old_cost, self.new_price, datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")) 
        
        if old_cost != self.new_price:
            for product in products:
                product.message_post(body=body_msg)
                product.last_cost_update = datetime.datetime.utcnow()
            if self._context['active_model'] == 'product.template':
                products[0].product_tmpl_id.message_post(body=body_msg)
                products[0].product_tmpl_id.last_cost_update = datetime.datetime.utcnow()
                
        return {'type': 'ir.actions.act_window_close'}


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'
    
    retail_pricelist_id = fields.Many2one('product.pricelist',string='Retail Pricelist')


class productSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    note_vendor = fields.Text(string='Note Vendor')


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    payment_gateway = fields.Many2one('shopify.payment.gateway.ept', string="Payment Gateway", copy=False, compute='_set_payment_gateway')
    customer_country = fields.Many2one('res.country', related='partner_shipping_id.country_id')
    customer_region = fields.Many2one('res.country.state', string='State', compute='_get_city_italy')
    
    def _get_city_italy(self):
        for rec in self:
            rec.customer_region = rec.partner_shipping_id.filtered(lambda x: x.country_id.code == 'IT').state_id
        
    def _set_payment_gateway(self):
        for a in self:
            a.payment_gateway = (a.env['sale.order'].search([('name','ilike',a.ref.split(',')[0] if a.ref else a.invoice_origin.split(',')[0])], limit=1).shopify_payment_gateway_id or False) if bool(a.ref or a.invoice_origin) else False


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def on_barcode_scanned(self, barcode):
        if not self.env.company.nomenclature_id:
            product = self.env['product.product'].search([('qvc_complete_code', '=', barcode)], limit=1)
            if product:
                if self._check_product(product):
                    return
        else:
            parsed_result = self.env.company.nomenclature_id.parse_barcode(barcode)
            if parsed_result['type'] in ['weight', 'product']:
                if parsed_result['type'] == 'weight':
                    product_barcode = parsed_result['base_code']
                    qty = parsed_result['value']
                else:
                    product_barcode = parsed_result['code']
                    qty = 1.0
                product = self.env['product.product'].search([('qvc_complete_code', '=', product_barcode)], limit=1)
                if product:
                    if self._check_product(product, qty):
                        return

        return super(StockPicking, self).on_barcode_scanned(barcode)


    def unlink(self):
        for order in self:
            if not self.env.user.has_group('base.group_system'):
                raise UserError("You do not have access to trigger this action")
        return super(StockPicking, self).unlink()

class ProductTags(models.Model):
    _name = "product.tags"
    _description = 'Product Tags'

    name = fields.Char("Name", required=1)
    sequence = fields.Integer("Sequence", required=1) 
    
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_fuori_collezione = fields.Boolean("Group Fuori Collezione", implied_group='syd_custom.group_fuori_collezione')
    group_double_checking_po_visibility = fields.Boolean("Activate double check while Validating/Cancelling PO", implied_group='syd_custom.group_double_checking_po_visibility', help='Checking this field activate the double checking on deleting a Purchase Order.') 
    group_double_checking_so_visibility = fields.Boolean("Activate double check while Validating/Cancelling SO", implied_group='syd_custom.group_double_checking_so_visibility', help='Checking this field activate the double checking on deleting a Sale Order.') 
    group_double_checking_do_visibility = fields.Boolean("Activate double check while Validating/Cancelling DO", implied_group='syd_custom.group_double_checking_do_visibility', help='Checking this field activate the double checking on deleting a Delivery Order.') 
    group_administrator_visibility = fields.Boolean("Activate double check while Validating/Cancelling DO", implied_group='syd_custom.group_administrator_visibility', help='Allow administrator to cancel orders.')

    show_gls_contrassegno = fields.Boolean(
        help='Set automatically GLS CONTRASSEGNO on orders with Cash On Delivery(Cod)',
        string='GLS CONTRASSEGNO',
        config_parameter='gls_config_settings.show_gls_contrassegno'
    )
class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    po_column = fields.Selection([('taglia','Taglia'),
                                  ('pietra','Pietra'),
                                  ('placcatura','Placcatura')])

class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    def assign_carrier(self, carrier_name):
        carrier_id = self.env['delivery.carrier'].sudo().search([('name', '=', carrier_name)], limit=1)
        if carrier_id:
            for picking in self.picking_ids:
                picking.carrier_id = carrier_id

    def action_confirm(self):
        res = super(SaleOrderInherit, self).action_confirm()
        show_gls = self.env['ir.config_parameter'].sudo().get_param('gls_config_settings.show_gls_contrassegno', 'False') == 'True'
        if show_gls:
            shopify_payment_gateway_name = self.env['ir.config_parameter'].sudo().get_param('shopify.payment.gateway', 'Cash on Delivery (COD)')
            if self.shopify_payment_gateway_id.name == shopify_payment_gateway_name:
                carrier_name = self.env['ir.config_parameter'].sudo().get_param('carrier.name.contrassegno', 'GLS CONTRASSEGNO')
                self.assign_carrier(carrier_name)
        return res

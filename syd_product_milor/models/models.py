# -*- coding: utf-8 -*-
# © 2019 SayDigital s.r.l.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import datetime, calendar
from dateutil.relativedelta import relativedelta
from odoo import api, exceptions, fields, models, _,SUPERUSER_ID, registry
from odoo.exceptions import UserError, AccessError, ValidationError
from werkzeug import urls
import calendar
from odoo import tools
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_join
from odoo.osv import expression
import json

import logging
_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = 'res.company'
    
    
    uom_cm_id = fields.Many2one('uom.uom',string="Unità di misura cm",default=lambda self: self.search([('name','=','cm')],limit=1))
    uom_inch_id = fields.Many2one('uom.uom',string="Unità di misura inch",default=lambda self: self.search([('name','=','inches')],limit=1))
    uom_gr_id = fields.Many2one('uom.uom',string="Unità di misura gr",default=lambda self: self.search([('name','=','g')],limit=1))
    uom_ct_id = fields.Many2one('uom.uom',string="Unità di misura carati",default=lambda self: self.search([('name','=','ct')],limit=1))


class MilorFinish(models.Model): 
    _name='product.finish'
    _description = 'Finish'
    
    name = fields.Char('Name',required=True)

class MilorShow(models.Model): 
    _name='product.milor_show'
    _description = 'Show'
    
    name = fields.Char('Name',required=True)

class MilorUnit(models.Model): 
    _name='product.milor_unit'
    _description = 'Milor Unit'
    
    name = fields.Char('Name',required=True)
    
class StoneType(models.Model): 
    _name='product.stone_type'
    _description = 'Stone Type'
    
    name = fields.Char('Name',translate=True,required=True)
    
class StoneShape(models.Model): 
    _name='product.stone_shape'
    _description = 'Stone Shape'
    
    name = fields.Char('Name',required=True)

class StoneCut(models.Model): 
    _name='product.stone_cut'
    _description = 'Stone Cut'
    
    name = fields.Char('Name',required=True)

class Feature(models.Model):
    _name = 'product.feature'
    _description = 'Feature'
    
    name = fields.Char('Name', translate=True,required=True)
    for_shopify = fields.Boolean('Tag to Shopify')

class Trend(models.Model):
    _name = 'product.trend'
    _description = 'Trend'
    
    name = fields.Char('Name', translate=True,required=True)


class ClosureType(models.Model):
    _name = 'product.closure_type'
    _description = 'Closure Type'
    
    name = fields.Char('Name', translate=True,required=True)

class Rolo(models.Model):
    _name = 'product.rolo'
    _description = 'Tipo Catena'
    
    name = fields.Char('Name', translate=True,required=True)

class WatchType(models.Model):
    _name = 'product.watch_type'
    _description = 'Watch Type'
    
    name = fields.Char('Name',required=True)


     
class HTS(models.Model):
    _name = 'product.hts'
    _description = 'HTS'
    
    name = fields.Char('Name',required=True)
    duty = fields.Float("Dazio",digits='Stock Weight')
    code = fields.Char("HTS Code")
    duty_extra = fields.Float("Dazio Extra",digits='Stock Weight')
    spedition_cost = fields.Float('Spese Spedizione')
    metal_id = fields.Many2one('product.metal','Metallo')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)

class Stamp(models.Model):
    _name = 'product.stamp'
    _description = 'Stamp'
    _inherit = ['image.mixin']
    
    name = fields.Char('Name',required=True)
    milor_unit_id = fields.Many2one('product.milor_unit',string="Milor Unit")
    
    image_1920_2 = fields.Image("Image 2 ", max_width=1920, max_height=1920)

    # resized fields stored (as attachment) for performance
    image_1024_2 = fields.Image("Image 2 1024", related="image_1920_2", max_width=1024, max_height=1024, store=True)
    image_512_2 = fields.Image("Image 2 512", related="image_1920_2", max_width=512, max_height=512, store=True)
    image_256_2 = fields.Image("Image 2 256", related="image_1920_2", max_width=256, max_height=256, store=True)
    image_128_2 = fields.Image("Image 2 128", related="image_1920_2", max_width=128, max_height=128, store=True)
    
    
    image_1920_3 = fields.Image("Image 3", max_width=1920, max_height=1920)

    # resized fields stored (as attachment) for performance
    image_1024_3 = fields.Image("Image 3 1024", related="image_1920_3", max_width=1024, max_height=1024, store=True)
    image_512_3 = fields.Image("Image 3 512", related="image_1920_3", max_width=512, max_height=512, store=True)
    image_256_3 = fields.Image("Image 3 256", related="image_1920_3", max_width=256, max_height=256, store=True)
    image_128_3 = fields.Image("Image 3 128", related="image_1920_3", max_width=128, max_height=128, store=True)
    
    image_1920_4 = fields.Image("Image 4 ", max_width=1920, max_height=1920)

    # resized fields stored (as attachment) for performance
    image_1024_4 = fields.Image("Image 4 1024", related="image_1920_4", max_width=1024, max_height=1024, store=True)
    image_512_4 = fields.Image("Image 4 512", related="image_1920_4", max_width=512, max_height=512, store=True)
    image_256_4 = fields.Image("Image 4 256", related="image_1920_4", max_width=256, max_height=256, store=True)
    image_128_4 = fields.Image("Image 4 128", related="image_1920_4", max_width=128, max_height=128, store=True)


class MegaColor(models.Model):
    _name = 'product.megacolor'
    _description = 'Megacolor'
    
    name = fields.Char('Name',translate=True,required=True)
    
    
class Plating(models.Model):
    _name = 'product.plating'
    _description = 'Plating'
    
    name = fields.Char('Name',translate=True,required=True)
    
class Stone(models.Model):
    _name = 'product.stone'
    _description = 'Stone'
    
    name = fields.Char('Name',translate=True,required=True)
    stone_type_id =fields.Many2one('product.stone_type',string="Stone Name")
    megacolor_id =fields.Many2one('product.megacolor',string="Megacolor")

    
class Metal(models.Model):
    _name = 'product.metal'
    _description = 'Metal'
    
    name = fields.Char('Name',translate=True,required=True)

     
class MetalCodeTitle(models.Model):
    _name = 'product.metal.code.title'
    _description = 'Metal Code & Title'

    name = fields.Char('Code & Title', required=True)


class WatchStrapMaterial(models.Model):
    _name = 'product.watch_strap_material'
    _description = 'Watch Strap Material'
    
    name = fields.Char('Name',translate=True,required=True)

class Genre(models.Model):
    _name = 'product.genre'
    _description = 'Genre'
    
    name = fields.Char('Name',translate=True,required=True)

class Season(models.Model):
    _name = 'product.season'
    _description = 'Season'
    
    name = fields.Char('Name',translate=True,required=True)
    
    

class Collection(models.Model):
    _name = 'product.collection'
    _description = 'Collection'
    
    name = fields.Char('Name',required=True)


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    default_code = fields.Char('Internal Reference', compute="_compute_variant_default_code",store=True,index=True,readonly=True)
    milor_extension_code = fields.Char('Codice Estensione')
    qvc_extension_code = fields.Char('Codice Estensione QVC')
    qvc_complete_code = fields.Char('Codice Completo QVC', compute="_compute_variant_qvc_code",store=True,index=True,readonly=True)
    commercehub_code = fields.Char('Vendor SKU')

    client_article_code = fields.Char('Client Article', compute="_compute_variant_client_article_code",store=True,index=True,readonly=True,tracking=True)
    client_extension_code = fields.Char('Codice Estensione Client')
    
    milor_plateau = fields.Char("Plateau")
    
    weight_gr = fields.Float("Peso (gr)",digits='Stock Weight')
    weight_gr_min = fields.Float("Peso Min (gr)",digits='Stock Weight')
    weight_gr_max = fields.Float("Peso Max (gr)",digits='Stock Weight')
    dimension = fields.Char("Dimensione (cm)")
    length_cm = fields.Char("Lunghezza (cm)")
    extension_cm = fields.Char('Estensione (cm)')
    
    top = fields.Float('Top',digits='Milor Dimension')
    depth = fields.Float('Profondità',digits='Milor Dimension')
    width = fields.Float('Larghezza',digits='Milor Dimension')
    height = fields.Float('Altezza',digits='Milor Dimension')
    stem = fields.Float('Gambo',digits='Milor Dimension')
    
    length_inch = fields.Char("Lunghezza (inch)",store=True)
    extension_inch = fields.Char('Estensione (inch)',store=True)
    metal_weight_gr = fields.Float("Peso Materiale (gr)",digits='Stock Weight')
    metal_weight_gr_min = fields.Float("Peso Materiale Min (gr)",digits='Stock Weight')
    metal_weight_gr_max = fields.Float("Peso Materiale Max (gr)",digits='Stock Weight')
    weight_stone_gr = fields.Char("Pietre Peso (gr)")
    weight_stone_kt = fields.Char("Pietre Peso (kt)")
    
    stone_number = fields.Integer('Numero pietre')
    stone_ids = fields.Many2many("product.stone",string="Pietre")
    stone_dimension = fields.Char("Dimensioni Pietre (mm)")
    lucid_sphere = fields.Char("Sfere Lucide (mm)")
    satinate_sphere = fields.Char("Sfere Satinate (mm)")
    
    size = fields.Char('Taglia')
    other_info = fields.Text('Altro')
    
    currency_cost = fields.Monetary('Costo Valuta',currency_field='currency_for_cost_id')
    metal_cost = fields.Monetary('Costo Metallo Totale',compute="_costs",store=True,readonly=True)
    
    out_of_collection_variant = fields.Boolean('Fuori Collezione Estensione')
    out_of_catalog_variant = fields.Boolean('Fuori Catalogo Estensione')
    raw_lst_price = fields.Float('Fixed Public Price')
    lst_price = fields.Float(
        'Public Price', compute='_compute_product_lst_price',
        digits='Product Price', inverse='_set_product_lst_price',
        help="The sale price is managed from the product template. Click on the 'Configure Variants' button to set the extra attribute prices.")
    
    total_cost_imported = fields.Char('Costo Totale Metallo')
    pepperi_pricelist_imported = fields.Char('Pepperi Pricelist')
    currency_char_imported = fields.Char('Valuta')
    milor_upc_code = fields.Char("UPC Code")

    plating_id = fields.Many2one("product.plating",string="Colore Placcatura")
    plating_note = fields.Text("Note Placcatura")
    plating_depth = fields.Char("Profondità Placcatura")
    plating_title = fields.Char("Plating Title")
    
    specific = fields.Char("Specifica")

    
    hts_price = fields.Float('Hts Price')
    product_stone_ids = fields.Many2many('product.template','product_stone_rel','product_id','product_stone_id',string='Prodotti Pietra',domain="[('is_a_stone','=',True)]")
    product_of_this_package_ids = fields.One2many('product.template','packaging_code_id',string="Product of this package")

    general_description = fields.Text("Descrizione Generale",readonly=True)
    collection_description = fields.Text("Descrizione Collezione",readonly=True)
    stone_description = fields.Text("Descrizione Pietra",readonly=True)
    when_use = fields.Text("Quando Utilizzarlo",readonly=True)
    keywords = fields.Text("Keywords",readonly=True)
    alternative_text = fields.Text('Testo Alternativo',readonly=True)
    description_lang = fields.Text('Description Lang',readonly=True)
    import_description = fields.Text('Descrizione per Import')

    supplies_last = fields.Boolean('Ad Esaurimento')
    bat_descr = fields.Char(compute='_compute_bat_descr', store=True)

    @api.depends('name')
    def _compute_bat_descr(self):
        for product in self:
            if product.name:
                product.bat_descr = f"<![CDATA[{product.name or ''}]]>"

    def price_compute(self, price_type, uom=False, currency=False, company=False):
        products = self
        prices = dict.fromkeys(self.ids, 0.0)
        if price_type == 'list_price':
            for product in products:
                prices[product.id] = product.lst_price or 0.0
            
            return prices
        else:
            return super(ProductProduct,self).price_compute(price_type,uom,currency,company)
        
    # @api.model
    # def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
    #     if not args:
    #         args = []
    #     res = []
    #     if name:
    #         positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
    #         product_ids = []
    #         if operator in positive_operators:
    #             product_ids = self._search([('milor_code', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
    #         res = models.lazy_name_get(self.browse(product_ids).with_user(name_get_uid))
    #     res += super(ProductProduct,self)._name_search(name,args,operator,limit,name_get_uid)
    #     return res
    
    @api.constrains('weight_gr')
    def _compute_weight(self):
        for a in self:
            a.weight = a.weight_gr / 1000
            
    @api.depends('list_price', 'price_extra','raw_lst_price','price_type','metal_cost')
    @api.depends_context('uom')
    def _compute_product_lst_price(self):
        for a in self:
            if a.product_tmpl_id.price_type == 'calculated_metal':
                a.lst_price = a.metal_cost
            elif a.product_tmpl_id.price_type == 'on_variant':
                a.lst_price = a.raw_lst_price
            else:
                super(ProductProduct,a)._compute_product_lst_price()
    
    def _set_product_lst_price(self):
        for product in self:
            if product.product_tmpl_id.price_type == 'on_variant':
                product.write({'raw_lst_price': product.lst_price})
            else:
                super(ProductProduct,product)._set_product_lst_price()
    
    @api.depends('metal_weight_gr','metal_cost_gr')
    def _costs(self):
        for a in self:
            a.write({
                     'metal_cost':a.metal_weight_gr*a.metal_cost_gr,
                     })

    @api.depends('product_tmpl_id.qvc_code','qvc_extension_code')
    def _compute_variant_qvc_code(self):
        for rec in self:
            ext_code = rec.qvc_extension_code
            rec.qvc_complete_code = (rec.product_tmpl_id.qvc_code or '') + (ext_code and (' ' + ext_code) or '')

    # @api.depends('product_tmpl_id.default_code','milor_extension_code')
    # def _compute_commercehub_code(self):
    #     for rec in self:
    #         ext_code = rec.milor_extension_code
    #         rec.commercehub_code = (rec.product_tmpl_id.default_code or '') + (ext_code and ('.' + ext_code) or '')

    @api.depends('product_tmpl_id.default_code','milor_extension_code')
    def _compute_variant_default_code(self):
        for rec in self:
            ext_code = rec.milor_extension_code
            rec.default_code = (rec.product_tmpl_id.default_code or '') + (ext_code and ('.' + ext_code) or '')

    @api.depends('product_tmpl_id.client_article_code','client_extension_code')
    def _compute_variant_client_article_code(self):
        for rec in self:
            ext_code = rec.client_extension_code
            rec.client_article_code = (rec.product_tmpl_id.client_article_code or '') + (ext_code and ('.' + ext_code) or '')

class ProductCategory(models.Model):
    _inherit = 'product.category'
    
    megacategory = fields.Char('Megacategory',translate=True,help="for connectors")
    is_watch=fields.Boolean('Articoli orologi',default=True)
    is_packaging=fields.Boolean('Articoli packaging',dafault=True)
    is_accessory=fields.Boolean('Articoli accessori',dafault=True)
    is_a_stone=fields.Boolean('Articoli Pietre',default=True)
    with_stone=fields.Boolean('Articoli con Pietra',default=True)
    metal_and_plating=fields.Boolean('Articoli di metallo con placcatura',default=True)
    with_closure=fields.Boolean('Articoli con chiusura',default=True)
    with_rolo=fields.Boolean('Articoli con catena',default=True)
    
    
class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    customer_product_ids = fields.Many2many('product.template',relation='product_template_res_partner_rel',string="Customer product")
    customer_product_count = fields.Integer('Products',compute="_customer_product_count")
    web_customer = fields.Boolean('Web Customer')
    
    def _customer_product_count(self):
        for a in self:
            a.customer_product_count = len(a.customer_product_ids)


class ProductAccontCode(models.Model):
    _name = 'product.account.code'

    name = fields.Char(string="Code")
    description = fields.Char()

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Name field must be unique.'),
    ]


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    
    customer_ids = fields.Many2many('res.partner',string='Clienti per prodotto',tracking=True)
    is_a_stone=fields.Boolean('Articoli Pietre',related="categ_id.is_a_stone")
    is_packaging=fields.Boolean('Articoli packaging',related="categ_id.is_packaging", store=True)
    is_accessory=fields.Boolean('Articoli accessory',related="categ_id.is_accessory")
    is_watch=fields.Boolean('Articoli orologi',related="categ_id.is_watch")
    with_stone=fields.Boolean('Articoli con Pietra',related="categ_id.with_stone")
    metal_and_plating=fields.Boolean('Articoli di metallo con placcatura',related="categ_id.metal_and_plating")
    with_closure=fields.Boolean('Articoli con chiusura',related="categ_id.with_closure")
    with_rolo=fields.Boolean('Articoli con catena',related="categ_id.with_rolo")
    
    client_article_code = fields.Char('Client Article',tracking=True)
    milor_unit_id = fields.Many2one('product.milor_unit',string="Milor Unit",tracking=True)
    milor_code = fields.Char('Codice Milor',tracking=True)
    milor_complete_code = fields.Char('Codice Completo',tracking=True)

    milor_account_code = fields.Char('Codice Contabilità')
    milor_account_code_id = fields.Many2one('product.account.code', tracking=True)

    packaging_code_id = fields.Many2one('product.product',"Prodotto Packaging",domain="[('is_packaging','=',True)]")
    add_packaging_to_order = fields.Boolean('Aggiungi package su ordine',default=True)

    is_packaging_code = fields.Char(compute='_compute_is_packaging_code', store=True)
    bat_descr2 = fields.Char(compute='_compute_bat_descr2', store=True)

    @api.depends('packaging_code_id', 'categ_id', 'packaging_code_id.default_code', 'categ_id.name')
    def _compute_bat_descr2(self):
        for product in self:
            if product.packaging_code_id.default_code or product.categ_id.name:
                product.bat_descr2 = f"<![CDATA[{product.packaging_code_id.default_code or ''}!{product.categ_id.name or ''}]]>"

    @api.depends('is_packaging', 'categ_id.is_packaging')
    def _compute_is_packaging_code(self):
        for product in self:
            product.is_packaging_code = '02' if product.is_packaging else '01'

    milor_packaging_code = fields.Char('Codice Packaging',related="packaging_code_id.milor_code")
    collection_id = fields.Many2one('product.collection',string="Collezione",tracking=True)
    trend_id = fields.Many2one('product.trend',string="Trend")
    out_of_collection = fields.Boolean('Fuori Collezione')
    out_of_catalog = fields.Boolean('Fuori Catalogo')

    supplies_last = fields.Boolean('Ad Esaurimento')
    season_id = fields.Many2one('product.season',string="Stagione")
    genre_id = fields.Many2one('product.genre',string="Genere")
    show_id = fields.Many2one('product.milor_show',string="Show")
    
    
    # watch
    watch_case = fields.Char("Cassa Orologio")
    watch_case_mm = fields.Float("Cassa (mm)",digits='Milor Dimension')
    watch_strap = fields.Char("Cinturino Orologio")
    watch_strap_material_id = fields.Many2one("product.watch_strap_material",string="Cinturino Materiale")
    watch_strap_thickness = fields.Char("Cinturino Spessore")
    watch_type_id = fields.Many2one("product.watch_type",string="Tipo Orologio")
    
    metal_id = fields.Many2one("product.metal","Metallo")
    metal_title = fields.Char("Title Metallo")
    metal_code_title_id = fields.Many2one('product.metal.code.title', help="Metal Code and Title to be used in TXT file.")

    # Variant
    metal_weight_gr = fields.Float("Peso Materiale (gr)",digits='Stock Weight',related='product_variant_ids.metal_weight_gr',readonly=False)
    metal_weight_gr_min = fields.Float("Peso Materiale Min (gr)",digits='Stock Weight',related='product_variant_ids.metal_weight_gr_min',readonly=False)
    metal_weight_gr_max = fields.Float("Peso Materiale Max (gr)",digits='Stock Weight',related='product_variant_ids.metal_weight_gr_max',readonly=False)
    
    # Variant
    dimension = fields.Char("Dimensione (cm)",related='product_variant_ids.dimension',readonly=False)
    length_cm = fields.Char("Lunghezza (cm)",related='product_variant_ids.length_cm',readonly=False)
    extension_cm = fields.Char('Estensione (cm)',related='product_variant_ids.extension_cm',readonly=False)
    length_inch = fields.Char("Lunghezza (inch)",readonly=False,related='product_variant_ids.length_inch')
    extension_inch = fields.Char('Estensione (inch)',readonly=False,related='product_variant_ids.extension_inch')
    top = fields.Float('Top',digits='Milor Dimension',related='product_variant_ids.top',readonly=False)
    depth = fields.Float('Profondità',digits='Milor Dimension',related='product_variant_ids.depth',readonly=False)
    width = fields.Float('Larghezza',digits='Milor Dimension',related='product_variant_ids.width',readonly=False)
    height = fields.Float('Altezza',digits='Milor Dimension',related='product_variant_ids.height',readonly=False)
    stem = fields.Float('Gambo',digits='Milor Dimension',related='product_variant_ids.stem',readonly=False)
    
    
    #packaging
    package_logo = fields.Char('Package Logo')
    package_logo_image_1920 = fields.Image("Package Logo Image", max_width=1920, max_height=1920)

    # resized fields stored (as attachment) for performance
    package_logo_image_1024 = fields.Image("Image 2 1024", related="package_logo_image_1920", max_width=1024, max_height=1024, store=True)
    package_logo_image_512 = fields.Image("Image 2 512", related="package_logo_image_1920", max_width=512, max_height=512, store=True)
    package_logo_image_256 = fields.Image("Image 2 256", related="package_logo_image_1920", max_width=256, max_height=256, store=True)
    package_logo_image_128 = fields.Image("Image 2 128", related="package_logo_image_1920", max_width=128, max_height=128, store=True)
    package_color = fields.Char('Package Colore')
    package_logo_color = fields.Char('PacKage Logo Colore')
    
    # Variant
    weight_gr = fields.Float("Peso (gr)",digits='Stock Weight',related='product_variant_ids.weight_gr',readonly=False)
    weight_gr_min = fields.Float("Peso Min (gr)",digits='Stock Weight',related='product_variant_ids.weight_gr_min',readonly=False)
    weight_gr_max = fields.Float("Peso Max (gr)",digits='Stock Weight',related='product_variant_ids.weight_gr_max',readonly=False)
    
    # Variant
    weight_stone_gr = fields.Char("Pietre Peso (gr)",related='product_variant_ids.weight_stone_gr',readonly=False)
    weight_stone_kt = fields.Char("Pietre Peso (kt)",related='product_variant_ids.weight_stone_kt',readonly=False)
    
    # Variant
    plating_id = fields.Many2one("product.plating",string="Colore Placcatura",related='product_variant_ids.plating_id')
    plating_note = fields.Text("Note Placcatura",related='product_variant_ids.plating_note')
    plating_depth = fields.Char("Profondità Placcatura",related='product_variant_ids.plating_depth')
    plating_title = fields.Char("Plating Title",related='product_variant_ids.plating_title')
    
    specific = fields.Char("Specifica",related='product_variant_ids.specific')
    
    
    stone_number = fields.Integer('Numero pietre',related='product_variant_ids.stone_number')
    stone_ids = fields.Many2many("product.stone",string="Pietre",related='product_variant_ids.stone_ids',readonly=False)
    stone_dimension = fields.Char("Dimensioni Pietre (mm)",related='product_variant_ids.stone_dimension',readonly=False)
    lucid_sphere = fields.Char("Sfere Lucide (mm)",related='product_variant_ids.lucid_sphere',readonly=False)
    satinate_sphere = fields.Char("Sfere Satinate (mm)",related='product_variant_ids.satinate_sphere',readonly=False)
    
    size = fields.Char('Taglia',related='product_variant_ids.size',readonly=False)
    
    rolo_id = fields.Many2one("product.rolo","Catena")
    rolo_thickness = fields.Char("Spessore (mm)")
    
    closure_type_id = fields.Many2one("product.closure_type","Chiusura Tipo")
    closure_dimension = fields.Float("Chiusura Dimensione (mm)",digits='Milor Dimension')
    closure_thickness = fields.Float("Chiusura Spessore (mm)",digits='Milor Dimension')
    
    chp = fields.Char("CHP (mm)",digits='Milor Dimension')
    
    stamp_id = fields.Many2one("product.stamp","Bollo",domain="['|',('milor_unit_id','=',False),('milor_unit_id','=',milor_unit_id)]")
    stamp_image_256 = fields.Image("Immagine Bollo", related="stamp_id.image_256", max_width=256, max_height=256)
    stamp_image_256_2 = fields.Image("Immagine Bollo 2", related="stamp_id.image_256_2", max_width=256, max_height=256)
    stamp_image_256_3 = fields.Image("Immagine Bollo 3", related="stamp_id.image_256_3", max_width=256, max_height=256)
    stamp_image_256_4 = fields.Image("Immagine Bollo 4", related="stamp_id.image_256_4", max_width=256, max_height=256)
    stamp_note = fields.Char('Note Bollo')
    
    hts_id = fields.Many2one("product.hts",string="HTS",domain="[('metal_id','=',metal_id)]")
    hts_duty = fields.Float("Dazio",related="hts_id.duty")
    hts_code = fields.Char("HTS Code",related="hts_id.code")
    hts_duty_extra = fields.Float("Dazio Extra",related="hts_id.duty_extra")
    hts_spedition_cost = fields.Float('Spese Spedizione',related="hts_id.spedition_cost")
    
    
    
    packing_master_carton = fields.Char("Imballaggio Master Carton")
    packing_inner_carton = fields.Char("Imballaggio Inner Carton")
    
    plastic_size = fields.Char("Plastic Size")
    
    bullet_points = fields.Text("Bullet Points",readonly=True)
    
    name_lang = fields.Text('Name Lang',readonly=True)
    general_description = fields.Text("Descrizione Generale",related='product_variant_ids.general_description',readonly=True)
    collection_description = fields.Text("Descrizione Collezione",related='product_variant_ids.general_description',readonly=True)
    technical_description = fields.Text("Descrizione Tecnica",readonly=True)
    plating_description = fields.Text("Descrizione Placcatura",readonly=True)
    stone_description = fields.Text("Descrizione Pietra",related='product_variant_ids.stone_description',readonly=True)
    when_use = fields.Text("Quando Utilizzarlo",related='product_variant_ids.when_use',readonly=True)
    keywords = fields.Text("Keywords",related='product_variant_ids.keywords',readonly=True)
    title = fields.Text("Title",readonly=True)
    meta_description = fields.Text("Meta Description",readonly=True)
    alternative_text = fields.Text('Testo Alternativo',related='product_variant_ids.alternative_text',readonly=True)
    
    description_lang = fields.Text('Description Lang',related='product_variant_ids.general_description',readonly=True)

    stone_sample = fields.Boolean('Campione')
    stone_type = fields.Many2one('product.stone_type','Stone name')
    stone_shape = fields.Many2one('product.stone_shape','Forma')
    stone_cut = fields.Many2one('product.stone_cut','Taglio')
    stone_color = fields.Char('Color')
    stone_quality = fields.Char('Quality')
    only_stone_weight = fields.Float('Peso Pietra (gr)',digits='Stock Weight')
    stone_ct = fields.Float('Peso in carati',digits='Milor Dimension',compute="_stone_ct")
    stone_measure = fields.Char('Misura')
    stone_thickness = fields.Char('Spessore')
    
    filo_id = fields.Many2one('uom.uom','Filo')
    
    feature_ids = fields.Many2many('product.feature',string="Features")
    
    milor_type = fields.Selection([('mto','Make to Order'),('mts','Make to Stock')],default="mts",string="Milor type")
    
    default_code = fields.Char(
        'Internal Reference', store=True)
    
    qvc_code = fields.Char('Codice QVC')
    qvc_code_url = fields.Char('QVC Linked Search', compute="_compute_qvc_code_url", store=False)
    group_code = fields.Char('CH Code')
    keyword = fields.Char('Parola Chiave')
    
    currency_for_cost_id = fields.Many2one('res.currency','Valuta per Costo Valuta',default=lambda self: self.env.company.currency_id.id,)
    #currency_cost = fields.Monetary('Costo Valuta',currency_field='currency_for_cost_id',related='product_variant_ids.currency_cost',readonly=False)
    
    gold_base_cost = fields.Monetary('Costo base quotazione oro',currency_field='currency_for_cost_id')
    cost_coefficient = fields.Float('Coefficiente Incremento / Decremento')
    metal_cost_gr = fields.Monetary('Costo Metallo al gr.')
    
    # variant
    metal_cost = fields.Monetary('Costo Metallo Totale',related='product_variant_ids.metal_cost',readonly=True)
    
    price_type=fields.Selection([('on_attribute','Su Attributo'),('on_variant','Sulla Variante'),('calculated_metal','Calcolato dal Peso')],string="Price Type",default="on_variant")
    
    product_with_stone_ids = fields.Many2many('product.product','product_stone_rel','product_stone_id','product_id',string='Prodotti con questa Pietra')

    finish_id = fields.Many2one('product.finish','Finitura')
    hole = fields.Char('Foro')

    free_qty = fields.Float(
        'Free To Use Quantity ', compute='_compute_template_quantities',
        digits='Product Unit of Measure', compute_sudo=False)

    @api.model
    def _cron_update_new_account_code(self, automatic):
        if automatic:
            cr = registry(self._cr.dbname).cursor()
            self = self.with_env(self.env(cr=cr))

        try:
            product_account_code = self.env['product.account.code'].sudo()
            for rec in self.sudo().search([('milor_account_code', 'not in', [False, ''])]):
                _id = product_account_code.search([('name', '=', rec.milor_account_code)])
                rec.milor_account_code_id = _id and _id.id or False
                if automatic:
                    self.env.cr.commit()
        except Exception as e:
            if automatic:
                self.env.cr.rollback()
            _logger.info(str(e))
            self.env.cr.commit()
        finally:
            if automatic:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return True

    def _compute_template_quantities(self):
        for a in self:
            if a.product_variant_ids and a.type=='product':
                a.free_qty = sum([v.free_qty for v in a.product_variant_ids])
            else:
                a.free_qty = 0
                
    def _get_meta_field(self,name,lang):
        self.ensure_one()
        json_field = getattr(self,name)
        if json_field:
            f = json.loads(json_field)
            return f.get(lang,'')
        return False
    
    @api.constrains('out_of_collection')
    def _out_of_collection(self):
        for a in self:
            for p in a.product_variant_ids:
                p.out_of_collection_variant = a.out_of_collection
                
    
    @api.constrains('out_of_catalog')
    def _out_of_catalog(self):
        for a in self:
            for p in a.product_variant_ids:
                p.out_of_catalog_variant = a.out_of_catalog
        
    @api.constrains('milor_type')
    def _milor_type(self):
        for a in self:
            buy = self.sudo().env.ref('purchase_stock.route_warehouse0_buy').id
            mto = self.sudo().env.ref('stock.route_warehouse0_mto').id
            for a in self:
                if a.milor_type == 'mts':
                    a.route_ids = [(4,buy)]
                    if (mto in a.route_ids.ids):
                        a.route_ids = [(3,mto)]
                else:
                    a.route_ids = [(4,buy),(4,mto)]
        
    def _compute_default_code(self):
        for a in self:
            default_code = a.default_code
            a.default_code = default_code
    
    def _compute_qvc_code_url(self):
        for rec in self:
            rec.qvc_code_url = (rec.qvc_code and "https://www.qvc.com/catalog/search.html?keyword=" + (rec.qvc_code or '')) or ''

    @api.constrains('only_stone_weight')
    def _weight_only_stone(self):
        weight_gr = self.only_stone_weight
        stone_weight  = self.only_stone_weight
        self.write({
                    'weight_gr':weight_gr,
                    'weight_stone_gr':stone_weight
                    })
        
    @api.depends('length_cm','extension_cm')
    def _conversion_from_cm(self):
        for a in self:
            length_inch = self.env.company.uom_cm_id._compute_quantity(a.length_cm,self.env.company.uom_inch_id)
            extension_inch = self.env.company.uom_cm_id._compute_quantity(a.extension_cm,self.env.company.uom_inch_id)
            a.write({
                     'length_inch':length_inch,
                     'extension_inch':extension_inch
                     })
            
    @api.depends('only_stone_weight')
    def _stone_ct(self):
        for a in self:
            stone_ct = self.env.company.uom_gr_id._compute_quantity(a.only_stone_weight,self.env.company.uom_ct_id)
            a.write({
                'stone_ct':stone_ct
            })


class Order(models.Model):
    _inherit = "sale.order"
    
    custom_type = fields.Selection([('vision_account', 'Conto Visione'),
                                    ('standard', 'Ordine standard')], string='Custom Type', default='standard')
    
    add_packaging_to_order = fields.Boolean('Aggiungi package su ordine',default=True)
    
    website_order_line = fields.One2many(
        'sale.order.line',
        compute='_compute_website_order_line',
        string='Order Lines displayed on Website',
        help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
    )
    web_customer = fields.Boolean('Web Order',related="partner_id.web_customer",store=True)
    
    

    @api.depends('order_line')
    def _compute_website_order_line(self):
        for order in self:
            order.website_order_line = order.order_line.filtered(lambda self: not bool(self.product_of_package_ids))
    
    def remove_packages(self):
        for a in self:
            if a.add_packaging_to_order:
                for l in a.order_line.filtered(lambda self: bool(self.packaging_line_id)):
                    l.packaging_line_id.unlink()
                a.add_packaging_to_order = False
            
    def add_packages(self):
        for a in self:
            if not a.add_packaging_to_order:
                a.add_packaging_to_order = True
                for l in a.order_line:
                    l.update_packaging()
                
    
class OrderLine(models.Model):
    _inherit = "sale.order.line"
    
    free_product = fields.Boolean('Omaggio')
    packaging_line_id = fields.Many2one('sale.order.line',string="Packaging Line",copy=False)
    add_packaging_to_order = fields.Boolean('Aggiungi package su ordine',store=True,related='order_id.add_packaging_to_order')
    product_of_package_ids = fields.One2many('sale.order.line','packaging_line_id',string="Product of this Package")
    #### if a product with packaging is inserted in an order, the packaging product with the same quantity is inserted too
    
    #saving packaging (if it is not saved by form)
    @api.constrains('product_id')
    def packaging_costrains_product(self):
        self.update_packaging()
    
    def update_packaging(self):
        for a in self:
            if a.add_packaging_to_order:
                if a.packaging_line_id and a.packaging_line_id.product_id.id != a.product_id.packaging_code_id.id :
                    a.packaging_line_id.unlink()
                if a.product_id.packaging_code_id and not a.packaging_line_id and a.product_id.add_packaging_to_order:
                    a.create_packaging_line()
            
    
    @api.constrains('product_uom_qty')
    def packaging_constrains_quantity(self):
        for a in self:
            if a.packaging_line_id:
                a.packaging_line_id.product_uom_qty = a.product_uom_qty
            
            
    def create_packaging_line(self):
        for a in self:
            a.packaging_line_id = self.create({
                         'order_id':a.order_id.id,
                         'product_id':a.product_id.packaging_code_id.id,
                         'product_uom_qty':a.product_uom_qty
                         }).id
    @api.model
    def create(self,values):
        res = super(OrderLine,self).create(values)
        if res.product_id.packaging_code_id and not res.packaging_line_id and res.product_id.add_packaging_to_order:
            res.create_packaging_line()
        return res

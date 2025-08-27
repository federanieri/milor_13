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
import logging
import psycopg2
_logger = logging.getLogger(__name__)

class PartnerImport(models.Model):
    _name="partner.import"
    _description = 'Model to help the migration of partner'
    
    
    name=fields.Char('OS1 Code')
    filemaker_code = fields.Char('Fm Code')
    l10n_it_pec_email = fields.Char('Pec Mail')
    l10n_it_codice_fiscale = fields.Char('Fiscal Code')
    l10n_it_pa_index = fields.Char(string="PA index")

    id_agente_c= fields.Char('Id Agente C')
    
    @api.model        
    def import_partners(self):
       products = self.search([(1,'=',1)]) 
       products.import_partner()
    
    def import_partner(self):
        ResPartner = self.env['res.partner']
        for p in self:
            try:
                partner = ResPartner.search([('fm_code','=',p.name)],limit=1)
                if partner:
                    if p.filemaker_code:
                        partner.write({'filemaker_code':p.filemaker_code})
                    if p.l10n_it_pec_email:
                        partner.write({'l10n_it_pec_email':p.l10n_it_pec_email})
                    if p.l10n_it_codice_fiscale:
                        partner.write({'l10n_it_codice_fiscale':p.l10n_it_codice_fiscale})
                    if p.l10n_it_pa_index:
                        partner.write({'l10n_it_pa_index':p.l10n_it_pa_index})
                    if p.id_agente_c:
                        id_agente_c = ResPartner.search([('fm_code','=',p.id_agente_c)],limit=1)
                        if id_agente_c:
                            partner.write({'salesman_parent_partner_id':id_agente_c.id})
            except Exception as e:
                _logger.error("%s %s"%(p.name,str(e)),exc_info=True)
                p.log = str(e)

class ProductImport(models.Model):
    _name = "product.import"
    _description = 'Model to help the migration of the product'
    
    
    name = fields.Char('nome articolo')
    barcode = fields.Char('Eancode')
    default_code = fields.Char('Codice prodotto')
    attributes = fields.Char('Attributo')
    
    ################################ TEMPLATE
    category_id = fields.Char('Categoria')#'product.category'
    product_brand_id = fields.Char( string="Brand") #'common.product.brand.ept',
    milor_unit_id = fields.Char(string="Base") #'product.milor_unit'
    milor_code = fields.Char('Codice Milor')
    milor_account_code = fields.Char('Codice Prodotto Contabilità')
    packaging_code_id = fields.Char("Codice Prodotto Packaging") #'product.product'
    collection_id = fields.Char(string="Collezione") #'product.collection'
    trend_id = fields.Char(string="Trend")#'product.trend',
    out_of_collection = fields.Boolean('Fuori Collezione Articolo')
    out_of_collection_variant = fields.Boolean('Fuori Collezione Estensione')
    supplies_last = fields.Boolean('Ad Esaurimento')
    season_id = fields.Char(string="Stagione") #'product.season',
    genre_id = fields.Char(string="Tipo_Genere") #'product.genre',
    show_id = fields.Char(string="Show")#'product.milor_show'
    watch_case = fields.Char("Cassa Orologio")
    watch_case_mm = fields.Float("Cassa (mm)")
    watch_strap = fields.Char("Cinturino Orologio")
    watch_strap_material_id = fields.Char(string="Orologio Cinturino Materiale")#"product.watch_strap_material",
    watch_strap_thickness = fields.Char("Cinturino Spessore")
    metal_id = fields.Char("Metallo") #"product.metal",
    metal_title = fields.Char("Title Metallo")
    rolo_id = fields.Char("Catena")#"product.rolo"
    rolo_thickness = fields.Char("Spessore (mm)")
    closure_type_id = fields.Char("Chiusura Tipo")#"product.closure_type",
    closure_dimension = fields.Float("Chiusura Dimensione (mm)")
    closure_thickness = fields.Float("Chiusura Spessore (mm)")
    chp = fields.Char("CHP (mm)",digits='Milor Dimension')
    stamp_id = fields.Char("Bollo") #"product.stamp",
    milor_upc_code = fields.Char("UPC Code")
    hts_id = fields.Char(string="Selezione per HTS")#"product.hts"  
    packing_master_carton = fields.Char("Imballaggio Master Carton")
    packing_inner_carton = fields.Char("Imballaggio Inner Carton") 
    plastic_size = fields.Char("Plastic Size")
    milor_type = fields.Selection([('mto','Make to Order'),('mts','Make to Stock')],default="mts",string="Milor type")
    commercehub_code = fields.Char('Vendor SKU')
    group_code = fields.Char('CH Code')
    keyword = fields.Char('Parola Chiave')
    gold_base_cost = fields.Float("Costo Base Quotazione Oro giorno all'oncia")
    cost_coefficient = fields.Float('Coefficiente di Incremento')
    metal_cost_gr = fields.Float('Prezzo Metallo al Gr.')
    #################################### VARIANT
       
    milor_extension_code = fields.Char('Codice Estensione')
    milor_plateau = fields.Char("Plateau")
    weight_gr = fields.Float("Peso Prodotto Gr.")
    weight_gr_min = fields.Float("Peso Prodotto Min Gr.")
    weight_gr_max = fields.Float("Peso Max (gr)")
    dimension = fields.Char("Dimensione (cm)")
    length_cm = fields.Char("Lunghezza")
    extension_cm = fields.Char('Lunghezza cm estensione')
    length_inch = fields.Char("Lunghezza (inch)")
    extension_inch = fields.Char('Lunghezza cm estensione (inch)')
    metal_weight_gr = fields.Float("Peso Materiale Gr.")
    metal_weight_gr_min = fields.Float("Peso Materiale Min Gr.")
    metal_weight_gr_max = fields.Float("Peso Materiale Max (gr)")
    weight_stone_gr = fields.Char("Pietra Peso gr.")
    weight_stone_kt = fields.Char("Pietra KT")
    stone_ids = fields.Char(string="Pietre")#"product.stone", Many2many
    stone_dimension = fields.Char("Dimensioni Pietre (mm)")
    lucid_sphere = fields.Char("Sfere Lucide (mm)")
    satinate_sphere = fields.Char("Sfere Satinate (mm)")
    plating_id = fields.Char(string="Placcatura")#"product.plating",
    size = fields.Char('Taglia')
    other_info = fields.Text('Altro')
    type=fields.Char('Type')
    description = fields.Text('Note')
    
    code = fields.Char('Codice HTS')
    duty = fields.Float('Dazio %')
    
    total_cost_imported = fields.Char('Costo Totale Metallo')
    pepperi_pricelist_imported = fields.Char('Pepperi Pricelist')
    currency_char_imported = fields.Char('Valuta')
    
    
    raw_lst_price = fields.Float('Raw List Price')
    imported = fields.Boolean('Imported',default=False,copy=False)
    log = fields.Text('Log',copy=False)
    
    top = fields.Float('Top',digits='Milor Dimension')
    depth = fields.Float('Profondità',digits='Milor Dimension')
    width = fields.Float('Larghezza',digits='Milor Dimension')
    height = fields.Float('Altezza',digits='Milor Dimension')
    stem = fields.Float('Gambo',digits='Milor Dimension')
    
    package_logo = fields.Char('Package Logo')
    package_color = fields.Char('Package Colore')
    package_logo_color = fields.Char('PacKage Logo Colore')
    
    finish_id = fields.Char('Finitura')
    hole = fields.Char('Foro')
    customer_id = fields.Char('Customer')
    unit_of_measure = fields.Char('Unità di misura')
    
    qvc_code = fields.Char('Codice QVC')
    qvc_extension_code = fields.Char('Codice Estensione QVC')

    def _prepare_template_value(self):
        return {
                'name':self.name,
                'default_code':self.default_code
                }

    def _get_attributes(self):
        res = []
        Attribute = self.env['product.attribute']
        Value = self.env['product.attribute.value']
        if self.attributes:
            avalues = self.attributes.split(';')
            for a in avalues:
                if len(a)>0:
                    b = a.split(':')
                    if len(b)==2:
                        attribute = Attribute.search([('name','=',b[0])],limit=1)
                        if not attribute :
                            attribute = Attribute.create({'name':b[0]})
                        value = Value.search([('name','=',b[1]),('attribute_id','=',attribute.id)],limit=1)
                        if not value:
                            value = Value.create({'name':b[1],'attribute_id':attribute.id})
                        res += [(attribute,value)]
        return res
    
    @api.model
    def _create_template_attribute(self,template_id,attribute_id,value_id):
        AttributeLines = self.env['product.template.attribute.line']
        template_attribute = AttributeLines.search([('product_tmpl_id','=',template_id.id),('attribute_id','=',attribute_id.id)],limit=1)
        if not template_attribute:
            template_attribute = AttributeLines.create({
                                       'product_tmpl_id':template_id.id,
                                       'attribute_id':attribute_id.id,
                                       'value_ids':[(6,0,[value_id.id])]
                                       })
        else:
            if not value_id.id in template_attribute.value_ids.ids:
               template_attribute.value_ids = [(4,value_id.id)]
        return template_attribute
    
    
    
    @api.model
    def _get_variant(self,template_id,attributes):
        AttributeLineValues = self.env['product.template.attribute.value']
        avalues = self.env['product.template.attribute.value']
        for t,v in attributes:
                avalues |= AttributeLineValues.search([('product_tmpl_id','=',template_id.id),('attribute_id','=',t.id),('product_attribute_value_id','=',v.id)])
        return template_id._get_variant_for_combination(avalues)
    
    
    
     
    def import_product(self,update=True):
        Template = self.env['product.template']
        Product = self.env['product.product']
        AttributeLines = self.env['product.template.attribute.line']
        for p in self:
            try:
                if update or not Product.search([('default_code','=',p.get_variant_default_code())],limit=1):
                    template = Template.search([('default_code','=',p.default_code)],limit=1)
                    if not template:
                       template = Template.create(p._prepare_template_value())
                    
                    # Read attributes
                    attributes = p._get_attributes()
                    template_attribute_ids = self.env['product.template.attribute.line']
                    for attribute,value in attributes:
                            template_attribute_ids |= self._create_template_attribute(template,attribute,value)
                    # set import field  on template
                    self._set_template_field(p,template)
                    template._create_variant_ids()    
                    # obtain variant from attributes
                    variant_id = self._get_variant(template,attributes)
                    # set import field on variant
                    res = self._set_variant_field(p,variant_id)
                    p.write({'imported':True,'log':res})
                    _logger.info("Product imported %s"%(p.name))
                    self.env.cr.commit()
                else:
                    p.write({'log':'Product %s already present'%p.get_variant_default_code()})
            except (BaseException,psycopg2.IntegrityError,psycopg2.InternalError) as e:
                _logger.error("%s %s"%(p.name,str(e)),exc_info=True)
                p.log = str(e)
    
    def _get_or_create(self,model_name,name,field_name=False,create=True):
        if name:
            if field_name:
                res_id = self.env[model_name].search([(field_name,'=',name)],limit=1)
            else:
                res_id = self.env[model_name].search([('name','=',name)],limit=1)
            if not res_id :
                if create:
                    res_id = self.env[model_name].create({
                                            'name':name 
                                             })
                else:
                    raise UserError('I cannot create %s %s'%(model_name,name))
            return res_id
        else:
            return False
    
    @api.model        
    def import_products(self):
       products = self.search([('imported','=',False)]) 
       
       products.import_product()
       
    
    #################################  Depends on Customer #######################
    
    
    
    def get_variant_default_code(self):
        self.ensure_one()
        if self.milor_extension_code:
            return self.default_code + "." + self.milor_extension_code
        else:
            return self.default_code   
        
             
    def _set_template_field(self,pimport,template):
                template.write({
                        'categ_id' :self._get_or_create_category(pimport.category_id),
                        'product_brand_id' :self._get_or_create('common.product.brand.ept',pimport.product_brand_id),
                        'milor_unit_id':self._get_or_create('product.milor_unit',pimport.milor_unit_id),
                        'milor_code' : pimport.milor_code,
                        'milor_account_code' : pimport.milor_account_code,
                        'packaging_code_id' :self._get_or_create('product.product',pimport.packaging_code_id,'default_code',False),
                        'collection_id' :self._get_or_create('product.collection',pimport.collection_id),
                        'trend_id':self._get_or_create('product.trend',pimport.trend_id),
                        'out_of_collection' :pimport.out_of_collection,
                        'supplies_last':pimport.supplies_last,
                        'season_id': self._get_or_create('product.season',pimport.season_id),
                        'genre_id' :self._get_or_create('product.genre',pimport.genre_id),
                        'show_id':self._get_or_create('product.milor_show',pimport.show_id),
                        'watch_case' : pimport.watch_case,
                        'watch_case_mm':pimport.watch_case_mm,
                        'watch_strap' :pimport.watch_strap,
                        'watch_strap_material_id': self._get_or_create("product.watch_strap_material",pimport.watch_strap_material_id),
                        'watch_strap_thickness' :pimport.watch_strap_thickness,
                        'metal_id' :self._get_or_create("product.metal",pimport.metal_id),
                        'metal_title' : pimport.metal_title,
                        'rolo_id' : self._get_or_create("product.rolo",pimport.rolo_id),
                        'rolo_thickness' : pimport.rolo_thickness,
                        'closure_type_id' : self._get_or_create("product.closure_type",pimport.closure_type_id),
                        'closure_dimension' : pimport.closure_dimension,
                        'closure_thickness' :pimport.closure_thickness,
                        'chp' : pimport.chp,
                        'stamp_id' :self._get_or_create("product.stamp",pimport.stamp_id),
                        'hts_id':self._get_or_create_hts(pimport),
                        'packing_master_carton' :pimport.packing_master_carton,
                        'packing_inner_carton' :pimport.packing_inner_carton,
                        'plastic_size' :pimport.plastic_size,
                        'group_code' : pimport.group_code,
                        'keyword' :pimport.keyword,
                        'gold_base_cost' :pimport.gold_base_cost,
                        'cost_coefficient' :pimport.cost_coefficient,
                        'metal_cost_gr' : pimport.metal_cost_gr,
                        'type'  :pimport.type,
                        'package_logo'  :pimport.package_logo,
                        'package_color' : pimport.package_color,
                        'package_logo_color'  :pimport.package_logo_color,
                        'list_price':pimport.raw_lst_price,
                        'finish_id' :self._get_or_create("product.finish",pimport.finish_id),
                        'hole' : pimport.hole,
                        'customer_ids':[(4,self.env['res.partner'].search([('fm_id','=',pimport.customer_id),('fm_type','=','CL')],limit=1).id)] if self.env['res.partner'].search([('fm_id','=',pimport.customer_id),('fm_type','=','CL')],limit=1) else False,
                        'milor_type': pimport.milor_type,
                        'qvc_code':pimport.qvc_code
                         })

                if pimport.unit_of_measure:
                    template.write({               
                        'uom_id':self._get_or_create_uom(pimport.unit_of_measure)
                })
                if not self.env['res.partner'].search([('fm_id','=',pimport.customer_id),('fm_type','=','CL')],limit=1):
                    template.write({               
                        'description_sale':pimport.customer_id
                        })
    def _set_variant_field(self,pimport,variant):
                res = False
                barcode = pimport.barcode
                if barcode:
                    if self.env['product.product'].search([('barcode','=',barcode),('id','!=',variant.id)]):
                        barcode = False
                        res = 'Barcode Already Present' 
                variant.write({
                               'milor_extension_code' :pimport.milor_extension_code,
                                'milor_plateau' : pimport.milor_plateau,
                                'weight_gr' : pimport.weight_gr,
                                'weight_gr_min' :pimport.weight_gr_min,
                                'weight_gr_max': pimport.weight_gr_max,
                                'dimension' :pimport.dimension,
                                'length_cm' :pimport.length_cm,
                                'extension_cm' :pimport.extension_cm,
                                'length_inch' :pimport.length_inch,
                                'extension_inch' :pimport.extension_inch,
                                'metal_weight_gr' :pimport.metal_weight_gr,
                                'metal_weight_gr_min':pimport.metal_weight_gr_min,
                                'metal_weight_gr_max' :pimport.metal_weight_gr_max,
                                'weight_stone_gr' :pimport.weight_stone_gr,
                                'weight_stone_kt' :pimport.weight_stone_kt,
                                'stone_ids':self._get_or_create_stone_ids(pimport.stone_ids),#"product.stone", Many2many
                                'stone_dimension' :pimport.stone_dimension,
                                'lucid_sphere' :pimport.lucid_sphere,
                                'satinate_sphere' :pimport.satinate_sphere,
                                'commercehub_code' :pimport.commercehub_code,
                                'plating_id' : self._get_or_create("product.plating",pimport.plating_id),#"",
                                'size': pimport.size,
                                'other_info': pimport.other_info,
                                'out_of_collection_variant':pimport.out_of_collection_variant,
                                'description':pimport.description,
                                'currency_char_imported':pimport.currency_char_imported,
                                'pepperi_pricelist_imported':pimport.pepperi_pricelist_imported,
                                'total_cost_imported':pimport.total_cost_imported,
                                'barcode':barcode,
                                 'top'  :pimport.top,
                                 'depth' : pimport.depth,
                                 'width'  :pimport.width,
                                 'height' : pimport.height,
                                 'stem' : pimport.stem,
                                 'raw_lst_price':pimport.raw_lst_price,
                                 'milor_upc_code' :pimport.milor_upc_code,
                                 'qvc_extension_code':pimport.qvc_extension_code
                                })
                return res
    
    def _get_or_create_hts(self,pimport):
        if pimport and pimport.hts_id:
            res_id = self.env['product.hts'].search([('name','=',pimport.hts_id)],limit=1)
            if not res_id:
                res_id = self.env['product.hts'].create({
                                            'name':pimport.hts_id,
                                            'duty':pimport.duty if pimport.duty< 1 else pimport.duty / 100,
                                            'code':pimport.code
                                             })
            return res_id
        else:
            return False
        
    def _get_or_create_uom(self,pimport):
        if pimport:
            res_id = self.env['uom.uom'].search([('name','=',pimport)],limit=1)
            if not res_id:
                res_id = self.env['uom.uom'].create({
                                            'name':pimport,
                                            'category_id':self.env['uom.category'].search([('name','=','Unit')],limit=1).id,
                                            'uom_type':'smaller'
                                             })
            return res_id.id
        else:
            return False
    
    def _get_or_create_category(self,name):
        if name:
            res_id = self.env['product.category'].search([('name','=',name),('parent_id','=',False)],limit=1)
            if not res_id :
                res_id = self.env['product.category'].create({
                                            'name':name 
                                             })
                if not res_id:
                    raise UserError('I cannot create Category %s'%(name))
            return res_id
        else:
            res_id = self.env['product.category'].search([('name','=','NOCATEGORY')],limit=1)
            return res_id
                
    
    
    def _get_or_create_stone_ids(self,stone_ids):
        stone_ids_list = []
        if stone_ids:
            stone_s = stone_ids.split('+')
            for s in stone_s:
                stone_id = self.env['product.stone'].search([('name','=',s)],limit=1)
                if not stone_id:
                    stone_id= self.env['product.stone'].create({'name':s})
                stone_ids_list.append((4,stone_id.id))
        return stone_ids_list
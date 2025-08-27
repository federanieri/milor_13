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
    
class PutawayRule(models.Model):
    _inherit = "stock.putaway.rule"

    putaway_cat_id= fields.Many2one('stock.putaway.filter_rule',string="Category",ondelete="cascade")
    
class PutawayFilter(models.Model):
    """ Defines Putaway category rules. """
    _name = "stock.putaway.filter_rule"
    _description = "Category Minimum Inventory Rule"
    
    
    def _default_category_id(self):
        if self.env.context.get('active_model') == 'product.category':
            return self.env.context.get('active_id')

    def _default_location_id(self):
        if self.env.context.get('active_model') == 'stock.location':
            return self.env.context.get('active_id')
    
    name = fields.Char(
        'Name', copy=False, required=True, 
        )
    putaway_ids = fields.One2many('stock.putaway.rule','putaway_cat_id',string="Putaway Rules")
    putaway_count = fields.Integer('Count',compute="_count")
    model_name = fields.Char('Model name',default='product.product')
    location_in_id = fields.Many2one(
        'stock.location', 'When product arrives in', check_company=True,
        domain="[('child_ids', '!=', False), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        default=_default_location_id, required=True, ondelete='cascade')
    location_out_id = fields.Many2one(
        'stock.location', 'Store to', check_company=True,
        domain="[('id', 'child_of', location_in_id), ('id', '!=', location_in_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        required=True, ondelete='cascade')
    sequence = fields.Integer('Priority', help="Give to the more specialized category, a higher priority to have them in top of the list.")
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, index=True)
    filter_domain = fields.Char('Filter On', help=" Filter on the object")

    
    def _count(self):
        self.putaway_count=len(self.putaway_ids)
        
        
    def generate(self):
        domain = [] + (safe_eval(self.filter_domain,  {}) if self.filter_domain else [])
        product_ids = self.env['product.product'].search(domain)
        for p in product_ids:
            rr = self.env['stock.putaway.rule'].search([
                                                            ('product_id','=',p.id),
                                                            ('location_out_id','=',self.location_out_id.id),
                                                            ('location_in_id','=',self.location_in_id.id),
                                                            ('putaway_cat_id','=',self.id)
                                                         ])
            if not rr:
                self.env['stock.putaway.rule'].create(
                                                              {
                                                               'putaway_cat_id':self.id,
                                                               'product_id':p.id,
                                                               'location_out_id':self.location_out_id.id,
                                                               'location_in_id':self.location_in_id.id,
                                                               'company_id':self.company_id.id,
                                                               }
                                                              )

    
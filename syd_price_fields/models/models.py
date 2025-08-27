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


class Product(models.Model):
    _inherit = 'product.product'
    
    
    price1 = fields.Monetary('Price 1',currency_field="currency1_id",compute="_compute_prices")
    currency1_id = fields.Many2one('res.currency',string="Currency",compute="_compute_currencies")
    
    price2 = fields.Monetary('Price 2',currency_field="currency2_id",compute="_compute_prices")
    currency2_id = fields.Many2one('res.currency',string="Currency",compute="_compute_currencies")
    
    price3 = fields.Monetary('Price 3',currency_field="currency3_id",compute="_compute_prices")
    currency3_id = fields.Many2one('res.currency',string="Currency",compute="_compute_currencies")
    
    price4 = fields.Monetary('Price 4',currency_field="currency4_id",compute="_compute_prices")
    currency4_id = fields.Many2one('res.currency',string="Currency",compute="_compute_currencies")
    
    price5 = fields.Monetary('Price 5',currency_field="currency5_id",compute="_compute_prices")
    currency5_id = fields.Many2one('res.currency',string="Currency",compute="_compute_currencies")
    
    price6 = fields.Monetary('Price 6',currency_field="currency6_id",compute="_compute_prices")
    currency6_id = fields.Many2one('res.currency',string="Currency",compute="_compute_currencies")
    
    price7 = fields.Monetary('Price 7',currency_field="currency7_id",compute="_compute_prices")
    currency7_id = fields.Many2one('res.currency',string="Currency",compute="_compute_currencies")
    
    price8 = fields.Monetary('Price 8',currency_field="currency8_id",compute="_compute_prices")
    currency8_id = fields.Many2one('res.currency',string="Currency",compute="_compute_currencies")
    
    price9 = fields.Monetary('Price 9',currency_field="currency9_id",compute="_compute_prices")
    currency9_id = fields.Many2one('res.currency',string="Currency",compute="_compute_currencies")
     
    def _compute_prices(self):
        for a in self:
            values = {}
            if self.env.user.company_id.pricelist1_id:
                values['price1']=self.env.user.company_id.pricelist1_id.price_get(a.id,1).get(self.env.user.company_id.pricelist1_id.id,0)
            if self.env.user.company_id.pricelist2_id:
                values['price2']=self.env.user.company_id.pricelist2_id.price_get(a.id,1).get(self.env.user.company_id.pricelist2_id.id,0)
            if self.env.user.company_id.pricelist3_id:
                values['price3']=self.env.user.company_id.pricelist3_id.price_get(a.id,1).get(self.env.user.company_id.pricelist3_id.id,0)
            if self.env.user.company_id.pricelist4_id:
                values['price4']=self.env.user.company_id.pricelist4_id.price_get(a.id,1).get(self.env.user.company_id.pricelist4_id.id,0)
            if self.env.user.company_id.pricelist5_id:
                values['price5']=self.env.user.company_id.pricelist5_id.price_get(a.id,1).get(self.env.user.company_id.pricelist5_id.id,0)
            if self.env.user.company_id.pricelist6_id:
                values['price6']=self.env.user.company_id.pricelist6_id.price_get(a.id,1).get(self.env.user.company_id.pricelist6_id.id,0)
            if self.env.user.company_id.pricelist7_id:
                values['price7']=self.env.user.company_id.pricelist7_id.price_get(a.id,1).get(self.env.user.company_id.pricelist7_id.id,0)
            if self.env.user.company_id.pricelist8_id:
                values['price8']=self.env.user.company_id.pricelist8_id.price_get(a.id,1).get(self.env.user.company_id.pricelist8_id.id,0)
            if self.env.user.company_id.pricelist9_id:
                values['price9']=self.env.user.company_id.pricelist9_id.price_get(a.id,1).get(self.env.user.company_id.pricelist9_id.id,0)    
            a.write(values)
            
    def _compute_currencies(self):
        for a in self:
            values = {}
            if self.env.user.company_id.pricelist1_id:
                values['currency1_id']=self.env.user.company_id.pricelist1_id.currency_id.id
            if self.env.user.company_id.pricelist2_id:
                values['currency2_id']=self.env.user.company_id.pricelist2_id.currency_id.id
            if self.env.user.company_id.pricelist3_id:
                values['currency3_id']=self.env.user.company_id.pricelist3_id.currency_id.id
            if self.env.user.company_id.pricelist4_id:
                values['currency4_id']=self.env.user.company_id.pricelist4_id.currency_id.id
            if self.env.user.company_id.pricelist5_id:
                values['currency5_id']=self.env.user.company_id.pricelist5_id.currency_id.id
            if self.env.user.company_id.pricelist6_id:
                values['currency6_id']=self.env.user.company_id.pricelist6_id.currency_id.id
            if self.env.user.company_id.pricelist7_id:
                values['currency7_id']=self.env.user.company_id.pricelist7_id.currency_id.id
            if self.env.user.company_id.pricelist8_id:
                values['currency8_id']=self.env.user.company_id.pricelist8_id.currency_id.id
            if self.env.user.company_id.pricelist9_id:
                values['currency9_id']=self.env.user.company_id.pricelist9_id.currency_id.id  
            a.write(values)
            
class Company(models.Model):
    _inherit = 'res.company'
    
    
    pricelist1_id = fields.Many2one('product.pricelist',string="Pricelist for field 1")
    pricelist2_id = fields.Many2one('product.pricelist',string="Pricelist for field 2")
    pricelist3_id = fields.Many2one('product.pricelist',string="Pricelist for field 3")
    pricelist4_id = fields.Many2one('product.pricelist',string="Pricelist for field 4")
    pricelist5_id = fields.Many2one('product.pricelist',string="Pricelist for field 5")
    pricelist6_id = fields.Many2one('product.pricelist',string="Pricelist for field 6")
    pricelist7_id = fields.Many2one('product.pricelist',string="Pricelist for field 7")
    pricelist8_id = fields.Many2one('product.pricelist',string="Pricelist for field 8")
    pricelist9_id = fields.Many2one('product.pricelist',string="Pricelist for field 9")
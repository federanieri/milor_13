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
from odoo.osv import expression


class ProductCategory(models.Model):
    _inherit = "product.public.category"
    
    category_ids = fields.Many2many('product.category',string="Categories")
    
    def fill_category(self):
        for a in self:
            a.product_tmpl_ids = [(6,0,[])]
            for c in a.category_ids:
                templates = self.env['product.template'].search([('categ_id','child_of',c.id)])
                a.product_tmpl_ids = [(4, t.id, False) for t in templates]
            
    
   
                        
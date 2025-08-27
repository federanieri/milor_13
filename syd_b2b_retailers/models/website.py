# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request


class Website(models.Model):
    _inherit = 'website'

    is_b2b_website = fields.Boolean(string='Is B2B Website')
    
    def get_current_pricelist(self):
         
        self.ensure_one()
        if self.is_b2b_website:
            partner = self.env.user.partner_id
            pl = partner.property_product_pricelist
            return pl
        else:
            return super(Website,self).get_current_pricelist()
        
class Http(models.AbstractModel):
    _inherit = 'ir.http'
     
    @classmethod
    def _dispatch(cls):
        return super(Http,cls)._dispatch()
#         req_page = request.httprequest.path
#         page_domain = [('url', '=', req_page)] + request.website.website_domain()
#  
#         published_domain = page_domain
#         # specific page first
#         page = request.env['website.page'].sudo().search(published_domain, order='website_id asc', limit=1)
#          
#         if request.is_frontend and request.website.is_b2b_website and not request.env.user.user_has_groups('syd_b2b_retailers.group_retailers'):
#             raise AccessDenied()
#         else:
#             return result
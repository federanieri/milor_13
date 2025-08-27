# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo import api, fields, models

class ProductWishlist(models.Model):
    _inherit = 'product.wishlist'
    
    
    @api.model
    def current(self):
        wish = super(ProductWishlist,self).current()
        if self.env.user.partner_id.selected_client_id:
            return wish.filtered(lambda x: x.sudo().product_id.product_brand_id.id in self.env.user.partner_id.selected_client_id.product_brand_ids.ids )
        else:
            return wish
        
class Website(models.Model):
    _inherit = 'website'

    
    @api.model
    def sale_get_payment_term(self, partner):
        if partner.selected_client_id and partner.selected_client_id.property_payment_term_id:
            return partner.selected_client_id.property_payment_term_id.id
        return (
            partner.property_payment_term_id or
            self.env.ref('account.account_payment_term_immediate', False) or
            self.env['account.payment.term'].sudo().search([('company_id', '=', self.company_id.id)], limit=1)
        ).id
        
    def get_current_pricelist(self):
         
        self.ensure_one()
        if self.is_b2b_website:
            partner = self.env.user.partner_id
            if partner.selected_client_id:
                pl = partner.selected_client_id.property_product_pricelist
            else:
                pl = partner.property_product_pricelist
            return pl
        else:
            return super(Website,self).get_current_pricelist()

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    salesman_partner_id = fields.Many2one(comodel_name='res.partner', string='Agent')
    
    @api.model
    def create(self, vals):
        if vals.get('partner_id') and vals.get('website_id'):
            selected_client_id = self.env['res.partner'].browse(vals['partner_id']).selected_client_id.id
            if selected_client_id:
                vals.update(
                    partner_id=selected_client_id,
                    partner_invoice_id=selected_client_id,
                    salesman_partner_id=vals['partner_id']
                )
        return super(SaleOrder, self).create(vals)

    def write(self, vals):
        if self.env.context.get('website_id'):
            Partner = self.env['res.partner']
            if vals.get('partner_id'):
                partner = Partner.browse(vals['partner_id'])
                if partner.selected_client_id:
                    vals['partner_id'] = partner.selected_client_id.id
            if vals.get('partner_invoice_id'):
                partner = Partner.browse(vals['partner_invoice_id'])
                if partner.selected_client_id:
                    vals['partner_invoice_id'] = partner.selected_client_id.id
        return super(SaleOrder, self).write(vals)

class returnOrderSheet(models.Model):
    _inherit = 'return.order.sheet'

    salesman_partner_id = fields.Many2one(comodel_name='res.partner', string='Agent')
    
    @api.model
    def create(self, vals):
        if vals.get('partner_id') and bool(vals.get('from_web')):
            selected_client_id = self.env['res.partner'].browse(vals['partner_id']).selected_client_id.id
            if selected_client_id:
                vals.update(
                    partner_id=selected_client_id,
                    salesman_partner_id=vals['partner_id']
                )
        return super(returnOrderSheet, self).create(vals)

    def write(self, vals):
        if self.env.context.get('website_id'):
            Partner = self.env['res.partner']
            if vals.get('partner_id'):
                partner = Partner.browse(vals['partner_id'])
                if partner.selected_client_id:
                    vals['partner_id'] = partner.selected_client_id.id
        return super(returnOrderSheet, self).write(vals)

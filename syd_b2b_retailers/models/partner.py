# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    product_brand_ids = fields.Many2many('common.product.brand.ept', string='Brands')
    is_retailer = fields.Boolean(string="Is Retailer")
    fixed_invoice_partner_id = fields.Many2one('res.partner',string="Fixed Invoice Address")
    
    @api.model
    def create(self, values):
        res = super(ResPartner, self).create(values)
        if values.get('is_retailer'):
            res.user_ids.write({
                'groups_id': [(4, self.env.ref('syd_b2b_retailers.group_retailers').id)]

                })
        for b in res.product_brand_ids:
            if b.group_id:
                res.user_ids.write({'groups_id': [(4, b.group_id.id, False)]})
        return res


    def write(self, values):
        brandedited= False
        if 'product_brand_ids' in values:
            for a in self:
                for b in a.product_brand_ids:
                    if b.group_id:
                        a.user_ids.write({'groups_id': [(3, b.group_id.id, False)]})
            brandedited= True
        res = super(ResPartner, self).write(values)
        if values.get('is_retailer'):
            self.user_ids.write({
                'groups_id': [(4, self.env.ref('syd_b2b_retailers.group_retailers').id)]

                })
        elif 'is_retailer' in values:
            self.user_ids.write({
                'groups_id': [(3, self.env.ref('syd_b2b_retailers.group_retailers').id,False)]

                })    
        if brandedited:
            for a in self:
                for b in a.product_brand_ids:
                    if b.group_id:
                        a.user_ids.write({'groups_id': [(4, b.group_id.id, False)]})
        return res

class Brand(models.Model):
    _inherit="common.product.brand.ept"
    
    group_id = fields.Many2one('res.groups',string="Groups",readonly=True,ondelete='set null')
    group_name = fields.Char('Group Name',readonly=True)
    
    def generate_groups(self):
        self.ensure_one()
        res_group = self.env['res.groups'].create({
                                                    'name': 'Group Brand %s'%self.name
                                                    })
        ir_model = self.env['ir.model.data'].create({
                'name': self.name.replace(" ","_").replace(".","_").lower(),
                'model': 'res.groups',
                'module': '__retailers__',
                'res_id': res_group.id,
                'noupdate': True,  # If it's False, target record (res_id) will be removed while module update
            })
        self.write({
                    'group_id':res_group.id,
                    'group_name':"%s.%s"%(ir_model.module,ir_model.name)
                    })
        
class PortalWizardUser(models.TransientModel):
    _inherit = 'portal.wizard.user'
    
    
    def action_apply(self):
        super(PortalWizardUser,self).action_apply()
        for wizard_user in self.sudo().with_context(active_test=False):
            if wizard_user.partner_id.is_retailer:
                wizard_user.partner_id.user_ids.write({
                    'groups_id': [(4, self.env.ref('syd_b2b_retailers.group_retailers').id)]
    
                    })
                for b in wizard_user.partner_id.product_brand_ids:
                    if b.group_id:
                        wizard_user.partner_id.user_ids.write({'groups_id': [(4, b.group_id.id, False)]})
                        
                        
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    @api.model
    def create(self, values):
        partner_id = self.env['res.partner'].browse(values['partner_id']) if 'partner_id' in values else False
        if partner_id.fixed_invoice_partner_id:
            values['partner_invoice_id'] = partner_id.fixed_invoice_partner_id.id
        return super(SaleOrder, self).create(values)


    def write(self, values):
        partner_id = self.env['res.partner'].browse(values['partner_id']) if 'partner_id' in values else (self.partner_id)
        if partner_id.fixed_invoice_partner_id:
            values['partner_invoice_id'] = partner_id.fixed_invoice_partner_id.id
        return super(SaleOrder, self).write(values)
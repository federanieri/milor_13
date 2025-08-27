# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_agent = fields.Boolean(string="Is B2B Agent")
    selected_client_id = fields.Many2one(comodel_name='res.partner',copy=False)
    salesman_partner_id = fields.Many2one('res.partner',string="Agente") 
    customer_of_salesman_ids = fields.One2many('res.partner','salesman_partner_id',string="Retailers") 
    
    def _reset_brand_group(self, old_partner, new_partner):
        total_brands = self.env['common.product.brand.ept'].search([])
        for brand in total_brands.filtered(lambda p: p.group_id):
            self.user_ids.write({'groups_id': [(3, brand.group_id.id, False)]})
        for brand in new_partner.product_brand_ids.filtered(lambda p: p.group_id):
            self.user_ids.write({'groups_id': [(4, brand.group_id.id, False)]})

    def write(self,values):
        res = super(ResPartner, self).write(values)
        if values.get('is_agent'):
            self.user_ids.write({
                'groups_id': [(4, self.env.ref('syd_ecommerce_agent.group_portal_agent').id)]

                })
        elif 'is_agent' in values:
            self.user_ids.write({
                'groups_id': [(3, self.env.ref('syd_ecommerce_agent.group_portal_agent').id,False)]

                })   
        return res
         
class PortalWizardUser(models.TransientModel):
    _inherit = 'portal.wizard.user'

    def action_apply(self):
        super(PortalWizardUser,self).action_apply()
        for wizard_user in self.sudo().with_context(active_test=False):
            if wizard_user.partner_id.is_agent:
                wizard_user.partner_id.user_ids.write({
                    'groups_id': [(4, self.env.ref('syd_ecommerce_agent.group_portal_agent').id)]
                })
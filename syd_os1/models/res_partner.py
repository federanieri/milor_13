# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class Country(models.Model):
    _inherit = 'res.country'
    
    os1_id_nation = fields.Char('IdNazione')
    
    def get_nation_code(self):
        account_os1 = self.env['syd_os1.os1.account'].getAccountOS1()
        nations = account_os1.get_nation_code()
        for nation in nations:
            nation_id = self.search([('code','=',nation['IdIso'])])
            if bool(nation_id) and len(nation_id) == 1:
                if not bool(nation_id.os1_id_nation):
                    nation_id.os1_id_nation = nation['IdNazione']

class Partner(models.Model):
    _inherit = "res.partner"
    
    get_unique_code = fields.Boolean('Unique code obtained')
    already_sent = fields.Boolean('Already sent')
    
    def getUniqueCode(self):
        for partner in self:
            account_os1 = partner.env['syd_os1.os1.account'].getAccountOS1()
            account_os1.getUniqueCode(partner)
    
    def createTemporaryCustomers(self):
        for partner in self.filtered(lambda rp: rp.already_sent == False and rp.get_unique_code == False and ( rp.fm_code == False or rp.fm_code == '' )):
            account_os1 = self.env['syd_os1.os1.account'].getAccountOS1()
            if bool(account_os1):
                if partner.web_customer == True and partner.country_id.id not in self.env.ref('base.europe').country_ids.ids:
                    account_os1.createCustomers(partner, True)
                for address_partner_id in partner.child_ids.filtered(lambda rp: rp.type == 'delivery'):
                    if partner.web_customer == True and partner.country_id.id not in self.env.ref('base.europe').country_ids.ids:
                        account_os1.createCustomers(address_partner_id, True)
    
    @api.model
    def cronCreateTemporaryCustomers(self):
        for partner in self.env['res.partner'].search([('already_sent','=',False),('get_unique_code','=',False),'|',('customer_rank','>', 0),('supplier_rank','>', 0),'|',('fm_code','=',False),('fm_code','=','')]):
            account_os1 = self.env['syd_os1.os1.account'].getAccountOS1()
            if bool(account_os1):
                if partner.web_customer == True and partner.country_id.id not in self.env.ref('base.europe').country_ids.ids:
                    account_os1.createCustomers(partner, True)
                for address_partner_id in partner.child_ids.filtered(lambda rp: rp.type == 'delivery'):
                    if partner.web_customer == True and partner.country_id.id not in self.env.ref('base.europe').country_ids.ids:
                        account_os1.createCustomers(address_partner_id, True)
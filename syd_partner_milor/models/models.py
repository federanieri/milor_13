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


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    delivery_partner_id = fields.Many2one('res.partner',string="Spedizioniere")
    
    
    @api.onchange('carrier_id')
    @api.constrains('carrier_id')
    def _delivery_partner_id(self):
        for a in self:
            if not a.delivery_partner_id and a.carrier_id.delivery_partner_id:
                a.delivery_partner_id = a.carrier_id.delivery_partner_id.id

    @api.constrains('state')
    def _constraint_state(self):
        for pick in self:
            if pick.state == 'done' and pick.picking_type_id.block_empty_fmcode and not pick.partner_id.fm_code:
                raise ValidationError(_("Can't validate: Partner %s has not OS1: Code." % pick.partner_id.display_name))
                   
class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'
    
    os1_code = fields.Char('OS1 Code')
    delivery_partner_id = fields.Many2one('res.partner',string="Spedizioniere")
    os1_dp_code = fields.Char('OS1 Spedizioniere ID',related="delivery_partner_id.fm_code")
    
class PaymentTerms(models.Model):
    _inherit = 'account.payment.term'
    
    os1_code = fields.Char('OS1 Code')

class Currency(models.Model):
    _inherit = 'res.currency'
    
    os1_code = fields.Char('OS1 Code')

class IVACode(models.Model):
    _inherit = 'account.tax'
    
    os1_code = fields.Char('OS1 Code')
    
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    salesman_partner_id = fields.Many2one('res.partner',string="Agente") 

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    fm_code = fields.Char('OS1: Code',compute="_fm_code",store=True)
    fm_type = fields.Char('OS1: ID Conto TP')
    fm_id= fields.Char('OS1: Id')
    fm_subtype_id = fields.Char('OS1: Subtype Id')
    
    filemaker_code = fields.Char('Filemaker Code')
    
    other_data= fields.Char('Other Data')
    phone2 = fields.Char('Phone 2')
    fax = fields.Char('Fax')
    telex = fields.Char('Telex')
    
    salesman_partner_id = fields.Many2one('res.partner',string="IdAgente1")
    salesman_partner_2_id = fields.Many2one('res.partner',string="IdAgente2")
    
    salesman_parent_partner_id = fields.Many2one('res.partner',string="IdAgenteC")
    
    carrier_partner_id = fields.Many2one('res.partner',string="IdSpedizione1")
    carrier_partner_2_id = fields.Many2one('res.partner',string="IdSpedizione2")
    
    agent_pricelist_ids = fields.Many2many('product.pricelist',string='Listini Agente')
    agent_product_brand_ids = fields.Many2many('common.product.brand.ept','agent_product_brand','agent_id','brand_id',string='Brand Agente')
    
    customer_currency_id = fields.Many2one('res.currency',string='Customer Currency')
    
    def _get_name(self):
        result = super(ResPartner,self)._get_name()
        if self.fm_code:
            result = "%s (%s)" % (result,self.fm_code)
        return result
    
    @api.depends('fm_subtype_id','fm_type','fm_id')
    def _fm_code(self):
        for a in self:
            if a.fm_subtype_id:
                a.fm_code = "%s%s-%s" %((a.fm_type if a.fm_type else''),(a.fm_id if a.fm_id else ''),(a.fm_subtype_id if a.fm_subtype_id else ''))
            else:
                a.fm_code = "%s%s" %((a.fm_type if a.fm_type else''),(a.fm_id if a.fm_id else ''))
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        
        domain = expression.AND([[], args])
        if operator in ('ilike', 'like', '=', '=like', '=ilike'):
                domain = expression.AND([
                    args or [],
                    ['|', ('name', operator, name), ('fm_code', operator, name)]
                ])
        partner_ids = self._search(domain, limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(partner_ids).with_user(name_get_uid))

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    block_empty_fmcode = fields.Boolean(string="Block Pickings without OS1: Code (FmCode)", help="Block Picking if `OS1: Code` (FmCode) in Partner is missing.")
    
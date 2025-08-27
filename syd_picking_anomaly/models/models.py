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

class Location(models.Model):
    _inherit = "stock.location"
    
    anomaly = fields.Boolean('Possible Anomaly',default=False,help='Transfer to this location can have anomaly')

class Picking(models.Model):
    _inherit = "stock.picking"
    
    anomaly = fields.Boolean('Possible Anomaly',related="location_dest_id.anomaly")

class Anomaly(models.Model):
    _name = "syd_anomaly.anomaly"
    _description = 'Anomaly'
    
    name = fields.Char("Anomaly Name")
    
class AnomalyPicking(models.Model):
    _name = "syd_anomaly.anomaly_picking"
    _description = 'Anomaly Picking'
    
    name=fields.Char('Name',related="anomaly_id.name")
    anomaly_id = fields.Many2one("syd_anomaly.anomaly",string="Anomaly",required=True)
    description = fields.Html('Description',required=True)
    picking_id = fields.Many2one('stock.picking',string="Picking",required=True)
    origin_purchase_id = fields.Many2one('purchase.order',string='Ordine',related="picking_id.origin_purchase_id",store=True)
    origin_vendor_id = fields.Many2one('res.partner', string='Fornitore',store=True)
    send_to_partner = fields.Boolean('Send Mail')
    
    
    @api.onchange('picking_id')
    def _origin_vendor_id(self):
        for a in self:
            a.origin_vendor_id = a.picking_id.origin_vendor_id.id
    
    @api.model
    def create(self,vals):
        res = super(AnomalyPicking,self).create(vals)
        partner_id = self.env.context.get('add_partner_id',False)
        res.message_anomaly(partner_id)
        return res
        
    def message_anomaly(self,partner_id=False):
        for a in self:
            subject = a.name
            body = a.description
            if a.origin_purchase_id:
                body += "<br /> PO: %s" % a.origin_purchase_id.name
                subject = "PO: %s - "% a.origin_purchase_id.name + subject
            a.picking_id.message_post(body=body, subject=subject)
            if a.origin_purchase_id:
                a.origin_purchase_id.message_post(body=body, subject=subject,message_type='comment',subtype='mail.mt_comment',partner_ids=[a.origin_purchase_id.partner_id.id]+a.origin_purchase_id.message_partner_ids.ids+([partner_id.id] if partner_id else []))
        
# -*- encoding: utf-8 -*-


from odoo import _, tools
from odoo import models, fields, api


class Region(models.Model):
    _name = 'res.region'
    _description = 'Region'
    
    name = fields.Char('Region Name',
                            help='The full name of the region.',
                            required=True)
    country_id=  fields.Many2one('res.country', 'Country')
    


class Province(models.Model):
    _inherit = 'res.country.state'

    region_id = fields.Many2one('res.region', 'Region')
    
class Partner(models.Model):
    _inherit = 'res.partner'
    
    
    region_id = fields.Many2one('res.region', 'Region',related="state_id.region_id",readonly=True)



# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError



class ProductFilters(models.Model):
	_name = 'product.filter'
	_description = 'Filter Product'
	_order = 'group_id'

	name = fields.Char('Name',translate=True)
	type = fields.Selection([
		('radio', 'Radio'),
		('select', 'Select'),
		('image', 'Image'),
		('color', 'Color')], default='radio', required=True)
	group_id = fields.Many2one('group.filter','Group Filter',required=True,default=lambda self: self.env['group.filter'].search([('name','=','Other Filters')],limit=1))
	filter_value_ids = fields.One2many('product.filter.value','filter_id',string="Filter Values",)
	group_ids = fields.Many2many('res.groups',string='Group Visible')

class FilterProductValue(models.Model):
	_name = 'product.filter.value' 
	_description = 'Filter Product Value'

	

	name = fields.Char('Filter Values Name',translate=True)
	filter_id = fields.Many2one('product.filter','Filter Name')
	
	html_color = fields.Char(
		string='HTML Color Index', oldname='color',
		help="""Here you can set a
		specific HTML color index (e.g. #ff0000) to display the color if the
		filterer type is 'Color'.""")
	
	filter_domain = fields.Char('Product Filter', help="Filter on the object")
	model_name = fields.Char(default='product.template', string='Model Name', readonly=True, store=True)
	group_ids = fields.Many2many('res.groups',string='Group Visible')
	image_1920 = fields.Image("Image",max_width=1920, max_height=1920)
    # resized fields stored (as attachment) for performance
	image_1024 = fields.Image("Image 1024", related="image_1920", max_width=1024, max_height=1024)
	image_512 = fields.Image("Image 512", related="image_1920", max_width=512, max_height=512)
	image_256 = fields.Image("Image 256", related="image_1920", max_width=256, max_height=256)
	image_128 = fields.Image("Image 128", related="image_1920", max_width=128, max_height=128)    
    
    

class FilterProductGroup(models.Model):
	_name = 'group.filter'
	_description = 'Filter Group'

	name = fields.Char('Filter Group Name',translate=True)
	group_ids = fields.Many2many('res.groups',string='Group Visible')

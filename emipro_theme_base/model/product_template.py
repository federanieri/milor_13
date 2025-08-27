# -*- coding: utf-8 -*-
"""
    This model is used to show the tab line filed in product template
"""
from odoo.exceptions import Warning
from odoo import fields, models, api

class ProductTemplate(models.Model):
    _inherit = "product.template"

    label_line_ids = fields.One2many('product.label.line', 'product_tmpl_id', 'Product Labels',help="Set the number of product labels")
    product_brand_ept_id = fields.Many2one(
        'product.brand.ept',
        string='Brand',
        help='Select a brand for this product',
        compute="_product_brand_ept_id",store=True
    )
    tab_line_ids = fields.One2many('product.tab.line', 'product_id', 'Product Tabs',help="Set the product tabs")
    document_ids = fields.One2many('ir.attachment', 'product_tmpl_id', string='Documents',
                                   help="Upload the document for display in website.")

    @api.depends('product_brand_id','product_brand_id.product_brand_ept_ids')
    def _product_brand_ept_id(self):
        for a in self:
            if a.product_brand_id and a.product_brand_id.product_brand_ept_ids:
                a.product_brand_ept_id = a.product_brand_id.product_brand_ept_ids[0].id
            else:
                a.product_brand_ept_id = False

    @api.constrains('tab_line_ids')
    def check_tab_lines(self):
        if len(self.tab_line_ids) > 4:
            raise Warning("You can not create more then 4 tabs!!")
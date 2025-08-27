import base64
import datetime

import requests
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from requests.exceptions import ConnectionError
from werkzeug import urls
import logging
from odoo.exceptions import ValidationError
from odoo.http import request
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)


class KsProduct(models.Model):
    _inherit = 'product.template'

    ks_length = fields.Float()
    ks_width = fields.Float()
    ks_height = fields.Float()
    ks_to_be_export = fields.Boolean('To be export on WooCommerce')
    ks_woo_variant_count = fields.Integer(default=0, compute='_ks_count_woo_variant', store=True)
    ks_woo_id = fields.Integer('Woo Id', track_visibility='onchange', default=0,
                               help="""Woo Id: Unique WooCommerce resource id for the product on the specified 
                                   WooCommerce Instance""")
    ks_woo_instance_id = fields.Many2one('ks.woocommerce.instances', track_visibility='onchange',
                                         string='Woo Instance',
                                         help="""WooCommerce Instance: Ths instance of woocomerce to which this 
                                             product variant belongs to.""")
    ks_woo_product_has_variant = fields.Boolean()
    ks_woo_product_type = fields.Selection([('simple', 'Simple Product'), ('grouped', 'Grouped Product'),
                                            ('variable', 'Variable Product')], readonly=True,
                                           string='Woo Product Type', store=True, compute='_ks_compute_product_type')
    ks_exported_in_woo = fields.Boolean('Exported in Woo',
                                        readonly=True,
                                        store=True,
                                        compute='_ks_compute_export_in_woo',
                                        help="""Exported in Woo: If enabled, the product is synced with the specified 
                                        WooCommerce Instance""")
    ks_woo_categories = fields.Many2many('product.category',
                                         string='Woo Categories',
                                         domain="[('ks_woo_instance_id', '=', ks_woo_instance_id)]",
                                         help="""Woo Categories: If this field is empty, then no category will be 
                                         exported on woo. \n [This will include the the category you selected on the 
                                         general information tab for the product]""")
    ks_woo_tag = fields.Many2many('ks.woo.product.tag',
                                  string='Woo Tags', domain="[('ks_woo_instance_id', '=', ks_woo_instance_id)]",
                                  help="""Woo Categories: If this field is empty, then no category will be 
                                   exported on woo."""
                                  )
    ks_woo_status = fields.Boolean('Woo Status',
                                   copy=False,
                                   help="""Woo Status: If enabled that means the product is published on the WooCommerce 
                                   Instance.""")
    ks_date_created = fields.Datetime('Created On',
                                      readonly=True,
                                      help="Created On: Date on which the WooCommerce Product has been created")
    ks_date_updated = fields.Datetime('Updated On',
                                      readonly=True,
                                      help="Updated On: Date on which the WooCommerce Product has been last updated")
    ks_product_image_ids = fields.One2many('ks.woo.product.image', 'ks_product_tmpl_id',
                                           string='Gallery Images',
                                           help="""Gallery Images: This includes all the images for the synced product
                                                 including the display image.""")
    ks_woo_description = fields.Html(help="Message displayed as product description on WooCommerce")
    ks_woo_short_description = fields.Html(help="Message displayed as product short description on WooCommerce")
    ks_average_rating = fields.Float(help="""Average Rating: Average rating for the product on WooCommerce""")
    ks_woo_regular_price = fields.Float('Woo regular price')
    ks_woo_sale_price = fields.Float('Woo Sale Price')
    ks_woo_visible_attributes = fields.Text(readonly=1)
    ks_update_false = fields.Boolean('Update False', default=False)
    ks_file_type = fields.Char(string='FileType')
    ks_woo_regular_pricelist = fields.Many2one('product.pricelist', string="Regular Pricelist", readonly=True,
                                               compute="ks_update_pricelist")
    ks_woo_sale_pricelist = fields.Many2one('product.pricelist', string="Sale Pricelist", readonly=True,
                                            compute="ks_update_pricelist")
    ks_sync_date = fields.Datetime('Modified On', readonly=True,
                                   help="Sync On: Date on which the record has been modified")
    ks_last_exported_date = fields.Datetime('Last Synced On', readonly=True)
    ks_sync_status = fields.Boolean('Sync Status', compute='sync_update', default=False)

    def sync_update(self):
        for rec in self:
            if rec.ks_last_exported_date and rec.ks_sync_date:
                ks_reduced_ks_sync_time = rec.ks_last_exported_date - datetime.timedelta(seconds=60)
                ks_increased_ks_sync_time = rec.ks_last_exported_date + datetime.timedelta(seconds=60)
                if rec.ks_sync_date > ks_reduced_ks_sync_time and rec.ks_sync_date < ks_increased_ks_sync_time:
                    rec.ks_sync_status = True
                else:
                    rec.ks_sync_status = False
            else:
                rec.ks_sync_status = False

    def ks_sync_price(self):
        woo_products = self.search([('ks_woo_instance_id', '!=', False)])
        for record in woo_products:
            if record.ks_woo_instance_id and record.ks_woo_product_type == 'simple':
                if record.list_price > 0 and record.ks_woo_regular_price <= 0:
                    record.write({
                        'ks_woo_regular_price': record.list_price,
                    })
            elif record.ks_woo_instance_id and record.ks_woo_product_type == 'variable':
                product_variant = record.product_variant_ids
                for rec in product_variant:
                    if rec.lst_price > 0 and rec.ks_woo_variant_reg_price <= 0:
                        rec.write({
                            'ks_woo_variant_reg_price': rec.lst_price,
                        })

    # This function is used to set sale price or regular price onchange of list price in the general tab
    @api.onchange('list_price')
    def onchange_list_price(self):
        """
        :return: none
        """
        for rec in self:
            if rec.ks_woo_sale_price:
                rec.ks_woo_sale_price = rec.list_price
            else:
                rec.ks_woo_regular_price = rec.list_price

    # This function is used to set the regular and onsale pricelist on the product view
    def ks_update_pricelist(self):
        """
        :return: none
        """
        for rec in self:
            rec.ks_woo_regular_pricelist = rec.ks_woo_instance_id.ks_woo_pricelist.id
            rec.ks_woo_sale_pricelist = rec.ks_woo_instance_id.ks_woo_sale_pricelist.id

    # This function is used to open the regular pricelist tree view with respective product
    def open_regular_pricelist_rules_data(self):
        """
        :return: The tree view for the regular pricelist
        """
        self.ensure_one()
        domain = ['|',
                  ('product_tmpl_id', '=', self.id),
                  ('product_id', 'in', self.product_variant_ids.ids),
                  ('currency_id', '=', self.ks_woo_instance_id.ks_woo_currency.id),
                  ('pricelist_id', '=', self.ks_woo_regular_pricelist.id)
                  ]
        return {
            'name': _('Price Rules'),
            'view_mode': 'tree,form',
            'views': [(self.env.ref('product.product_pricelist_item_tree_view_from_product').id, 'tree'),
                      (False, 'form')],
            'res_model': 'product.pricelist.item',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain,
            'context': {
                'default_product_tmpl_id': self.id,
                'default_applied_on': '1_product',
                'product_without_variants': self.product_variant_count == 1,
            },
        }

    # This function is used to open the sale pricelist tree view with respective product
    def open_sale_pricelist_rules_data(self):
        """
        :return: The tree view for the sale pricelist
        """
        self.ensure_one()
        domain = ['|',
                  ('product_tmpl_id', '=', self.id),
                  ('product_id', 'in', self.product_variant_ids.ids),
                  ('currency_id', '=', self.ks_woo_instance_id.ks_woo_currency.id),
                  ('pricelist_id', '=', self.ks_woo_sale_pricelist.id)
                  ]
        return {
            'name': _('Price Rules'),
            'view_mode': 'tree,form',
            'views': [(self.env.ref('product.product_pricelist_item_tree_view_from_product').id, 'tree'),
                      (False, 'form')],
            'res_model': 'product.pricelist.item',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain,
            'context': {
                'default_product_tmpl_id': self.id,
                'default_applied_on': '1_product',
                'product_without_variants': self.product_variant_count == 1,
            },
        }

    # @api.onchange('ks_woo_regular_price')
    # def onchange_ks_woo_regular_price(self):
    #     if self.browse(self.ids[0]):
    #         self.browse(self.ids[0]).ks_woo_regular_price = self.ks_woo_regular_price
    #
    # @api.onchange('ks_woo_sale_price')
    # def onchange_ks_woo_sale_price(self):
    #     if self.browse(self.ids[0]):
    #         self.browse(self.ids[0]).ks_woo_sale_price = self.ks_woo_sale_price

    # This function is used to update the regular pricelist when there is any change in the regular price on product
    @api.constrains('ks_woo_regular_price')
    def change_regular_price_in_pricelist(self):
        """
        :return: none
        """
        for rec in self:
            if rec.ks_woo_regular_price >= rec.ks_woo_sale_price:
                rec.ks_woo_instance_id.ks_woo_pricelist.item_ids.search(
                    [('pricelist_id', '=', rec.ks_woo_instance_id.ks_woo_pricelist.id),
                     ('applied_on', '=', '0_product_variant'),
                     ('product_tmpl_id', '=', rec.id),
                     ('compute_price', '=', 'fixed'),
                     ('ks_instance_id', '=', rec.ks_woo_instance_id.id)],
                    limit=1).fixed_price = rec.ks_woo_regular_price
            else:
                raise ValidationError("Regular price cannot be less than Sale price !")
            if not rec.ks_woo_sale_price:
                rec.list_price = rec.ks_woo_regular_price
            else:
                rec.list_price = rec.ks_woo_sale_price

    # This function is used to update the sale pricelist when there is any change in the sale price on product
    @api.constrains('ks_woo_sale_price')
    def change_sale_price_in_pricelist(self):
        """
        :return: none
        """
        for rec in self:
            if rec.ks_woo_sale_price <= rec.ks_woo_regular_price:
                rec.ks_woo_instance_id.ks_woo_sale_pricelist.item_ids.search(
                    [('pricelist_id', '=', rec.ks_woo_instance_id.ks_woo_sale_pricelist.id),
                     ('applied_on', '=', '0_product_variant'),
                     ('product_tmpl_id', '=', rec.id),
                     ('compute_price', '=', 'fixed'),
                     ('ks_instance_id', '=', rec.ks_woo_instance_id.id)],
                    limit=1).fixed_price = rec.ks_woo_sale_price
            else:
                raise ValidationError("Sale price cannot be more than Regular price !")
            if rec.ks_woo_sale_price:
                rec.list_price = rec.ks_woo_sale_price
            else:
                rec.list_price = rec.ks_woo_regular_price

    def unlink(self):
        woo_product_ids = self.mapped('ks_woo_id')
        woo_instance_ids = self.mapped('ks_woo_instance_id.id')
        res = super(KsProduct, self).unlink()
        if woo_product_ids:
            for each_instance in woo_instance_ids:
                for each_rec in woo_product_ids:
                    woo_private_attribute = self.env['product.attribute'].search([('ks_woo_id', '=', -1),
                                                                                  ('ks_woo_instance_id', '=',
                                                                                   each_instance),
                                                                                  ('ks_slug', '=',
                                                                                   'product_' + str(each_rec))])
                    if woo_private_attribute:
                        woo_private_attribute.unlink()
        return res

    @api.onchange('ks_product_image_ids')
    def _onchange_ks_product_image_ids(self):
        a = 1
        if self.ks_product_image_ids and self.ks_to_be_export:
            if -1 in self.ks_product_image_ids.mapped('sequence'):
                ks_temp = self.ks_product_image_ids
                ks_sequence = self.ks_change_sequence(ks_temp)
            elif self.ks_product_image_ids.mapped('sequence').count(0) > 1:
                ks_temp = self.ks_product_image_ids
                ks_arrange_from_wizard = self.ks_arrange_from_wizard(ks_temp)
            elif 0 not in self.ks_product_image_ids.mapped('sequence'):
                ks_temp = self.ks_product_image_ids
                ks_sequence_ = self.ks_decrease_sequence(ks_temp)
            for each_rec in self.ks_product_image_ids:
                if 0 in self.ks_product_image_ids.mapped('sequence'):
                    if each_rec.sequence == 0:
                        self.image_1920 = each_rec.ks_image
                        self.ks_file_type = each_rec.ks_file_name
                        each_rec.ks_src = True
                else:
                    seq = min(self.ks_product_image_ids.mapped('sequence'))
                    if each_rec.sequence == seq:
                        self.image_1920 = each_rec.ks_image
                        self.ks_file_type = each_rec.ks_file_name
                        each_rec.ks_src = True

    # This function is used to add product main image to the woocommerce gallery whenever the image is changed
    @api.onchange('image_1920')
    def _onchange_image_1920(self):
        if self.image_1920 and not self.env['ks.woo.product.image'].search(
                [('ks_image', '=', self.image_1920), ('ks_file_name', '=', self.ks_file_type),
                 ('ks_product_tmpl_id', '=', self.ids[0] if self.ids else 0)], limit=1):
            if not self.image_1920 in self.ks_product_image_ids.mapped('ks_image'):
                woo_image = self.env['ks.woo.product.image'].create({
                    'ks_product_tmpl_id': self.id,
                    'ks_image': self.image_1920,
                    'ks_file_name': self.ks_file_type if self.ks_file_type else None,
                    'sequence': -1,
                })
                ks_image_list = []
                ks_image_list.append(woo_image.id)
                for rec in self.ks_product_image_ids:
                    if rec.id not in ks_image_list and rec.ks_src == True:
                        ks_image_list.append(rec.id)
                        rec.ks_src = False
                self.ks_product_image_ids = ks_image_list
                self.ks_change_sequence(self.ks_product_image_ids)

    def ks_change_sequence(self, ks_pro_temp):
        if ks_pro_temp:
            for img in ks_pro_temp:
                seq = img.sequence + 1
                img.write({'sequence': seq})
        return True

    def ks_decrease_sequence(self, ks_pro_temp):
        if ks_pro_temp:
            for img in ks_pro_temp:
                seq = img.sequence - 1
                img.write({'sequence': seq})
        return True

    def ks_arrange_from_wizard(self, ks_images):
        seq = 0
        for img in ks_images:
            img.sequence = seq
            seq += 1
        return True

    # @api.onchange('image_1920')
    # def _onchange_image_1920(self):
    #     if self.image_1920:
    #         product_id = self if type(self.id) == int else self._origin
    #         if self.image_1920 and not product_id.ks_product_image_ids:
    #             woo_image = self.env['ks.woo.product.image'].create({
    #                 'ks_product_tmpl_id': product_id.id,
    #                 'ks_image': self.image_1920,
    #                 'ks_file_name': product_id.name,
    #                 'sequence': -1,
    #             })
    #             self.ks_product_image_ids = [(4, woo_image.id)]
    #         elif self.image_1920 and product_id.ks_product_image_ids:
    #             woo_image = self.env['ks.woo.product.image'].create({
    #                 'ks_product_tmpl_id': product_id.id,
    #                 'ks_image': self.image_1920,
    #                 'ks_file_name': product_id.name,
    #                 'sequence': -1,
    #             })
    #             self.ks_product_image_ids = [(4, woo_image.id)]

    @api.onchange('ks_to_be_export')
    def _onchange_ks_to_be_export(self):
        if self.ks_to_be_export:
            product_id = self if type(self.id) == int else self._origin
            if product_id.image_1920 and not product_id.ks_product_image_ids:
                woo_image = self.env['ks.woo.product.image'].create({
                    'ks_product_tmpl_id': product_id.id,
                    'ks_image': product_id.image_1920,
                    'ks_file_name': product_id.name
                })
                self.ks_product_image_ids = [(4, woo_image.id)]
            if self.attribute_line_ids:
                self.ks_woo_product_type = 'variable'
            else:
                self.ks_woo_product_type = 'simple'

    @api.model
    def create(self, values):
        res = super(KsProduct, self).create(values)
        # res._onchange_ks_to_be_export()
        if res.ks_exported_in_woo:
            res.ks_to_be_export = bool(res.ks_woo_id)
            if res.ks_woo_product_type != 'grouped':
                if res.ks_woo_variant_count > 0:
                    res.ks_woo_product_type = 'variable'
                else:
                    res.ks_woo_product_type = 'simple'
        return res

    def write(self, values):
        for rec in self:
            if values.get('ks_woo_id'):
                values.update({
                    'ks_to_be_export': bool(values.get('ks_woo_id'))
                })
            if rec.ks_woo_product_type != 'grouped':
                if rec.ks_woo_variant_count > 1:
                    values.update({
                        'ks_woo_product_type': 'variable'
                    })
                else:
                    values.update({
                        'ks_woo_product_type': 'simple'
                    })
            if rec.ks_woo_id:
                values.update({'ks_sync_date': datetime.datetime.now()})
        # if self.ks_exported_in_woo:
        #     if self.ks_woo_product_type != 'grouped':
        #         if self.ks_woo_variant_count > 1:
        #             values.update({
        #                 'ks_woo_product_type': 'variable'
        #             })
        #         else:
        #             values.update({
        #                 'ks_woo_product_type': 'simple'
        #             })

        # return super(KsProduct, self).write(values)
        res = super(KsProduct, self).write(values)
        # for rec in self:
        #     if values.get('ks_product_image_ids', False):
        #         ks_arrange_images = self.ks_arrange_from_wizard(rec.ks_product_image_ids)
        #         _logger.info(rec.ks_product_image_ids.mapped('sequence'))
        return res

    @api.depends('product_variant_ids', 'ks_to_be_export')
    def _ks_count_woo_variant(self):
        for each_rec in self:
            if each_rec.ks_to_be_export:
                if each_rec.product_variant_id.product_template_attribute_value_ids:
                    each_rec.ks_woo_variant_count = len(each_rec.product_variant_ids)

    @api.depends('ks_woo_variant_count')
    def _ks_compute_product_type(self):
        for each_rec in self:
            if each_rec.ks_woo_product_type != 'grouped':
                if each_rec.ks_woo_variant_count > 0:
                    each_rec.ks_woo_product_type = 'variable'
                else:
                    each_rec.ks_woo_product_type = 'simple'

    @api.depends('ks_woo_id')
    def _ks_compute_export_in_woo(self):
        """
        This will make enable the Exported in Woo if record has the WooCommerce Id

        :return: None
        """
        for rec in self:
            rec.ks_exported_in_woo = bool(rec.ks_woo_id)

    def ks_auto_import_product(self, cron_id=False):
        """
        This will sync the product from Woo to Odoo
        :param cron_id: current executing cron id
        :return:
        """
        if not cron_id:
            if self._context.get('params'):
                cron_id = self._context.get('params').get('id')
        instance_id = self.env['ks.woocommerce.instances'].search(
            [('ks_auto_import_product', '=', True), ('ks_aip_cron_id', '=', cron_id)], limit=1)
        if instance_id.ks_instance_state == 'active':
            try:
                wcapi = instance_id.ks_api_authentication()
                if wcapi.get("").status_code in [200, 201]:
                    self.ks_sync_product_woocommerce(wcapi, instance_id)
                    # instance_id.ks_aip_cron_last_updated = fields.datetime.now()
                    # this field is commented as it is now related with cron field lastcall
                else:
                    self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                                 ks_status='success' if wcapi.get("").status_code in [
                                                                     200,
                                                                     201] else 'failed',
                                                                 ks_type='system_status',
                                                                 ks_woo_instance_id=instance_id.id,
                                                                 ks_operation='odoo_to_woo',
                                                                 ks_operation_type='connection',
                                                                 response='Connection successful' if wcapi.get(
                                                                     "").status_code in [200, 201] else wcapi.get(
                                                                     "").text)
            except ConnectionError:
                self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id.id,
                                                                    type='product',
                                                                    operation='woo_to_odoo')
            except Exception as e:
                self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="product",
                                                             operation_type="import",
                                                             instance_id=instance_id.id,
                                                             operation="woo_to_odoo", exception=e)
        else:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_status='failed',
                                                         ks_type='product',
                                                         ks_woo_instance_id=instance_id.id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='create',
                                                         response='Auto Import Product Job: Did not Found the WooCommerce Instance' if not instance_id else
                                                         "Auto Import Product Job: WooCommerce instance is not in active state to perform this operation")

    def ks_auto_update_stock(self, cron_id=False):
        """
        This will update the stock level of product from odoo to Woo.
        :param cron_id:
        :return:
        """
        if not cron_id:
            if self._context.get('params'):
                cron_id = self._context.get('params').get('id')
        instance_id = self.env['ks.woocommerce.instances'].search(
            [('ks_aus_cron_id', '=', cron_id), ('ks_auto_update_stock', '=', True)], limit=1)
        if instance_id.ks_instance_state == 'active':
            try:
                wcapi = instance_id.ks_api_authentication()
                if wcapi.get("").status_code in [200, 201]:
                    self.ks_update_product_stock(instance_id, wcapi)
                    # instance_id.ks_aus_cron_last_updated = fields.datetime.now()
                else:
                    self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                                 ks_status='success' if wcapi.get("").status_code in [
                                                                     200,
                                                                     201] else 'failed',
                                                                 ks_type='system_status',
                                                                 ks_woo_instance_id=instance_id.id,
                                                                 ks_operation='odoo_to_woo',
                                                                 ks_operation_type='connection',
                                                                 response='Connection successful' if wcapi.get(
                                                                     "").status_code in [200, 201] else wcapi.get(
                                                                     "").text)
            except ConnectionError:
                self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id.id,
                                                                    type='stock',
                                                                    operation='odoo_to_woo')
            except Exception as e:
                self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="stock",
                                                             operation_type="export",
                                                             instance_id=instance_id.id,
                                                             operation="odoo_to_woo", exception=e)
        else:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_status='failed',
                                                         ks_type='stock',
                                                         ks_woo_instance_id=instance_id.id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='create',
                                                         response='Auto Update Product Stock Job: Did not Found the WooCommerce Instance' if not instance_id else
                                                         "Auto Update Product Stock Job: WooCommerce instance is not in active state to perform this operation")

    def ks_update_product_stock(self, instance_id, wcapi, ks_woo_id=False):
        non_variant_product = []
        if not ks_woo_id:
            product_records = self.env['product.template'].search(
                [('ks_woo_instance_id', '=', instance_id.id),
                 ('ks_woo_id', '!=', False)])
        if ks_woo_id:
            product_records = self.env['product.template'].search(
                [('ks_woo_instance_id', '=', instance_id.id), ('ks_woo_id', '=', ks_woo_id)])
        # ('ks_woo_id', '!=', False)])
        if wcapi.get("").status_code in [200, 201]:
            for each_product in product_records:
                variant_product = []
                if each_product.product_variant_count > 1:
                    for each_variant in each_product.product_variant_ids:
                        if each_variant.ks_woo_variant_id:
                            variant_product.append({
                                'id': each_variant.ks_woo_variant_id,
                                'manage_stock': True,
                                'stock_quantity': each_variant.qty_available if each_variant.ks_woo_instance_id.ks_stock_field_type.name == 'qty_available'
                                else each_variant.virtual_available,
                            })
                else:
                    if each_product.product_variant_id.ks_woo_variant_id:
                        variant_product.append({
                            'id': each_product.product_variant_id.ks_woo_variant_id,
                            'manage_stock': True,
                            'stock_quantity': each_product.qty_available if each_product.ks_woo_instance_id.ks_stock_field_type.name == 'qty_available'
                            else each_product.virtual_available,
                        })
                    else:
                        non_variant_product.append({
                            'id': each_product.ks_woo_id,
                            'manage_stock': True,
                            'stock_quantity': each_product.qty_available if each_product.ks_woo_instance_id.ks_stock_field_type.name == 'qty_available'
                            else each_product.virtual_available,
                        })
                if variant_product:
                    try:
                        woo_product_response = wcapi.post("products/%s/variations/batch" %
                                                          each_product.ks_woo_id,
                                                          {'update': variant_product})
                        self.ks_batch_update_response(wcapi, woo_product_response, instance_id, product_variant=True)
                    except ConnectionError:
                        self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                            type='stock',
                                                                            operation='odoo_to_woo')
                    except Exception as e:
                        self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="stock",
                                                                     operation_type="export",
                                                                     instance_id=instance_id,
                                                                     operation="odoo_to_woo", exception=e)
            try:
                woo_response = wcapi.post("products/batch", {'update': non_variant_product})
                self.ks_batch_update_response(wcapi, woo_response, instance_id)
            except ConnectionError:
                self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                    type='stock',
                                                                    operation='odoo_to_woo')
            except Exception as e:
                self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="stock",
                                                             operation_type="export",
                                                             instance_id=instance_id,
                                                             operation="odoo_to_woo", exception=e)
        else:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_type='system_status',
                                                         ks_status='success' if wcapi.get("").status_code in [
                                                             200, 201] else 'failed',
                                                         ks_woo_instance_id=instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='connection',
                                                         response=str(wcapi.get("").status_code) + ': ' + eval(
                                                             wcapi.get("").text).get('message'))

    @api.onchange('ks_length', 'ks_width', 'ks_height')
    def onchange_l_b_h(self):
        """
        This will calculate the value for Volume with respective of ks_length, ks_width and ks_height

        :return: None
        """
        self.volume = float(self.ks_length if self.ks_length else 0) * float(
            self.ks_width if self.ks_width else 0) * float(
            self.ks_height if self.ks_height else 0)

    def ks_update_product_status_in_woo(self):
        """
        This will publish and unpublish the products on WooCommerce in real time.
        :return:
        """
        for each_rec in self:
            if each_rec.ks_woo_instance_id.ks_instance_state == 'active':
                try:
                    wcapi = each_rec.ks_woo_instance_id.ks_api_authentication()
                    if wcapi.get("").status_code in [200, 201]:
                        woo_cancel_response = wcapi.put("products/%s" % each_rec.ks_woo_id,
                                                        {
                                                            "status": 'publish' if not each_rec.ks_woo_status else 'draft'})
                        if woo_cancel_response.status_code in [200, 201]:
                            each_rec.ks_woo_status = not each_rec.ks_woo_status
                            product_name = self.ks_get_product_name(each_rec)
                            message = 'Product [' + product_name + '] is Published in WooCommerce' if each_rec.ks_woo_status else 'Product [' + product_name + '] is Unpublished in WooCommerce'
                            status = 'Success'
                        else:
                            status = 'Error'
                            message = str(woo_cancel_response.status_code) + ': ' + eval(woo_cancel_response.text).get(
                                'message')
                        return self.env['ks.message.wizard'].ks_pop_up_message(names=status,
                                                                               message=message)
                    else:
                        self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                                     ks_status='success' if wcapi.get(
                                                                         "").status_code in [
                                                                                                200,
                                                                                                201] else 'failed',
                                                                     ks_type='system_status',
                                                                     ks_woo_instance_id=each_rec.ks_woo_instance_id,
                                                                     ks_operation='odoo_to_woo',
                                                                     ks_operation_type='connection',
                                                                     response='Connection successful' if wcapi.get(
                                                                         "").status_code in [200, 201] else wcapi.get(
                                                                         "").text)
                except ConnectionError:
                    self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=each_rec.ks_woo_instance_id,
                                                                        type='product',
                                                                        operation='odoo_to_woo',
                                                                        ks_woo_id=each_rec.ks_woo_id)
                except Exception as e:
                    self.env['ks.woo.sync.log'].ks_exception_log(record=each_rec, type="product",
                                                                 operation_type="update",
                                                                 instance_id=each_rec.ks_woo_instance_id,
                                                                 operation="odoo_to_woo", exception=e)
            else:
                self.env['ks.woo.sync.log'].ks_no_instance_log(each_rec, 'product')

    # This will return the product name
    def ks_get_product_name(self, record):
        return record.name

    # Action Function
    def ks_update_product_to_woo(self):
        """
        This will export and update the product on woocommerce.
        :return: Open a popup wizard with a summary message
        """

        ks_rec_failed_list = []
        for each_record in self:
            if each_record.ks_woo_instance_id and each_record.ks_woo_instance_id.ks_instance_state == 'active':
                try:
                    wcapi = each_record.ks_woo_instance_id.ks_api_authentication()
                    if wcapi.get("").status_code in [200, 201]:
                        json_data = self.ks_prepare_product_template_data_to_export_in_woo(
                            each_record, wcapi)
                        product_name = self.ks_get_product_name(each_record)
                        if each_record.ks_woo_id and not each_record.ks_update_false:
                            record_exist = wcapi.get("products/%s" % each_record.ks_woo_id)
                            if record_exist.status_code == 404:
                                woo_product_response = wcapi.post("products", json_data)
                                self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=each_record.ks_woo_id,
                                                                             ks_status='success' if woo_product_response.status_code in [
                                                                                 200, 201] else 'failed',
                                                                             ks_type='product',
                                                                             ks_woo_instance_id=each_record.ks_woo_instance_id,
                                                                             ks_operation='odoo_to_woo',
                                                                             ks_operation_type='create',
                                                                             response='Product [ ' + product_name + ' ] has been succesfully created' if woo_product_response.status_code in [
                                                                                 200,
                                                                                 201] else 'The create operation failed for Product [ ' + product_name + ' ] due to ' + eval(
                                                                                 woo_product_response.text).get(
                                                                                 'message'))
                                each_record.ks_update_product_details(
                                    woo_product_response, wcapi)

                            else:
                                woo_product_response = wcapi.put("products/%s" % each_record.ks_woo_id, json_data)
                                self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=each_record.ks_woo_id,
                                                                             ks_status='success' if woo_product_response.status_code in [
                                                                                 200, 201] else 'failed',
                                                                             ks_type='product',
                                                                             ks_woo_instance_id=each_record.ks_woo_instance_id,
                                                                             ks_operation='odoo_to_woo',
                                                                             ks_operation_type='update',
                                                                             response='Product [' + product_name + '] has been succesfully updated' if woo_product_response.status_code in [
                                                                                 200,
                                                                                 201] else 'The update operation failed for Product [' + product_name + '] due to ' + eval(
                                                                                 woo_product_response.text).get(
                                                                                 'message'))
                                each_record.ks_update_product_details(
                                    woo_product_response, wcapi)

                        else:
                            if not each_record.ks_update_false:
                                woo_product_response = wcapi.post("products", json_data)
                                self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=each_record.ks_woo_id,
                                                                             ks_status='success' if woo_product_response.status_code in [
                                                                                 200, 201] else 'failed',
                                                                             ks_type='product',
                                                                             ks_woo_instance_id=each_record.ks_woo_instance_id,
                                                                             ks_operation='odoo_to_woo',
                                                                             ks_operation_type='create',
                                                                             response='Product [' + product_name + '] has been succesfully created' if woo_product_response.status_code in [
                                                                                 200,
                                                                                 201] else 'The create operation failed for Product [' + product_name + '] due to ' + eval(
                                                                                 woo_product_response.text).get(
                                                                                 'message'))
                                each_record.ks_update_product_details(
                                    woo_product_response, wcapi)
                    else:
                        self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                                     ks_status='success' if wcapi.get(
                                                                         "").status_code in [
                                                                                                200,
                                                                                                201] else 'failed',
                                                                     ks_type='system_status',
                                                                     ks_woo_instance_id=each_record.ks_woo_instance_id,
                                                                     ks_operation='odoo_to_woo',
                                                                     ks_operation_type='connection',
                                                                     response='Connection successful' if wcapi.get(
                                                                         "").status_code in [200, 201] else wcapi.get(
                                                                         "").text)
                except ConnectionError:
                    self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=each_record.ks_woo_instance_id,
                                                                        type='product',
                                                                        operation='odoo_to_woo',
                                                                        ks_woo_id=each_record.ks_woo_id)
                except Exception as e:
                    if each_record.id not in ks_rec_failed_list:
                        ks_rec_failed_list.append(each_record)
                    self.env['ks.woo.sync.log'].ks_exception_log(record=each_record, type="product",
                                                                 operation_type="create" if each_record.ks_woo_id else "update",
                                                                 instance_id=each_record.ks_woo_instance_id,
                                                                 operation="odoo_to_woo", exception=e)
                each_record.ks_sync_date = datetime.datetime.now()
                each_record.ks_last_exported_date = each_record.ks_sync_date
                each_record.sync_update()

            else:
                self.env['ks.woo.sync.log'].sudo().ks_no_instance_log(each_record, 'product')
                return 'error'
        return ks_rec_failed_list

    def ks_update_product_to_woo_wizard(self):
        ks_failed_instance_list = []
        ks_failed_product_id = []
        for rec in self:
            ks_failed_list = rec.ks_update_product_to_woo()
            if ks_failed_list == 'error':
                format_info = 'The instance must be in active state or instance field should be updated to perform the operations'
                format_string = ks_message_string = ''
                log = 'Export Status'
            else:
                for record in ks_failed_list:
                    ks_failed_product_id.append(record.name)
                    ks_failed_instance_list.append(record['ks_woo_instance_id'].display_name)
                log = 'Export Status'
                format_string = ks_message_string = ''
                if len(ks_failed_product_id) != 0:
                    ks_message_string = '\n\nList of Failed Records:\n'
                    format_string = 'Name:\t' + str(ks_failed_product_id) + '\n' + 'Instance:\t' + str(
                        ks_failed_instance_list)
                format_info = 'Export Operation has been performed, Please refer logs for further details.'
        return self.env['ks.message.wizard'].ks_pop_up_message(names=log,
                                                               message=format_info + ks_message_string + format_string)

    def ks_update_product_details(self, woo_product_response, wcapi):
        if woo_product_response.status_code in [200, 201]:
            woo_product_data = woo_product_response.json()
            self.env['ks.woocommerce.instances'].ks_store_record_after_export(self, woo_product_data)
            self.ks_manage_image_in_odoo(woo_product_data)
            self.ks_manage_variants_for_odoo_products(wcapi)

    def ks_prepare_product_template_data_to_export_in_woo(self, product_record, wcapi):
        """
        This will prepare the json data to export in WooCommerce.

        :param product_record: product.template record
        :param wcapi: The WooCommerce API instance
        :return: Dict
        """
        data = {
            'name': product_record.name,
            'type': product_record.ks_woo_product_type,
            'status': 'publish' if product_record.ks_woo_status else 'draft',
            'description': product_record.ks_woo_description if product_record.ks_woo_description else '',
            'short_description': product_record.ks_woo_short_description if product_record.ks_woo_short_description else '',
            'sku': product_record.default_code if product_record.default_code else '',
            'weight': str(product_record.weight),
            'dimensions': {
                'length': str(product_record.ks_length),
                'width': str(product_record.ks_width),
                'height': str(product_record.ks_height)
            },
            'categories': self.ks_categories_json_data(product_record.ks_woo_categories, wcapi),
            'tags': self.ks_tags_json_data(product_record.ks_woo_tag, wcapi, product_record.ks_woo_instance_id),
            'attributes': self.ks_attribute_json_data(product_record),
        }
        if product_record.ks_product_image_ids:
            data.update({
                'images': self.ks_images_woo_data(product_record, product_record.ks_product_image_ids)
            })
            # else:
            #     data.update({
            #         'images': []
            #     })
        if product_record.ks_woo_product_type == 'simple':
            data.update({
                'stock_quantity': product_record.qty_available if product_record.ks_woo_instance_id.ks_stock_field_type.name == 'qty_available' else product_record.virtual_available,
                'manage_stock': True,
            })
        if product_record.ks_woo_id == 0:
            data.update({
                'regular_price': str(
                    product_record.ks_woo_regular_price) if product_record.ks_woo_regular_price else '',
                'sale_price': str(product_record.ks_woo_sale_price) if product_record.ks_woo_sale_price else ''
            })
        else:
            if product_record.ks_woo_product_type == 'simple':
                data.update({
                    'regular_price': str(
                        product_record.ks_woo_regular_price) if product_record.ks_woo_regular_price else '',
                    'sale_price': str(product_record.ks_woo_sale_price) if product_record.ks_woo_sale_price else ''
                })
        return data

    def ks_images_woo_data(self, product_record, image_records):
        """

        :param product_record: Product template record
        :param image_records: Gallery Images record
        :return: Dict of Image data
        """
        if product_record.ks_to_be_export or product_record.ks_woo_id:
            image_data = []
            for each_img in image_records:
                if each_img.ks_woo_id:
                    image_data.append({
                        'id': each_img.ks_woo_id
                    })
                else:
                    image_data.append({
                        'src': each_img.ks_woo_image_url(product_record.id, each_img.id, each_img.ks_file_name)
                    })
            return image_data

    def ks_variant_images_woo_data(self, product_record, image_records):
        """

        :param product_record: Product template record
        :param image_records: Gallery Images record
        :return: Dict of Image data
        """
        if product_record.ks_to_be_export or product_record.ks_woo_id:
            image_data = []
            for each_img in image_records:
                if each_img.ks_woo_id:
                    image_data.append({
                        'id': each_img.ks_woo_id
                    })
                else:
                    image_data.append({
                        'src': each_img.ks_variant_woo_image_url(product_record.id, each_img.id, each_img.ks_file_name)
                    })
            return image_data

    def ks_manage_image_in_odoo(self, json_data):
        for each_rec in self:
            if each_rec:
                each_rec.ks_product_image_ids.search([('ks_woo_id', '=', 0),
                                                      ('ks_woo_instance_id', '=', each_rec.ks_woo_instance_id.id),
                                                      ('ks_product_tmpl_id', '=', each_rec.id)]).unlink()
                data = each_rec.find_product_template_image(json_data.get('images') or '', self.ks_woo_instance_id,
                                                            each_rec)
                each_rec.image_1920 = each_rec.ks_product_image_ids[
                    0].ks_image if each_rec.ks_product_image_ids else False

    def ks_manage_variants_for_odoo_products(self, wcapi):
        """
        This will update the product variants
        :param wcapi: The WooCommerce API instance
        :return: None
        """
        try:
            if self.product_variant_count >= 1 and self.product_variant_id.product_template_attribute_value_ids:
                for each_variant in self.product_variant_ids:
                    # Todo
                    variant_json_data = self.ks_prepare_product_variant_data_to_export_in_woo(
                        each_variant)
                    if each_variant.ks_woo_variant_id:
                        record_exist = wcapi.get("products/%s/variations/%s" % (self.ks_woo_id,
                                                                                each_variant.ks_woo_variant_id))
                        if record_exist.status_code == 404:
                            woo_variant_response = wcapi.post("products/%s/variations" % self.ks_woo_id,
                                                              variant_json_data)
                            self.ks_update_product_variant_details(woo_variant_response, each_variant)
                            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=each_variant.ks_woo_variant_id,
                                                                         ks_status='success' if woo_variant_response.status_code in [
                                                                             200, 201] else 'failed',
                                                                         ks_type='product_variant',
                                                                         ks_woo_instance_id=each_variant.ks_woo_instance_id,
                                                                         ks_operation='odoo_to_woo',
                                                                         ks_operation_type='create',
                                                                         response='Product Variant[ ' + each_variant.display_name + ' ] has been succesfully created' if woo_variant_response.status_code in [
                                                                             200,
                                                                             201] else 'The create operation failed for Product Variant[ ' + each_variant.display_name + ' ] due to ' + eval(
                                                                             woo_variant_response.text).get('message'))
                        else:
                            woo_variant_response = wcapi.put("products/%s/variations/%s" % (self.ks_woo_id,
                                                                                            each_variant.ks_woo_variant_id),
                                                             variant_json_data)
                            self.ks_update_product_variant_details(woo_variant_response, each_variant)
                            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=each_variant.ks_woo_variant_id,
                                                                         ks_status='success' if woo_variant_response.status_code in [
                                                                             200, 201] else 'failed',
                                                                         ks_type='product_variant',
                                                                         ks_woo_instance_id=each_variant.ks_woo_instance_id,
                                                                         ks_operation='odoo_to_woo',
                                                                         ks_operation_type='update',
                                                                         response='Product Variant[ ' + each_variant.display_name + ' ] has been succesfully update' if woo_variant_response.status_code in [
                                                                             200,
                                                                             201] else 'The update operation failed for Product Variant[ ' + each_variant.display_name + ' ] due to ' + eval(
                                                                             woo_variant_response.text).get('message'))

                    else:
                        woo_variant_response = wcapi.post("products/%s/variations" % self.ks_woo_id, variant_json_data)
                        self.ks_update_product_variant_details(woo_variant_response, each_variant)
                        self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=each_variant.ks_woo_variant_id,
                                                                     ks_status='success' if woo_variant_response.status_code in [
                                                                         200, 201] else 'failed',
                                                                     ks_type='product_variant',
                                                                     ks_woo_instance_id=each_variant.ks_woo_instance_id,
                                                                     ks_operation='odoo_to_woo',
                                                                     ks_operation_type='create',
                                                                     response='Product Variant[ ' + each_variant.display_name + ' ] has been succesfully created' if woo_variant_response.status_code in [
                                                                         200,
                                                                         201] else 'The create operation failed for Product Variant[ ' + each_variant.display_name + ' ] due to ' + eval(
                                                                         woo_variant_response.text).get('message'))
            else:
                if self.product_variant_id.product_template_attribute_value_ids:
                    # Todo
                    variant_json_data = self.ks_prepare_product_variant_data_to_export_in_woo(
                        self.product_variant_id)
                    if self.product_variant_id.ks_woo_id:
                        record_exist = wcapi.get("products/%s" % self.product_variant_id.ks_woo_id)
                        if record_exist.status_code == 404:
                            woo_variant_response = wcapi.post("products/%s/variations" % self.ks_woo_id,
                                                              variant_json_data)
                            self.ks_update_product_variant_details(woo_variant_response, self.product_variant_id)
                            self.env['ks.woo.sync.log'].create_log_param(
                                ks_woo_id=self.product_variant_id.ks_woo_variant_id,
                                ks_status='success' if woo_variant_response.status_code in [
                                    200, 201] else 'failed',
                                ks_type='product_variant',
                                ks_woo_instance_id=self.product_variant_id.ks_woo_instance_id,
                                ks_operation='odoo_to_woo',
                                ks_operation_type='create',
                                response='Product Variant[ ' + self.product_variant_id.display_name + ' ] has been succesfully created' if woo_variant_response.status_code in [
                                    200,
                                    201] else 'The create operation failed for Product Variant[ ' + self.product_variant_id.display_name + ' ] due to ' + eval(
                                    woo_variant_response.text).get('message'))

                        else:
                            woo_variant_response = wcapi.put("products/%s/variations/%s" % (self.ks_woo_id,
                                                                                            self.product_variant_id.ks_woo_id),
                                                             variant_json_data)
                            self.ks_update_product_variant_details(woo_variant_response, self.product_variant_id)
                            self.env['ks.woo.sync.log'].create_log_param(
                                ks_woo_id=self.product_variant_id.ks_woo_variant_id,
                                ks_status='success' if woo_variant_response.status_code in [
                                    200, 201] else 'failed',
                                ks_type='product_variant',
                                ks_woo_instance_id=self.product_variant_id.ks_woo_instance_id,
                                ks_operation='odoo_to_woo',
                                ks_operation_type='update',
                                response='Product Variant[ ' + self.product_variant_id.display_name + ' ] has been succesfully update' if woo_variant_response.status_code in [
                                    200,
                                    201] else 'The update operation failed for Product Variant[ ' + self.product_variant_id.display_name + ' ] due to ' + eval(
                                    woo_variant_response.text).get('message'))

                    else:
                        woo_variant_response = wcapi.post("products/%s/variations" % self.ks_woo_id, variant_json_data)
                        self.ks_update_product_variant_details(woo_variant_response, self.product_variant_id)
                        self.env['ks.woo.sync.log'].create_log_param(
                            ks_woo_id=self.product_variant_id.ks_woo_variant_id,
                            ks_status='success' if woo_variant_response.status_code in [
                                200, 201] else 'failed',
                            ks_type='product_variant',
                            ks_woo_instance_id=self.product_variant_id.ks_woo_instance_id,
                            ks_operation='odoo_to_woo',
                            ks_operation_type='create',
                            response='Product Variant[ ' + self.product_variant_id.display_name + ' ] has been succesfully created' if woo_variant_response.status_code in [
                                200,
                                201] else 'The create operation failed for Product Variant[ ' + self.product_variant_id.display_name + ' ] due to ' + eval(
                                woo_variant_response.text).get('message'))
        except ConnectionError:
            self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=self.ks_woo_instance_id,
                                                                type='product_variant',
                                                                operation='odoo_to_woo')
        except Exception as e:
            self.env['ks.woo.sync.log'].ks_exception_log(record=self, type="product_variant",
                                                         operation_type="export", instance_id=self.ks_woo_instance_id,
                                                         operation="odoo_to_woo", exception=e)

    def ks_update_product_variant_details(self, woo_variant_response, each_variant):
        if woo_variant_response.status_code in [200, 201]:
            woo_variant_record = woo_variant_response.json()
            each_variant.ks_woo_variant_id = woo_variant_record.get('id')
            # each_variant.ks_update_price_on_product_variant(woo_variant_record)
            each_variant.ks_date_variant_created = datetime.datetime.strptime(
                (woo_variant_record.get('date_created') or False).replace('T',
                                                                          ' '),
                DEFAULT_SERVER_DATETIME_FORMAT)
            each_variant.ks_date_variant_updated = datetime.datetime.strptime(
                (woo_variant_record.get('date_modified') or False).replace('T',
                                                                           ' '),
                DEFAULT_SERVER_DATETIME_FORMAT)

    def ks_prepare_product_variant_data_to_export_in_woo(self, product_record):
        """

        :param product_record: product.product record
        :return: Dict
        """
        data = {
            "sku": product_record.default_code if product_record.default_code else "",
            "weight": str(product_record.weight),
            "dimensions": {
                "length": str(product_record.ks_length),
                "width": str(product_record.ks_width),
                "height": str(product_record.ks_height)
            },
            "stock_quantity": product_record.qty_available,
            'manage_stock': True,
            "description": product_record.ks_woo_variant_description if product_record.ks_woo_variant_description else ''
        }
        if product_record.ks_variant_profile_image:
            # Todo
            image_data = []
            image_data = self.ks_variant_images_woo_data(product_record, product_record.ks_product_image_id)
            if len(image_data) > 0:
                data.update({
                    'image': image_data[0],
                })
        else:
            data.update({
                'image': None,
            })
        attribute = []
        for each_value in product_record.product_template_attribute_value_ids:
            attribute.append({
                "id": 0 if each_value.attribute_id.ks_woo_id == -1 else each_value.attribute_id.ks_woo_id,
                "name": each_value.attribute_id.name,
                "option": each_value.name
            })
        data.update({"attributes": attribute})
        data.update({
            'regular_price': str(
                product_record.ks_woo_variant_reg_price) if product_record.ks_woo_variant_reg_price else '',
            'sale_price': str(
                product_record.ks_woo_variant_sale_price) if product_record.ks_woo_variant_sale_price else ''
        })
        return data

    def ks_attribute_json_data(self, product_record):
        """

        :param product_record: product.template record
        :return: Dict
        """
        data = []
        if product_record.attribute_line_ids:
            for each_attr_line in product_record.attribute_line_ids:
                manage_attribute = self.ks_manage_attribute_for_variants(each_attr_line)
                if manage_attribute:
                    data.append({
                        "id": 0 if each_attr_line.attribute_id.ks_woo_id == -1 else each_attr_line.attribute_id.ks_woo_id,
                        "name": each_attr_line.attribute_id.name,
                        "position": 1,
                        "visible": True,
                        "variation": True,
                        "options": each_attr_line.value_ids.mapped('name')
                    })
        if product_record.ks_woo_visible_attributes:
            data.append(product_record.ks_woo_visible_attributes)
        return data

    def ks_manage_attribute_for_variants(self, each_attr_line):
        """
        :param each_attr_line: Attribute line record of a product
        :return: True
        """
        if not each_attr_line.attribute_id.ks_woo_id:
            each_attr_line.attribute_id.ks_update_product_attribute_to_woo()
        return True

    # @api.model
    # def ks_image_import_permission_wizard(self):
    #     ks_product_template_ids = self._context.get('active_ids')
    #     ks_which_operation = False
    #     return {
    #         'name': _('Image Permission Wizard'),
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'ks.image.permission.wizard',
    #         'views': [(self.env.ref('ks_woocommerce.ks_image_permission_wizard_view').id, 'form')],
    #         'view_id': self.env.ref('ks_woocommerce.ks_image_permission_wizard_view').id,
    #         'target': 'new',
    #         'context': {'default_ks_product_template': ks_product_template_ids,
    #                     'default_ks_export_operation': ks_which_operation},
    #     }

    # @api.model
    # def ks_image_export_permission_wizard(self):
    #     ks_product_template_ids = self._context.get('active_ids')
    #     # templates =[]
    #     # for temp_id in ks_product_template_ids:
    #     #     templates.append(self.env['product.template'].brwose(temp_id))
    #     ks_which_operation = True
    #     return {
    #         'name': _('Image Permission Wizard'),
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'ks.image.permission.wizard',
    #         'views': [(self.env.ref('ks_woocommerce.ks_image_permission_wizard_view').id, 'form')],
    #         'view_id': self.env.ref('ks_woocommerce.ks_image_permission_wizard_view').id,
    #         'target': 'new',
    #         'context': {'default_ks_product_template': ks_product_template_ids,
    #                     'default_ks_export_operation': ks_which_operation},
    #     }

    @api.model
    def ks_update_product_to_odoo(self):
        """
        This will get the woocommerce product data and create or update the selected product on odoo

        :param wcapi: The WooCommerce API instance
        :param instance_id: The WooCommerce instance
        :return: None
        """
        ks_rec_failed_list = []
        for rec in self:
            instance_id = self.env['ks.woocommerce.instances'].search([('id', '=', rec.ks_woo_instance_id.id)], limit=1)
            if instance_id.ks_instance_state == 'active':
                try:
                    wcapi = rec.ks_woo_instance_id.ks_api_authentication()
                    if wcapi.get("").status_code in [200, 201]:
                        woo_product_response = wcapi.get("products/%s" % rec.ks_woo_id)
                        if woo_product_response.status_code in [200, 201]:
                            if woo_product_response.json().get('type') in ['simple', 'grouped', 'variable']:
                                rec.ks_mangae_woo_product(woo_product_response.json(), wcapi, instance_id)
                        else:
                            if rec.id not in ks_rec_failed_list:
                                ks_rec_failed_list.append(rec)
                            self.env['ks.woo.sync.log'].create_log_param(
                                ks_woo_id=False,
                                ks_status='failed',
                                ks_type='product',
                                ks_woo_instance_id=instance_id,
                                ks_operation='woo_to_odoo',
                                ks_operation_type='fetch',
                                response=str(woo_product_response.status_code) + eval(woo_product_response.text).get(
                                    'message'),
                            )
                except ConnectionError:
                    self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                        type='product',
                                                                        operation='woo_to_odoo')
                except Exception as e:
                    if rec.id not in ks_rec_failed_list:
                        ks_rec_failed_list.append(rec)
                    self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="product",
                                                                 operation_type="import",
                                                                 instance_id=instance_id,
                                                                 operation="woo_to_odoo", exception=e)
            else:
                return 'error'
        return ks_rec_failed_list

    def ks_update_product_to_odoo_wizard(self):
        ks_failed_instance_list = []
        ks_failed_product_id = []
        for rec in self:
            ks_failed_list = rec.ks_update_product_to_odoo()
            if ks_failed_list == 'error':
                format_info = 'The instance must be in active state or instance field should be updated to perform the operations'
                format_string = ks_message_string = ''
                log = 'Import Status'
            else:
                for record in ks_failed_list:
                    ks_failed_product_id.append(record.name)
                    ks_failed_instance_list.append(record['ks_woo_instance_id'].display_name)
                log = 'Import Status'
                format_string = ks_message_string = ''
                if len(ks_failed_product_id) != 0:
                    ks_message_string = '\n\nList of Failed Records:\n'
                    format_string = 'Name:\t' + str(ks_failed_product_id) + '\n' + 'Instance:\t' + str(
                        ks_failed_instance_list)
                format_info = 'Import Operation has been performed, Please refer logs for further details.'
        return self.env['ks.message.wizard'].ks_pop_up_message(names=log,
                                                               message=format_info + ks_message_string + format_string)

    def ks_sync_product_woocommerce(self, wcapi, instance_id):
        """
        This will get the woocommerce product data and create or update the products on odoo

        :param wcapi: The WooCommerce API instance
        :param instance_id: The WooCommerce instance
        :return: None
        """
        multi_api_call = True
        per_page = 100
        page = 1
        try:
            while (multi_api_call):
                woo_product_response = wcapi.get("products", params={"per_page": per_page, "page": page})
                if woo_product_response.status_code in [200, 201]:
                    woo_products_record = woo_product_response.json()
                    for each_record in woo_products_record:
                        if each_record.get('type') in ['simple', 'grouped', 'variable']:
                            self.ks_mangae_woo_product(each_record, wcapi, instance_id)
                else:
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='failed',
                        ks_type='product',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='fetch',
                        response=str(woo_product_response.status_code) + eval(woo_product_response.text).get('message'),
                    )

                total_api_calls = woo_product_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                else:
                    multi_api_call = False
        except ConnectionError:
            self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                type='product',
                                                                operation='woo_to_odoo')
        except Exception as e:
            self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="product",
                                                         operation_type="import",
                                                         instance_id=instance_id,
                                                         operation="woo_to_odoo", exception=e)

    def ks_mangae_woo_product(self, each_record, wcapi, instance_id):
        product_template_exist = self.search([('ks_woo_id', '=', each_record.get('id')),
                                              ('ks_woo_instance_id', '=', instance_id.id)], limit=1)
        #     modified_date = datetime.strptime(each_record.get('date_modified'), '%Y-%m-%dT%H:%M:%S')
        #     if not product_template_exist.ks_date_updated == modified_date:
        #         self.ks_create_update_woo_product(each_record, product_template_exist, wcapi, instance_id)
        #
        # def ks_create_update_woo_product(self, each_record, product_template_exist, wcapi, instance_id):
        """
        This will create the woo product
        :param each_record: json data
        :param wcapi: The WooCommerce API instance
        :param instance_id: The WooCommerce instance
        :return: None datetime.strptime(each_record.get('date_modified'), '%Y-%m-%dT%H:%M:%S')
        """
        product_template_data = self.prepare_product_template_data(each_record, instance_id, wcapi,
                                                                   product_template_exist, )
        if product_template_exist:
            product_template_exist.write(product_template_data)
            # product_template_exist = self.create(product_template_data)
            ks_operation_type = 'update'
        else:
            product_template_exist = self.create(product_template_data)
            ks_operation_type = 'create'
        product_name = self.ks_get_product_name(product_template_exist)
        # if product_template_exist.ks_woo_product_type == 'variable' and product_template_exist.product_variant_count == 1:
        #     product_template_exist.ks_woo_product_type = 'simple'
        if product_template_exist.ks_woo_product_type == 'simple':
            # ks_write_product_image = self.ks_write_image_1920(product_template_exist)
            product_variant = product_template_exist.product_variant_id
            ks_pricelists = instance_id.ks_woo_pricelist_ids
            if not ks_pricelists:
                ks_pricelists = []
                ks_pricelists.append(instance_id.ks_woo_pricelist)
                ks_pricelists.append(instance_id.ks_woo_sale_pricelist)
            else:
                data = ks_pricelists
                ks_pricelists = []
                for rec in data:
                    ks_pricelists.append(rec)
                if instance_id.ks_woo_sale_pricelist not in ks_pricelists:
                    ks_pricelists.append(instance_id.ks_woo_sale_pricelist)
            for price_list in ks_pricelists:
                product_template_exist.ks_update_price_on_price_list(each_record, price_list, product_variant,
                                                                     instance_id)
        # if product_template_exist.ks_woo_product_type == 'simple':
        #     product_template_exist.ks_update_price_on_price_list(each_record, instance_id.ks_woo_pricelist,
        #                                                          product_template_exist.product_variant_id)
        product_template_exist.ks_update_price_on_product(each_record)
        self.env['ks.woo.sync.log'].create_log_param(
            ks_woo_id=each_record.get('id'),
            ks_status='success',
            ks_type='product',
            ks_woo_instance_id=instance_id,
            ks_operation='woo_to_odoo',
            ks_operation_type=ks_operation_type,
            response='Product [' + product_name + '] has been succesfully created' if ks_operation_type == 'create' else 'Product [' + product_name + '] has been succesfully updated',
        )
        data = self.find_product_template_image(each_record.get('images') or '', instance_id, product_template_exist)
        if product_template_exist.ks_product_image_ids:
            product_template_exist.image_1920 = self.env['ks.woo.product.image'].browse(data[0]).ks_image
        if each_record.get('type') == 'variable':
            product_template_exist.ks_manage_variants_for_products(each_record, wcapi, instance_id)
            # ks_write_product_image = self.ks_write_image_1920(product_template_exist)
            # ks_image_per_ = self._context.get('ks_image_permission', True)
            # product_template_exist.with_context(
            #     {"ks_image_permission": ks_image_per_}).ks_manage_variants_for_products(each_record, wcapi,
            #                                                                                 instance_id)
        elif product_template_exist.attribute_line_ids:
            product_template_exist.attribute_line_ids.unlink()
            product_template_exist.write({'attribute_line_ids': [(6, 0, [])]})
        product_template_exist.ks_sync_date = datetime.datetime.now()
        product_template_exist.ks_last_exported_date = product_template_exist.ks_sync_date
        product_template_exist.sync_update()

    def ks_manage_variants_for_products(self, json_data, wcapi, instance_id):
        """

        :param json_data: json data
        :param wcapi: The WooCommerce API instance
        :param instance_id: The WooCommerce instance
        :return:
        """
        variant_ids = json_data.get('variations')
        if variant_ids:
            variation_attribute = self.ks_update_attribute_for_variation(json_data.get('attributes'), wcapi,
                                                                         instance_id, self)
            self.ks_update_product_attribute_line(variation_attribute, instance_id)
            # self.product_variant_ids.search([('product_tmpl_id', '=', self.id), '|', ('active', '=', False),
            #                                  ('active', '=', True)])
            for each_var_id in variant_ids:
                try:
                    woo_variant_response = wcapi.get("products/%s/variations/%s" % (json_data.get('id'), each_var_id))
                    if woo_variant_response.status_code in [200, 201]:
                        woo_variant_record = woo_variant_response.json()
                        ks_image_per_ = self._context.get('ks_images_permission', True)
                        if not ks_image_per_:
                            woo_variant_record['image'] = []
                        value_ids = []
                        for each_attribute in woo_variant_record.get('attributes'):
                            if each_attribute.get('id') == 0:
                                attribute_id = self.env['product.attribute'].search(
                                    [('name', '=', each_attribute.get('name')),
                                     ('ks_woo_id', '=', -1),
                                     ('ks_slug', '=', 'product_' + str(self.ks_woo_id)),
                                     ('ks_woo_instance_id', '=', instance_id.id)], limit=1)
                                if attribute_id:
                                    attr_value = attribute_id.value_ids.search(
                                        [('name', '=', each_attribute.get('option')),
                                         ('ks_woo_id', '=', -1),
                                         ('attribute_id', '=', attribute_id.id)]
                                        , limit=1)
                                    if attr_value:
                                        value_ids.append(attr_value.id)
                            else:
                                attribute_id = self.env['product.attribute'].search(
                                    [('ks_woo_id', '=', each_attribute.get('id')),
                                     ('ks_woo_instance_id', '=', instance_id.id)], limit=1)
                                if attribute_id:
                                    attr_value = attribute_id.value_ids.search(
                                        [('name', '=', each_attribute.get('option')),
                                         ('attribute_id', '=', attribute_id.id)], limit=1)
                                    if attr_value:
                                        value_ids.append(attr_value.id)
                        count = 0
                        if value_ids:
                            product_template_attribute_value_ids = self.env['product.template.attribute.value'].search(
                                [('product_tmpl_id', '=', self.id),
                                 ('product_attribute_value_id', 'in', value_ids)]).ids
                            # odoo_product_variant = self.product_variant_ids.search(
                            #     [('active', '=', True),
                            #      ('product_template_attribute_value_ids', 'in', product_template_attribute_value_ids),
                            #      ('ks_woo_instance_id', '=', instance_id.id)], limit=1)
                            for i in range(len(variant_ids)):
                                values = False
                                if i < len(self.product_variant_ids):
                                    variant_value = self.product_variant_ids[i].combination_indices.split(',')
                                    variant_value_list = []
                                    for j in range(len(variant_value)):
                                        variant_value_list.append(int(variant_value[j]))
                                    value1 = sorted(variant_value_list)
                                    value2 = sorted(product_template_attribute_value_ids)
                                    if value1 == value2:
                                        values = True
                                    if values:
                                        if product_template_attribute_value_ids and values:
                                            self.product_variant_ids[i].write(
                                                self.env['product.product'].ks_prepare_product_variant_data(
                                                    woo_variant_record))
                                            ks_pricelists = instance_id.ks_woo_pricelist_ids
                                            if not ks_pricelists:
                                                ks_pricelists = []
                                                ks_pricelists.append(instance_id.ks_woo_pricelist)
                                                ks_pricelists.append(instance_id.ks_woo_sale_pricelist)
                                            else:
                                                data = ks_pricelists
                                                ks_pricelists = []
                                                for rec in data:
                                                    ks_pricelists.append(rec)
                                                if instance_id.ks_woo_sale_pricelist not in ks_pricelists:
                                                    ks_pricelists.append(instance_id.ks_woo_sale_pricelist)

                                            for ks_pricelist in ks_pricelists:
                                                self.ks_update_price_on_price_list(woo_variant_record, ks_pricelist,
                                                                                   self.product_variant_ids[i], instance_id)

                                            self.product_variant_ids[i].ks_update_price_on_product_variant(
                                                woo_variant_record)
                                            self.env['ks.woo.sync.log'].create_log_param(
                                                ks_woo_id=woo_variant_record.get('id'),
                                                ks_status='success',
                                                ks_type='product_variant',
                                                ks_woo_instance_id=instance_id,
                                                ks_operation='woo_to_odoo',
                                                ks_operation_type='update',
                                                response='Product Variant [' + self.product_variant_ids[
                                                    i].display_name + '] has been succesfully updated',
                                            )
                                            count = count + 1
                            if count == 0:
                                varint_record = self.env['product.product'].ks_prepare_product_variant_data(
                                    woo_variant_record)
                                varint_record.update({
                                    'product_template_attribute_value_ids': [(6, 0, value_ids)],
                                    'ks_woo_instance_id': instance_id.id,
                                    'product_tmpl_id': self.id
                                })

                                # variant_value_list.sort()
                                # product_template_attribute_value_ids.sort()

                                # if variant_value_list.sort() == product_template_attribute_value_ids.sort():
                                #     values = True
                                # if len(product_template_attribute_value_ids) == len(variant_value):
                                #     for i in range(len(variant_value)):
                                #         if product_template_attribute_value_ids[i] == int(variant_value[i]):
                                #             values = True
                                #         else:
                                #             values = False
                                # else:
                                #     values = False
                                # if product_template_attribute_value_ids and values:
                                #     self.product_variant_ids[i].write(
                                #         self.env['product.product'].ks_prepare_product_variant_data(woo_variant_record))
                                #     ks_pricelists = instance_id.ks_woo_pricelist_ids
                                #     if not ks_pricelists:
                                #         ks_pricelists = []
                                #         ks_pricelists.append(instance_id.ks_woo_pricelist)
                                #         ks_pricelists.append(instance_id.ks_woo_sale_pricelist)
                                #     else:
                                #         data = ks_pricelists
                                #         ks_pricelists = []
                                #         for rec in data:
                                #             ks_pricelists.append(rec)
                                #         if instance_id.ks_woo_sale_pricelist not in ks_pricelists:
                                #             ks_pricelists.append(instance_id.ks_woo_sale_pricelist)
                                # if not ks_pricelists:
                                #     ks_pricelists = instance_id.ks_woo_pricelist
                                # for ks_pricelist in ks_pricelists:
                                #     self.ks_update_price_on_price_list(woo_variant_record, ks_pricelist,
                                #                                        self.product_variant_ids[i], instance_id)

                                # self.ks_update_price_on_price_list(woo_variant_record,
                                #                                    instance_id.ks_woo_pricelist,
                                #                                    odoo_product_variant)
                                # odoo_product_variant.ks_update_price_on_product_variant(woo_variant_record)
                                # self.env['ks.woo.sync.log'].create_log_param(
                                #     ks_woo_id=woo_variant_record.get('id'),
                                #     ks_status='success',
                                #     ks_type='product_variant',
                                #     ks_woo_instance_id=instance_id,
                                #     ks_operation='woo_to_odoo',
                                #     ks_operation_type='update',
                                #     response='Product Variant [' + odoo_product_variant.display_name + '] has been succesfully updated',
                                # )

                                # self.product_variant_ids[i].ks_update_price_on_product_variant(
                                #     woo_variant_record)
                                # self.env['ks.woo.sync.log'].create_log_param(
                                #     ks_woo_id=woo_variant_record.get('id'),
                                #     ks_status='success',
                                #     ks_type='product_variant',
                                #     ks_woo_instance_id=instance_id,
                                #     ks_operation='woo_to_odoo',
                                #     ks_operation_type='update',
                                #     response='Product Variant [' + self.product_variant_ids[
                                #         i].display_name + '] has been succesfully updated',
                                # )
                                # count = count + 1
                except ConnectionError:
                    self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                        type='product_variant',
                                                                        operation='woo_to_odoo',
                                                                        ks_woo_id=each_var_id)
                except Exception as e:
                    self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="product_variant",
                                                                 operation_type="import",
                                                                 instance_id=instance_id,
                                                                 operation="woo_to_odoo", exception=e)

    def ks_update_product_attribute_line(self, variation_attribute, instance_id):
        """
        This will update the attribute_line_ids in product template.
        :param variation_attribute:
        :return: None
        """
        attribute_line_data = []
        for each_attribute in variation_attribute:
            if each_attribute.get('id') == 0:
                attribute = self.env['product.attribute'].search([('name', '=', each_attribute.get('name')),
                                                                  ('ks_woo_id', '=', -1),
                                                                  ('ks_woo_instance_id', '=', instance_id.id),
                                                                  ('ks_slug', '=', 'product_' + str(self.ks_woo_id))]
                                                                 , order="id desc", limit=1)
            else:
                attribute = self.env['product.attribute'].search([('ks_woo_id', '=', each_attribute.get('id')),
                                                                  ('ks_woo_instance_id', '=', instance_id.id)], limit=1)
            value_ids = []
            if each_attribute.get('options'):
                for att_terms in each_attribute.get('options'):
                    att_value = attribute.value_ids.search(
                        [('name', '=', att_terms), ('attribute_id', '=', attribute.id)], limit=1)
                    value_ids.append(att_value.id)

            attribute_exist = self.attribute_line_ids.search([('attribute_id', '=', attribute.id),
                                                              ('product_tmpl_id', '=', self.id)], limit=1)
            if attribute_exist:
                attribute_line_data.append((1, attribute_exist.id, {
                    'attribute_id': attribute.id,
                    'product_tmpl_id': self.id,
                    'value_ids': [(6, 0, value_ids)]
                }))
            else:
                attribute_line_data.append((0, 0, {'attribute_id': attribute.id, 'product_tmpl_id': self.id,
                                                   'value_ids': [(6, 0, value_ids)]}))
        if attribute_line_data:
            self.write({'attribute_line_ids': attribute_line_data})

    def ks_update_attribute_for_variation(self, attributes, wcapi, instance_id, product_data):
        variation_attribute = []
        visible_attribute = []
        for each_attribute in attributes:
            if each_attribute.get('variation'):
                variation_attribute.append(each_attribute)
                if each_attribute.get('id') == 0:
                    private_attribute_exist = self.env['product.attribute'].search([
                        ('name', '=', each_attribute.get('name')),
                        ('ks_slug', '=', 'product_' + str(self.ks_woo_id)),
                        ('ks_woo_id', '=', -1), ('ks_woo_instance_id', '=', instance_id.id)],
                        limit=1)
                    if not private_attribute_exist:
                        private_attribute_exist = self.env['product.attribute'].create(
                            {'name': each_attribute.get('name'),
                             'ks_slug': "product_" + str(self.ks_woo_id),
                             'ks_woo_instance_id': instance_id.id,
                             'display_type': 'select',
                             'ks_woo_id': -1})
                    for each_term in each_attribute.get('options'):
                        attribute_value_exist = self.env['product.attribute.value'].search([
                            ('name', '=', each_term),
                            ('attribute_id', '=', private_attribute_exist.id),
                            ('ks_woo_id', '=', -1)], limit=1)
                        if not attribute_value_exist:
                            self.env['product.attribute.value'].create({'name': each_term,
                                                                        'attribute_id': private_attribute_exist.id,
                                                                        'ks_woo_id': -1})
                else:
                    try:
                        attributes_woo_data = wcapi.get("products/attributes/%s" % each_attribute.get('id')).json()
                        if attributes_woo_data:
                            self.env['product.attribute'].ks_update_product_attribute_from_woo(attributes_woo_data,
                                                                                               wcapi,
                                                                                               instance_id,
                                                                                               product_data)
                    except ConnectionError:
                        self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                            type='attribute',
                                                                            operation='woo_to_odoo',
                                                                            ks_woo_id=each_attribute.get('id'))
            else:
                visible_attribute.append(each_attribute)
        if visible_attribute:
            self.ks_woo_visible_attributes = visible_attribute
        return variation_attribute

    def prepare_product_template_data(self, json_data, instance_id, wcapi, product_template=False):
        """

        :param json_data: The json data to be created on Odoo
        :param instance_id: The woocommerce instance
        :return: A Dict of product JSON data
        """
        data = {
            "name": json_data.get('name') or '',
            "default_code": json_data.get('sku') or '',
            "type": "product",
            "ks_woo_product_type": json_data.get('type') or '',
            "weight": json_data.get('weight') or '',
            "ks_length": json_data.get('dimensions').get('length') or '',
            "ks_height": json_data.get('dimensions').get('height') or '',
            "ks_width": json_data.get('dimensions').get('width') or '',
            "volume": float(json_data.get('dimensions').get('length') or 0.0) * float(
                json_data.get('dimensions').get('height') or 0.0) * float(
                json_data.get('dimensions').get('width') or 0.0),
            'ks_woo_instance_id': instance_id.id,
            'ks_woo_id': json_data.get('id'),
            'ks_woo_regular_price': float(json_data.get('regular_price') or 0.0) if float(
                json_data.get('regular_price') or 0.0) > float(json_data.get('sale_price') or 0.0) else float(
                json_data.get('sale_price') or 0.0),
            'ks_woo_sale_price': float(json_data.get('sale_price') or 0.0),
            'ks_woo_status': True if json_data.get('status') == 'publish' else False,
            'ks_average_rating': json_data.get('average_rating') or '',
            'ks_date_created': datetime.datetime.strptime((json_data.get('date_created')).replace('T', ' '),
                                                          DEFAULT_SERVER_DATETIME_FORMAT) if json_data.get(
                'date_created') else False,
            'ks_date_updated': datetime.datetime.strptime((json_data.get('date_modified')).replace('T', ' '),
                                                          DEFAULT_SERVER_DATETIME_FORMAT) if json_data.get(
                'date_created') else False,
            'ks_woo_description': json_data.get('description') or '',
            'ks_woo_short_description': json_data.get('short_description') or '',
            'company_id': instance_id.ks_company.id,
            'location_id': instance_id.ks_warehouse.sudo().lot_stock_id.id
        }

        tag_ids = self.env['ks.woo.product.tag'].update_tag_on_odoo(json_data.get('tags')
                                                                    or '', instance_id)
        categ_ids = self.env['product.category'].update_category_on_odoo(json_data.get('categories')
                                                                         or '', instance_id, wcapi)
        if categ_ids:
            data.update({
                'ks_woo_categories': [(6, 0, categ_ids)],
            })
        if not categ_ids:
            # If there is no category then it works
            data.update({
                'ks_woo_categories': [(6, 0, [])],
            })
        if tag_ids:
            data.update({
                'ks_woo_tag': [(6, 0, tag_ids)]
            })
        if not tag_ids:
            # If there is no tag then it works
            data.update({
                'ks_woo_tag': [(6, 0, [])]
            })
        if json_data.get('type') == 'variable' and product_template:
            variation_count = len(json_data.get('variations'))
            if product_template and variation_count <= 1:
                data.update({
                    "list_price": product_template.list_price if product_template.list_price else json_data.get(
                        'price') or 0.0})
            else:
                data.update({"list_price": 0.0})
        else:
            data.update({"list_price": float(json_data.get('price') or 0.0)})
        return data

    def ks_categories_json_data(self, all_categories, wcapi):
        woo_category = []
        if all_categories:
            for each_category in all_categories:
                category_data = self.env['product.category']._prepare_odoo_product_category_data(each_category)
                if each_category.ks_woo_id:
                    record_exist_status = wcapi.get("products/categories/%s" % each_category.ks_woo_id)
                    if record_exist_status.status_code == 404:
                        each_category = self.env['product.category'].create_category_on_woo(wcapi, each_category,
                                                                                            category_data)
                        if each_category:
                            woo_category.append({'id': each_category.ks_woo_id,
                                                 'name': each_category.name,
                                                 'slug': each_category.ks_slug})
                    else:
                        woo_category.append({'id': each_category.ks_woo_id,
                                             'name': each_category.name,
                                             'slug': each_category.ks_slug})
                else:
                    each_category = self.env['product.category'].create_category_on_woo(wcapi, each_category,
                                                                                        category_data)
                    if each_category:
                        woo_category.append({'id': each_category.ks_woo_id,
                                             'name': each_category.name,
                                             'slug': each_category.ks_slug})
            return woo_category

    def ks_tags_json_data(self, all_tags, wcapi, instance_id):
        """

        :param all_tags: Json data for all the avialable tasks in woocommerce
        :param wcapi: The WooCommerce API instance
        :return: The tag ids
        """
        woo_tags = []
        if all_tags:
            for each_tag in all_tags:
                tag_data = self.env['ks.woo.product.tag']._ks_prepare_odoo_product_tag_data(each_tag)
                if each_tag.ks_woo_id:
                    try:
                        record_exist_status = wcapi.get("products/tags/%s" % each_tag.ks_woo_id)
                        if record_exist_status.status_code == 404:
                            each_tag = self.env['ks.woo.product.tag'].ks_create_tag_on_woo(wcapi, tag_data, each_tag)
                            if each_tag:
                                woo_tags.append({'id': each_tag.ks_woo_id,
                                                 'name': each_tag.ks_name,
                                                 'slug': each_tag.ks_slug})
                        else:
                            woo_tags.append({'id': each_tag.ks_woo_id,
                                             'name': each_tag.ks_name,
                                             'slug': each_tag.ks_slug})
                    except ConnectionError:
                        self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                            type='tags',
                                                                            operation='odoo_to_woo',
                                                                            ks_woo_id=each_tag.ks_woo_id)
                else:
                    each_tag = self.env['ks.woo.product.tag'].ks_create_tag_on_woo(wcapi, tag_data, each_tag)
                    if each_tag:
                        woo_tags.append({'id': each_tag.ks_woo_id,
                                         'name': each_tag.ks_name,
                                         'slug': each_tag.ks_slug})
            return woo_tags

    def find_product_template_image(self, json_data, instance_id, product_template):
        """

        :param json_data: The json data to be created on Odoo
        :param instance_id: The current woocommerce instance
        :return: The image record ids
        """
        data = []
        count = 0
        for each_image in json_data:
            image_exist = self.env['ks.woo.product.image'].search([('ks_woo_id', '=', each_image.get('id')),
                                                                   ('ks_woo_instance_id', '=', instance_id.id),
                                                                   ('ks_product_tmpl_id', '=', product_template.id)],
                                                                  limit=1)
            if image_exist:
                image_data = self.prepare_image_data(each_image, instance_id, image_exist.ks_image, product_template)
                if not count:
                    image_data.update({
                        'sequence': -999,
                    })
                else:
                    image_data.update({
                        'sequence': 0,
                    })
                count = count + 1
                image_exist.write(image_data)
                data.append(image_exist.id)
            else:
                image_base64 = self.ks_image_read_from_url(each_image)
                if image_base64:
                    image_data = self.prepare_image_data(each_image, instance_id, image_base64, product_template)
                    if not count:
                        image_data.update({
                            'sequence': -999,
                        })
                    else:
                        image_data.update({
                            'sequence': 0,
                        })
                    count = count + 1
                    image = self.env['ks.woo.product.image'].create(image_data)
                    data.append(image.id)
        for existing_image in self.ks_product_image_ids:
            if existing_image.id not in data:
                existing_image.sequence = 0
        return data

    def ks_image_read_from_url(self, image_data):
        """

        :param image_data: Woo Image record that contains image related data
        :return: The Base64 format of image by reading the image from url
        """
        if image_data:
            response = requests.get(image_data.get('src'))
            if response.status_code == 200:
                image_base64 = base64.encodebytes(response.content)
                return image_base64

    def prepare_image_data(self, image_data, instance_id, image_base64, product_template):
        """

        :param image_data: Woo Image record that contains image related data
        :param instance_id: The woocommerce instance
        :param image_base64: The image in Base64 format
        :return: A Dict od json data for images
        """
        data = {
            'ks_image': image_base64,
            'ks_file_name': image_data.get('name'),
            'ks_woo_id': image_data.get('id'),
            'ks_woo_instance_id': instance_id.id,
            'ks_src': image_data.get('src'),
            'ks_product_tmpl_id': product_template.id
        }
        return data

    def ks_average_woo_product_rating(self):
        pass

    def ks_publish_unpublish_data(self, product_records, op_type):
        json_data = []
        for rec in product_records:
            json_data.append({
                'id': rec.ks_woo_id,
                'status': 'publish' if op_type == 'publish' else 'draft'
            })
        return {
            'update': json_data
        }

    # This function updates the price change on the product
    def ks_update_price_on_product(self, json_data):
        """
        :param json_data: Product data from woocommerce
        :return: none
        """
        pricelists = self.ks_woo_instance_id.ks_woo_sale_pricelist.search(
            [('ks_instance_id', '=', self.ks_woo_instance_id.id), ('ks_onsale_pricelist', '=', True),
             ('currency_id', '=', self.ks_woo_instance_id.ks_woo_currency.id)])
        self.ks_woo_regular_price = float(json_data.get('regular_price') or 0.0) if float(
            json_data.get('regular_price') or 0.0) > float(json_data.get('sale_price') or 0.0) else float(
            json_data.get('sale_price') or 0.0)
        if self.ks_woo_instance_id.ks_global_discount_enable and not self.ks_woo_instance_id.ks_global_discount:
            self.ks_woo_sale_price = 0.0
        elif self.ks_woo_instance_id.ks_global_discount_enable and self.ks_woo_instance_id.ks_global_discount:
            self.ks_woo_sale_price = float((
                0 if self.ks_woo_product_type == 'variable' else self.ks_woo_instance_id.ks_woo_sale_pricelist.search(
                    [('ks_instance_id', '=', self.ks_woo_instance_id.id),
                     ('currency_id', '=', self.ks_woo_instance_id.ks_woo_currency.id),
                     ('ks_onsale_pricelist', '=', True)]).item_ids.search([('pricelist_id', '=', pricelists.id),
                                                                           ('applied_on', '=', '0_product_variant'),
                                                                           ('product_tmpl_id', '=', self.id),
                                                                           ('compute_price', '=', 'fixed'),
                                                                           ('ks_instance_id', '=',
                                                                            self.ks_woo_instance_id.id)]).fixed_price))
        else:
            self.ks_woo_sale_price = float(json_data.get('sale_price') or 0.0)
        self.list_price = self.ks_woo_sale_price if self.ks_woo_sale_price else self.ks_woo_regular_price
        instance_id = self.ks_woo_instance_id
        ks_pricelists = instance_id.ks_woo_pricelist_ids
        if not ks_pricelists:
            ks_pricelists = []
            ks_pricelists.append(instance_id.ks_woo_pricelist)
            ks_pricelists.append(instance_id.ks_woo_sale_pricelist)
        for ks_pricelist in ks_pricelists:
            self.ks_update_price_on_price_list(json_data, ks_pricelist, self.product_variant_id, instance_id)

    # This function updates the price on every pricelist created for current instance
    def ks_update_price_on_price_list(self, json_data, price_list, product_record, ks_instance):
        """
        :param json_data: Product data from woocommerce
        :param price_list: current pricelist
        :param product_record: current product record data in odoo
        :param ks_instance: Current instance details
        :return: none
        """
        record_exist = price_list.item_ids.search([('pricelist_id', '=', price_list.id),
                                                   ('applied_on', '=', '0_product_variant'),
                                                   ('product_id', '=', product_record.id),
                                                   ('compute_price', '=', 'fixed'),
                                                   ('ks_instance_id', '=', ks_instance.id)],
                                                  limit=1)
        if price_list.ks_onsale_pricelist == False:
            ks_price = float(json_data.get('regular_price') or 0.0) if float(
                json_data.get('regular_price') or 0.0) > float(json_data.get('sale_price') or 0.0) else float(
                json_data.get('sale_price') or 0.0)
        else:
            if ks_instance.ks_global_discount_enable and ks_instance.ks_global_discount:
                record_exist.ks_on_sale_price = True
                ks_price = (float(json_data.get('regular_price') or 0.0) if float(
                    json_data.get('regular_price') or 0.0) > float(json_data.get('sale_price') or 0.0) else float(
                    json_data.get('sale_price') or 0.0)) - (
                                   (float(json_data.get('regular_price') or 0.0) if float(
                                       json_data.get('regular_price') or 0.0) > float(
                                       json_data.get('sale_price') or 0.0) else float(
                                       json_data.get('sale_price') or 0.0) * ks_instance.ks_global_discount) / 100) * 10
            elif ks_instance.ks_global_discount_enable and not ks_instance.ks_global_discount:
                ks_price = 0.0
            else:
                ks_price = float(json_data.get('sale_price') or 0.0)
        ks_sale_price = float(json_data.get('sale_price') or 0.0)
        if price_list.ks_onsale_pricelist:
            record_exist.ks_on_sale_price = True
        if record_exist:
            if price_list.id == ks_instance.ks_woo_pricelist.id or price_list.id == ks_instance.ks_woo_sale_pricelist.id:
                record_exist.fixed_price = ks_price
                # if record_exist.product_id.ks_woo_product_type == 'variable':
                #     record_exist.product_id.ks_woo_variant_sale_price = ks_price
            else:
                conversion_rate = price_list.currency_id.rate / ks_instance.ks_woo_pricelist.currency_id.rate
                record_exist.fixed_price = ks_price * conversion_rate

            if ks_price < float(json_data.get('regular_price') or 0.0) if float(
                    json_data.get('regular_price') or 0.0) > float(json_data.get('sale_price') or 0.0) else float(
                json_data.get('sale_price') or 0.0) or (
                                                                                                                    ks_price == ks_sale_price and ks_sale_price != 0.0):
                record_exist.ks_on_sale_price = True
            else:
                record_exist.ks_on_sale_price = False
        else:
            price_list_item = {
                'pricelist_id': price_list.id,
                'applied_on': '0_product_variant',
                'product_tmpl_id': product_record.product_tmpl_id.id,
                'product_id': product_record.id,
                'compute_price': 'fixed',
                'ks_instance_id': product_record.ks_woo_instance_id.id
            }
            if price_list.id == ks_instance.ks_woo_pricelist.id or price_list.id == ks_instance.ks_woo_sale_pricelist.id:
                price_list_item.update({
                    'fixed_price': ks_price
                })
            else:
                conversion_rate = price_list.currency_id.rate / ks_instance.ks_woo_pricelist.currency_id.rate
                computed_price = ks_price * conversion_rate
                price_list_item.update({
                    'fixed_price': computed_price
                })

            if ks_price == ks_sale_price and ks_sale_price != 0.0:
                price_list_item.update({
                    'ks_on_sale_price': True,
                })
            else:
                price_list_item.update({
                    'ks_on_sale_price': False,
                })
            price_list.item_ids.create(price_list_item)

    def ks_price_export_in_woo(self, price_list_instance, product_record):
        price_dict = {}
        if price_list_instance.ks_woo_sale_pricelist:
            record_exist = price_list_instance.ks_woo_sale_pricelist.item_ids.search(
                [('pricelist_id', '=', price_list_instance.ks_woo_sale_pricelist.id),
                 ('applied_on', '=', '0_product_variant'),
                 ('product_id', '=', product_record.id),
                 ('compute_price', '=', 'fixed'),
                 ('ks_instance_id', '=', product_record.ks_woo_instance_id.id)],
                limit=1)
        else:
            record_exist = price_list_instance.ks_woo_pricelist.item_ids.search(
                [('pricelist_id', '=', price_list_instance.ks_woo_pricelist.id),
                 ('applied_on', '=', '0_product_variant'),
                 ('product_id', '=', product_record.id),
                 ('compute_price', '=', 'fixed'),
                 ('ks_instance_id', '=', product_record.ks_woo_instance_id.id)],
                limit=1)
        if record_exist:
            if record_exist.ks_on_sale_price:
                price_dict.update({
                    'sale_price': "" if record_exist.fixed_price == 0.0 else str(record_exist.fixed_price),
                })
            else:
                price_dict.update({
                    'regular_price': "" if record_exist.fixed_price == 0.0 else str(record_exist.fixed_price),
                })
        return price_dict

    def ks_import_stock_woocommerce(self, wcapi, instance_id):
        """
        This will get the woocommerce product data and update the products stock quantity on odoo

        :param wcapi: The WooCommerce API instance
        :param instance_id: The WooCommerce instance
        :return: None
        """
        multi_api_call = True
        per_page = 100
        page = 1
        product_records = []
        while (multi_api_call):
            try:
                woo_product_response = wcapi.get("products", params={"per_page": per_page, "page": page})
                if woo_product_response.status_code in [200, 201]:
                    woo_products_record = woo_product_response.json()
                    product_records += woo_products_record
                else:
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='failed',
                        ks_type='stock',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='fetch',
                        response=str(woo_product_response.status_code) + eval(woo_product_response.text).get('message'),
                    )

                total_api_calls = woo_product_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                else:
                    multi_api_call = False
            except ConnectionError:
                self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                    type='stock',
                                                                    operation='woo_to_odoo',
                                                                    ks_woo_id=False)
        self.ks_manage_inventory_adjustments(product_records, instance_id, wcapi)

    def ks_manage_inventory_adjustments(self, product_records, instance_id, wcapi):
        record = []
        records_id = []
        for each_product in product_records:
            product = self.search([('ks_woo_id', '=', each_product.get('id')),
                                   ('ks_woo_instance_id', '=', instance_id.id)], limit=1)
            variation_id = each_product.get('variations')
            if variation_id:
                for each_variation in variation_id:
                    product_variant = self.env['product.product'].search([
                        ('ks_woo_id', '=', each_product.get('id')),
                        ('ks_woo_instance_id', '=', instance_id.id),
                        ('ks_woo_variant_id', '=', each_variation)], limit=1)
                    if product_variant:
                        woo_variant_response = wcapi.get("products/%s" % each_variation)
                        if woo_variant_response.status_code in [200, 201]:
                            woo_variant_record = woo_variant_response.json()
                            if woo_variant_record.get('manage_stock') and woo_variant_record.get(
                                    'manage_stock') != 'parent':
                                if woo_variant_record.get('stock_quantity') != 0:
                                    record.append((0, 0, {
                                        'product_id': product_variant.id,
                                        'product_qty': woo_variant_record.get('stock_quantity'),
                                        'location_id': instance_id.ks_warehouse.lot_stock_id.id
                                    }))
                                    records_id.append(product_variant.id)
            if each_product.get('type') in ['simple'] and each_product.get(
                    'manage_stock') and product.product_variant_id:
                if each_product.get('stock_quantity') != 0:
                    record.append((0, 0, {
                        'product_id': product.product_variant_id.id,
                        'product_qty': each_product.get('stock_quantity'),
                        'location_id': instance_id.ks_warehouse.lot_stock_id.id
                    }))
                    records_id.append(product.product_variant_id.id)
        if record:
            inventory_adjustment = self.env['stock.inventory'].create({
                'name': instance_id.ks_name + ' ' + product.product_variant_id.name + ' [' + str(
                    fields.datetime.now()) + ']',
                'company_id': instance_id.ks_company.id,
                'product_ids': [(6, 0, records_id)]
            })
            try:
                inventory_adjustment.write({'line_ids': record})
                self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                             ks_status='success',
                                                             ks_type='stock',
                                                             ks_woo_instance_id=instance_id,
                                                             ks_operation='woo_to_odoo',
                                                             ks_operation_type='batch_update',
                                                             response='Inventory adjustment for product ' + product.name + ' has been created ,Validate it to import stock for the products.')

            except Exception as e:
                self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                             ks_status='failed',
                                                             ks_type='stock',
                                                             ks_woo_instance_id=instance_id,
                                                             ks_operation='woo_to_odoo',
                                                             ks_operation_type='batch_update',
                                                             response='Inventory adjustment failed due to %s ' % e)

    def ks_batch_update_response(self, wcapi, woo_response, instance_id, product_variant=False):
        product = 'Product Variant ' if product_variant else 'Product '
        if woo_response.status_code in [200, 201]:
            woo_records = woo_response.json()
            if woo_records:
                for each_rec in woo_records.get('update'):
                    if each_rec.get('error'):
                        ks_status = "failed"
                        ks_woo_id = each_rec.get('id')
                        response = product + 'Stock update operation for Woo Id [' + str(
                            each_rec.get('id')) + '] failed due to ' + each_rec.get('error').get('message')
                    else:
                        ks_status = "success"
                        ks_woo_id = each_rec.get('id')
                        # self.ks_import_stock_woocommerce(wcapi, instance_id) This is making inventory adjustment while exporting the stock
                        response = 'The stock has been successfully updated for ' + product + ' with Woo Id [' + str(
                            each_rec.get('id')) + ']'
                    self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=ks_woo_id,
                                                                 ks_status=ks_status,
                                                                 ks_type='product',
                                                                 ks_woo_instance_id=instance_id,
                                                                 ks_operation='odoo_to_woo',
                                                                 ks_operation_type='batch_update',
                                                                 response=response)
        else:
            ks_status = "failed"
            ks_woo_id = False
            response = product + 'Stock update operation failed due to  ' + eval(woo_response.text).get('message')
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=ks_woo_id,
                                                         ks_status=ks_status,
                                                         ks_type='product',
                                                         ks_woo_instance_id=instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='batch_update',
                                                         response=response)

    def ks_change_product_price(self):
        pricelist = self.ks_woo_instance_id.ks_woo_pricelist
        currency = self.ks_woo_instance_id.ks_woo_currency
        rec = self.env['ks.change.product.price'].sudo().create({
            'ks_currency_id': currency.id,
            'ks_price_list_id': pricelist.id,
            'ks_instance_id': self.ks_woo_instance_id.id
        })
        vals = []
        variant_ids = self.product_variant_ids
        for variant_id in variant_ids:
            pricelist_item = pricelist.item_ids.search(
                [('product_id', '=', variant_id.id), ('ks_instance_id', '=', self.ks_woo_instance_id.id),
                 ('pricelist_id', '=', pricelist.id)])
            variant_data = {
                'ks_change_price_id': rec.id,
                'ks_product_id': variant_id.id,
                'ks_product_tmpl_id': self.id,
                'ks_pricelist_item_id': pricelist_item.id,
                'ks_old_price': pricelist_item.fixed_price,
                'ks_new_price': 0,
            }
            vals.append(variant_data)
        self.env['ks.product.price'].sudo().create(vals)
        return {
            'name': _('Change Product List Price'),
            'view_mode': 'form',
            'res_model': 'ks.change.product.price',
            'res_id': rec.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self._context,
        }


class KsWooProductImage(models.Model):
    _name = 'ks.woo.product.image'
    _description = 'Woo Product Image'
    _order = 'sequence asc'

    ks_file_name = fields.Char('Image Name', required=True)
    ks_image = fields.Image('Image', required="True")
    ks_woo_instance_id = fields.Many2one('ks.woocommerce.instances', 'Instance',
                                         related='ks_product_tmpl_id.ks_woo_instance_id')
    ks_woo_id = fields.Integer('WooCommerce Id', readonly=True, default=0)
    ks_product_tmpl_id = fields.Many2one('product.template')
    ks_exported_in_woo = fields.Boolean('Exported in Woo', compute='_ks_compute_export_in_woo')
    ks_src = fields.Char('Woo Link')
    sequence = fields.Integer()
    ks_profile_image = fields.Boolean('Profile Image or not ?')

    @api.depends('ks_woo_id')
    def _ks_compute_export_in_woo(self):
        """
        This will make enable the Exported in Woo if record has the WooCommerce Id

        :return: None
        """
        for rec in self:
            rec.ks_exported_in_woo = bool(rec.ks_woo_id)

    def ks_woo_image_url(self, template_id, image_id, filename):
        """
        :param template_id: Product Id
        :param image_id: Product Image Id
        :param filename: Product Image File Name
        :return: This will return the public image url
        """
        ext = len(filename.split('.'))
        if not ext > 1:
            filename = filename + '.jpg'
        base_url = '/' if self.env.context.get('relative_url') else \
            self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        public_url = urls.url_join(base_url, "/ks_woo_image/%s/%s/%s/%s/%s" % (
            request.session.db, self.env.user.id, template_id, image_id, filename))
        return public_url

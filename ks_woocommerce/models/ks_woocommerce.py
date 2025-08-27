# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from requests.exceptions import ConnectionError
from woocommerce import API as WCAPI
from odoo.http import request


class KsWooCommerceInstance(models.Model):
    _name = 'ks.woocommerce.instances'
    _description = 'WooCommerce Instances Details'
    _rec_name = 'ks_name'

    ks_name = fields.Char('Woo Instance Name', required=True)
    ks_woo_store_url = fields.Char('WooCommerce Store URL', required=True)
    ks_customer_key = fields.Char('Customer Key', required=True)
    ks_customer_secret = fields.Char('Customer Secret', required=True)
    ks_verify_ssl = fields.Boolean('Verify SSL')
    ks_auth = fields.Boolean('Authorization')
    ks_wc_version = fields.Selection([('wc/v3', '3.5.x or later'), ('wc/v2', '3.0.x or later'),
                                      ('wc/v1', '2.6.x or later')],
                                     string='WooCommerce Version', default='wc/v3', readonly=True,
                                     required=True)
    color = fields.Integer(default=10)
    ks_stock_field_type = fields.Many2one('ir.model.fields', 'Stock Field Type',
                                          domain="[('model_id', '=', 'product.product'),"
                                                 "('name', 'in', ['qty_available','virtual_available'])]")
    ks_instance_state = fields.Selection([('draft', 'Draft'), ('connected', 'Connected'), ('active', 'Active'),
                                          ('deactivate', 'Deactivate')], string="Woo Instance State", default="draft")
    ks_instance_connected = fields.Boolean(default=False)
    ks_company = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id, readonly=1)
    ks_warehouse = fields.Many2one('stock.warehouse', 'Warehouse', domain="[('company_id', '=', ks_company)]")

    ks_woo_currency = fields.Many2one('res.currency', 'Main Currency', default=lambda self: self.ks_company.currency_id)
    ks_multi_currency_option = fields.Boolean(string='Multi-Currency Option', default=False)
    ks_woo_multi_currency = fields.Many2many(comodel_name='res.currency', string='Multi-Currency')

    ks_import_order_state_config = fields.One2many('ks.woocommerce.status', 'ks_instance_id')
    ks_sales_team = fields.Many2one('crm.team', string="Sales Team")
    ks_sales_person = fields.Many2one('res.users', string="Sales Person")
    ks_use_custom_order_prefix = fields.Boolean(string='Use Custom Order Prefix')
    ks_order_prefix = fields.Char(string="Order Prefix")
    ks_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    ks_journal_id = fields.Many2one('account.journal', string='Payment Method',
                                    domain=[('type', 'in', ('bank', 'cash'))])
    ks_woo_count_orders = fields.Integer('Order Count', compute='_compute_count_of_woo_records')
    ks_woo_count_products = fields.Integer('Product Count', compute='_compute_count_of_woo_records')
    ks_woo_count_coupons = fields.Integer('Coupon Count', compute='_compute_count_of_woo_records')
    ks_woo_count_customers = fields.Integer('Customer Count', compute='_compute_count_of_woo_records')
    ks_woo_fees = fields.Many2one('product.product', 'Woo Fees')
    ks_woo_shipping = fields.Many2one('product.product', 'Woo Shipping')
    ks_auto_update_stock = fields.Boolean('Auto Update Product Stock?')
    ks_aus_cron_id = fields.Many2one('ir.cron', readonly=1)
    ks_aus_cron_last_updated = fields.Datetime('Last Updated [Product Stock]', related='ks_aus_cron_id.lastcall',
                                               readonly=True)
    ks_aus_cron_next_update = fields.Datetime('Next Update [Product Stock]', related='ks_aus_cron_id.nextcall',
                                              readonly=True)
    ks_aus_update_permission = fields.Boolean(string="Update Product Stock", default=False)
    ks_aus_cron_active_permission = fields.Boolean(default=False, string="Active/Inactive Product Stock Cron")
    ks_auto_update_order_status = fields.Boolean('Auto Update Order Status?')
    ks_auos_cron_id = fields.Many2one('ir.cron', readonly=1)
    ks_auos_cron_last_updated = fields.Datetime('Last Updated [Order Status]', related='ks_auos_cron_id.lastcall',
                                                readonly=True)
    ks_auos_cron_next_update = fields.Datetime('Next Update [Order Status]', related='ks_auos_cron_id.nextcall',
                                               readonly=True)
    ks_auos_update_permission = fields.Boolean(string="Update Order Status Cron", default=False)
    ks_auos_cron_active_permission = fields.Boolean(default=False, string="Active/Inactive Order Status Cron")
    ks_auto_import_order = fields.Boolean('Auto Import Order?')
    ks_aio_cron_id = fields.Many2one('ir.cron', readonly=1)
    ks_aio_cron_last_updated = fields.Datetime('Last Updated [Sale Order]', related='ks_aio_cron_id.lastcall',
                                               readonly=True)
    ks_aio_cron_next_update = fields.Datetime('Next Update [Sale Order]', related='ks_aio_cron_id.nextcall',
                                              readonly=True)
    ks_aio_update_permission = fields.Boolean(string="Update Order Cron", default=False)
    ks_aio_cron_active_permission = fields.Boolean(default=False, string="Active/Inactive Order Update Cron")

    ks_auto_import_product = fields.Boolean('Auto Import Product?')
    ks_aip_cron_id = fields.Many2one('ir.cron', readonly=1)
    ks_aip_cron_last_updated = fields.Datetime('Last Updated [Product]', related='ks_aip_cron_id.lastcall',
                                               readonly=True)
    ks_aip_cron_next_update = fields.Datetime('Next Update [Product]', related='ks_aip_cron_id.nextcall',
                                              readonly=True)
    ks_aip_update_permission = fields.Boolean(string="Update Product Cron", default=False)
    ks_aip_cron_active_permission = fields.Boolean(default=False, string="Active/Inactive Product Update Cron")

    ks_woo_customer = fields.Many2one('res.partner', 'Woo Customer')
    ks_base_url = fields.Char(default=lambda self: self.env['ir.config_parameter'].sudo().get_param('web.base.url'))
    ks_woo_pricelist = fields.Many2one('product.pricelist', string='Regular Main Pricelist', store=True,
                                       compute='_ks_pricelist_on_currency_change')
    ks_woo_sale_pricelist = fields.Many2one('product.pricelist', string='OnSale Main Pricelist', store=True,
                                       compute='_ks_pricelist_on_currency_change')
    ks_global_discount_enable = fields.Boolean(string='Enable/Disable Global Discount', default=False)
    ks_global_discount = fields.Float(string='Global Discount (%)', default=0.0)
    ks_woo_pricelist_ids = fields.Many2many('product.pricelist', string='Multi-Pricelist', store=True,
                                            compute='_ks_multi_pricelist_on_multi_currency_change')
    ks_woo_auto_order_status = fields.Boolean('Auto Order Status Update')
    ks_woo_order_status_invoice = fields.Char(default='Invoice', readonly=True, string='Invoice Stage')
    ks_woo_order_status_shipment = fields.Char(default='Shipment', readonly=True, string='Shipment Stage')
    ks_options = fields.Char()
    ks_woo_order_invoice_selection = fields.Selection([('pending', 'Pending'), ('on-hold', 'On-Hold'),
                                                       ('processing', 'Processing'), ('completed', 'Completed')],
                                                      string='Invoice State')
    ks_woo_order_shipment_selection = fields.Selection([('pending', 'Pending'), ('on-hold', 'On-Hold'),
                                                        ('processing', 'Processing'), ('completed', 'Completed')],
                                                       string='Shipment State')
    ks_id = fields.Char(string="Instance Unique No.", required=True, copy=False, index=True, readonly=True,
                        default='New')
    # Todo
    ks_import_images_with_products = fields.Boolean(default=False, string="Import/Export Products with Images")

    # Todo these fields are used for cron testing
    # order import cron fields on instance
    ks_cron_aio_schedule_user = fields.Many2one('res.users', string="Scheduler User",
                                                default=lambda self: self.env.user)
    ks_cron_aio_interval_number = fields.Integer(string='Execute Every', default=1)
    ks_cron_aio_nextcall = fields.Datetime(string="Execution Date")
    ks_cron_aio_interval_type = fields.Selection([('minutes', 'Minutes'),
                                                  ('hours', 'Hours'),
                                                  ('days', 'Days'),
                                                  ('weeks', 'Weeks'),
                                                  ('months', 'Months')], string='Interval Unit', default='months')
    # product import cron on instance
    ks_cron_ip_schedule_user = fields.Many2one('res.users', string="Scheduler User", default=lambda self: self.env.user)
    ks_cron_ip_interval_number = fields.Integer(string='Execute Every', default=1)
    ks_cron_ip_nextcall = fields.Datetime(string="Execution Date")
    ks_cron_ip_interval_type = fields.Selection([('minutes', 'Minutes'),
                                                 ('hours', 'Hours'),
                                                 ('days', 'Days'),
                                                 ('weeks', 'Weeks'),
                                                 ('months', 'Months')], string='Interval Unit', default='months')

    # auto order status update cron from instance
    ks_cron_auos_schedule_user = fields.Many2one('res.users', string="Scheduler User",
                                                 default=lambda self: self.env.user)
    ks_cron_auos_interval_number = fields.Integer(string='Execute Every', default=1)
    ks_cron_auos_nextcall = fields.Datetime(string="Execution Date")
    ks_cron_auos_interval_type = fields.Selection([('minutes', 'Minutes'),
                                                   ('hours', 'Hours'),
                                                   ('days', 'Days'),
                                                   ('weeks', 'Weeks'),
                                                   ('months', 'Months')], string='Interval Unit', default='months')

    # auto update stock using cron from instance
    ks_cron_aus_schedule_user = fields.Many2one('res.users', string="Scheduler User",
                                                default=lambda self: self.env.user)
    ks_cron_aus_interval_number = fields.Integer(string='Execute Every', default=1)
    ks_cron_aus_nextcall = fields.Datetime(string="Execution Date")
    ks_cron_aus_interval_type = fields.Selection([('minutes', 'Minutes'),
                                                  ('hours', 'Hours'),
                                                  ('days', 'Days'),
                                                  ('weeks', 'Weeks'),
                                                  ('months', 'Months')], string='Interval Unit', default='months')
    ks_database_name = fields.Char('Database Name', compute='_compute_count_of_woo_records')
    ks_current_user = fields.Char('Current User', compute='_compute_count_of_woo_records')

    # This function is used to reset global discount value on Gobal Discount Toggle button disable
    @api.onchange('ks_global_discount_enable')
    def onchange_ks_global_discount_enable(self):
        """
        :return: none
        """
        for rec in self:
            if not rec.ks_global_discount_enable:
                rec.ks_global_discount = 0.0

    # This function is used to Change the value of sale price in pricelist when global discount value is given and saved
    @api.constrains('ks_global_discount')
    def depends_ks_global_discount(self):
        """
        :return: none
        """
        for rec in self:
            if rec.ks_global_discount >= 100:
                raise ValidationError("Discount should be less than 100% !")
            elif rec.ks_global_discount < 0:
                raise ValidationError('Discount cannot be less than 0% !')
            if rec.ks_woo_pricelist_ids:
                pricelist = rec.ks_woo_pricelist_ids
            else:
                pricelist = []
                pricelist.append(rec.ks_woo_pricelist)
                pricelist.append(rec.ks_woo_sale_pricelist)
            for record in pricelist:
                for data in record.item_ids:
                    self.ks_update_price_on_price_list_instance(record, data, rec)

    # This function is used to update prices on every pricelist created under current instance with the conversion rate
    def ks_update_price_on_price_list_instance(self, price_list, record_exist, ks_instance):
        """
        :param price_list: current pricelist data
        :param record_exist: existing pricelist data in the database
        :param ks_instance: current instance data
        :return: none
        """
        ks_woo_regular_price = 0
        if record_exist.product_id.ks_woo_product_type != 'variable':
            ks_woo_regular_price = record_exist.product_id.ks_woo_regular_price
        else:
            ks_woo_regular_price = record_exist.product_id.ks_woo_variant_reg_price
        if price_list.ks_onsale_pricelist == False:
            ks_price = float(ks_woo_regular_price or 0.0)
        else:
            if ks_instance.ks_global_discount_enable and ks_instance.ks_global_discount:
                record_exist.ks_on_sale_price = True
                ks_price = (float(ks_woo_regular_price or 0.0)) - (
                            (float(ks_woo_regular_price or 0.0) * ks_instance.ks_global_discount) / 100)
                record_exist.product_id.list_price = ks_price
            elif ks_instance.ks_global_discount_enable and not ks_instance.ks_global_discount:
                ks_price = 0.0
                record_exist.product_id.list_price = ks_woo_regular_price
            else:
                ks_price = float(record_exist.product_id.ks_woo_sale_price or 0.0)
                record_exist.product_id.list_price = record_exist.product_id.ks_woo_sale_price if record_exist.product_id.ks_woo_sale_price else record_exist.product_id.ks_woo_regular_price
            if record_exist.currency_id.id == ks_instance.ks_woo_currency.id:
                if record_exist.product_id.ks_woo_product_type != 'variable':
                    record_exist.product_id.ks_woo_sale_price = ks_price
                else:
                    record_exist.product_id.ks_woo_variant_sale_price = ks_price
        ks_sale_price = float(record_exist.product_id.ks_woo_sale_price or 0.0)
        if price_list.ks_onsale_pricelist:
            record_exist.ks_on_sale_price = True
        if record_exist:
            if price_list.id == ks_instance.ks_woo_pricelist.id or price_list.id == ks_instance.ks_woo_sale_pricelist.id:
                record_exist.fixed_price = ks_price
            else:
                conversion_rate = price_list.currency_id.rate / ks_instance.ks_woo_pricelist.currency_id.rate
                record_exist.fixed_price = ks_price * conversion_rate

            if ks_price < float(ks_woo_regular_price or 0.0) or (
                    ks_price == ks_sale_price and ks_sale_price != 0.0):
                record_exist.ks_on_sale_price = True
            else:
                record_exist.ks_on_sale_price = False
        else:
            price_list_item = {
                'pricelist_id': price_list.id,
                'applied_on': '0_product_variant',
                'product_tmpl_id': record_exist.product_tmpl_id.id,
                'product_id': record_exist.product_id.id,
                'compute_price': 'fixed',
                'ks_instance_id': record_exist.ks_woo_instance_id.id
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

    def name_get(self):
        result = []
        for instance in self:
            name = "[" + instance.ks_id + "] - " + instance.ks_name
            result.append((instance.id, name))
        return result

    # @api.onchange('ks_woo_order_invoice_selection')
    # def auto_order(self):
    #     ls_ks_options = ['pending','on-hold','processing','completed']
    #     if self.ks_woo_auto_order_status and len(self.ks_woo_order_invoice_selection) > 0:
    #         return {
    #             'domain': {
    #                 'ks_woo_currency': [('id', 'not in', ls_ks_options)]
    #             }
    #         }
    #     return {
    #         'domain': {
    #             'ks_woo_currency': [('id', 'in', [])]
    #         }
    #     }

    # This function is used to set domain for main currency on the change of multi currency option or multi currency field
    @api.onchange('ks_woo_multi_currency', 'ks_multi_currency_option')
    def ks_pricelist_domain(self):
        """
        :return: none
        """
        if self.ks_multi_currency_option and len(self.ks_woo_multi_currency) > 0:
            return {
                'domain': {
                    'ks_woo_currency': [('id', 'in', self.ks_woo_multi_currency.ids)]
                }
            }
        elif not self.ks_multi_currency_option:
            return {
                'domain': {
                    'ks_woo_currency': [('id', 'in', self.env['res.currency'].search([]).ids)]
                }
            }
        return {
            'domain': {
                'ks_woo_currency': [('id', 'in', [])]
            }
        }

    @api.model
    def create(self, values):
        values.update({
            'ks_import_order_state_config': [
                (0, 0, {'ks_woo_states': 'on-hold', 'ks_odoo_state': 'draft'}),
                (0, 0, {'ks_woo_states': 'pending', 'ks_odoo_state': 'sale'}),
                (0, 0, {'ks_woo_states': 'processing', 'ks_odoo_state': 'sale', 'ks_create_invoice': True,
                        'ks_set_invoice_state': 'paid'}),
                (0, 0, {'ks_woo_states': 'completed', 'ks_odoo_state': 'sale', 'ks_create_invoice': True,
                        'ks_set_invoice_state': 'paid', 'ks_confirm_shipment': True})],
            'ks_woo_fees': self.env.ref('ks_woocommerce.ks_woo_fees').id,
            'ks_woo_shipping': self.env.ref('ks_woocommerce.ks_woo_shipping_fees').id,
            'ks_woo_customer': self.env.ref('ks_woocommerce.ks_woo_guest_customers').id
        })
        if values.get('ks_id', 'New') == 'New':
            values['ks_id'] = self.env['ir.sequence'].next_by_code(
                'ks.woocommerce.instances') or 'New'
        res = super(KsWooCommerceInstance, self).create(values)
        res.ks_manage_auto_job()
        return res

    def write(self, values):
        res = super(KsWooCommerceInstance, self).write(values)
        if self._context.get('ks_manage_auto_job', False):
            return res
        self.ks_manage_auto_job()
        return res

    # This function is used to set domain for main currency on the change of multi currency option or multi currency field
    @api.onchange('ks_multi_currency_option')
    def ks_main_currency_change(self):
        """
        :return: none
        """
        for rec in self:
            if rec.ks_multi_currency_option:
                rec.ks_woo_currency = False
                rec.ks_woo_pricelist = False
            else:
                rec.ks_woo_multi_currency = [(5, 0, 0)]
                rec.ks_woo_pricelist_ids = [(5, 0, 0)]

    # This function is used create main pricelist
    @api.depends('ks_woo_currency')
    def _ks_pricelist_on_currency_change(self):
        """
        :return: none
        """
        for rec in self:
            if 'int' in str(type(rec.id)):
                if rec.ks_woo_currency:
                    regular_pricelist_id = self.env['product.pricelist'].search([('ks_instance_id', '=', rec.id),
                                                                         ('currency_id', '=', rec.ks_woo_currency.id),
                                                                         ('ks_onsale_pricelist', '=', False)])
                    onsale_pricelist_id = self.env['product.pricelist'].search([('ks_instance_id', '=', rec.id),
                                                                         ('currency_id', '=', rec.ks_woo_currency.id),
                                                                         ('ks_onsale_pricelist', '=', True)])
                    if regular_pricelist_id:
                        rec.ks_woo_pricelist = regular_pricelist_id[0].id
                    else:
                        price_list_data = {
                            'name': rec.ks_name + ' ' + (rec.ks_woo_currency and rec.ks_woo_currency.name or '-') + ' Regular Pricelist',
                            'currency_id': rec.ks_woo_currency.id or rec.ks_company.currency_id.id,
                            'company_id': rec.ks_company.id,
                            'ks_instance_id': rec.id,
                            'ks_onsale_pricelist': False,
                        }
                        pricelist_id = self.env['product.pricelist'].create(price_list_data)
                        rec.ks_woo_pricelist = pricelist_id.id
                    if onsale_pricelist_id:
                        rec.ks_woo_sale_pricelist = onsale_pricelist_id[0].id
                    else:
                        price_list_data = {
                            'name': rec.ks_name + ' ' + (rec.ks_woo_currency and rec.ks_woo_currency.name or '-') + ' OnSale Pricelist',
                            'currency_id': rec.ks_woo_currency.id or rec.ks_company.currency_id.id,
                            'company_id': rec.ks_company.id,
                            'ks_instance_id': rec.id,
                            'ks_onsale_pricelist': True,
                        }
                        pricelist_id = self.env['product.pricelist'].create(price_list_data)
                        rec.ks_woo_sale_pricelist = pricelist_id.id
            else:
                rec.ks_woo_pricelist = False
                rec.ks_woo_sale_pricelist = False
            if rec.ks_woo_multi_currency:
                rec.ks_woo_pricelist_ids = rec.ks_woo_pricelist.search([('ks_instance_id', '=', rec.id)]).ids
                rec._ks_multi_pricelist_on_multi_currency_change()

    # This function is used create multi pricelist
    @api.depends('ks_woo_multi_currency')
    def _ks_multi_pricelist_on_multi_currency_change(self):
        """
        :return: none
        """
        for rec in self:
            if 'int' in str(type(rec.id)):
                if rec.ks_woo_multi_currency:
                    rec.ks_woo_pricelist_ids = [(5, 0, 0)]
                    for currency_id in rec.ks_woo_multi_currency:
                        pricelist_id = self.env['product.pricelist'].search([('ks_instance_id', '=', rec.id),
                                                                             ('currency_id', '=', currency_id.id)])
                        if pricelist_id:
                            pricelist_price = []
                            for record in pricelist_id:
                                pricelist_price.append(record.id)
                                rec.ks_woo_pricelist_ids = [(4, record.id)]
                        else:
                            price_list_data = {
                                'name': rec.ks_name + ' ' + currency_id.name + ' Regular Pricelist',
                                'currency_id': currency_id.id,
                                'company_id': rec.ks_company.id,
                                'ks_instance_id': rec.id,
                                'ks_onsale_pricelist': False,
                            }
                            pricelist_id = self.env['product.pricelist'].create(price_list_data)
                            rec.ks_woo_pricelist_ids = [(4, pricelist_id.id)]
                            price_list_data = {
                                'name': rec.ks_name + ' ' + currency_id.name + ' OnSale Pricelist',
                                'currency_id': currency_id.id,
                                'company_id': rec.ks_company.id,
                                'ks_instance_id': rec.id,
                                'ks_onsale_pricelist': True,
                            }
                            pricelist_id = self.env['product.pricelist'].create(price_list_data)
                            rec.ks_woo_pricelist_ids = [(4, pricelist_id.id)]
                else:
                    rec.ks_woo_pricelist_ids = [(5, 0, 0)]

    def ks_manage_auto_job(self):
        if self.ks_instance_state != 'active':
            if self.ks_aio_cron_id.active:
                self.ks_aio_cron_id.active = False
            elif self.ks_aip_cron_id.active:
                self.ks_aip_cron_id.active = False
            elif self.ks_aus_cron_id.active:
                self.ks_aus_cron_id.active = False
            elif self.ks_auos_cron_id.active:
                self.ks_auos_cron_id.active = False
        if self.ks_auto_import_product:
            data = {
                'name': '[' + self.ks_id + '] - ' + self.ks_name + ': ' + 'WooCommerce Auto Product Import from Woo to Odoo (Do Not Delete)',
                'interval_number': self.ks_cron_ip_interval_number,
                'interval_type': self.ks_cron_ip_interval_type,
                'user_id': self.ks_cron_ip_schedule_user.id,
                'model_id': self.env.ref('product.model_product_template').id,
                'state': 'code',
                'active': self.ks_aip_cron_active_permission,
                'numbercall': -1,
                'ks_woo_instance_id': self.id,
                'ks_cron_type': 'auto import product'
            }
            if self.ks_aip_cron_id and self.ks_aip_update_permission:
                self.ks_aip_cron_id.write(data)
                self.ks_aip_update_permission = False
            if not self.ks_aip_cron_id:
                ks_aip_cron_id = self.env['ir.cron'].create(data)
                self.with_context({'ks_manage_auto_job': 'Do not run'}).write({'ks_aip_cron_id': ks_aip_cron_id.id})
                # self.ks_aio_cron_id = ks_aip_cron_id.id
                self.ks_aip_cron_id.write({'code': 'model.ks_auto_import_product(' + str(self.ks_aip_cron_id.id) + ')'})

        else:
            if self.ks_aip_cron_id.active:
                self.ks_aip_cron_id.active = False

        if self.ks_auto_update_stock:
            # ks_date_time_aus = fields.Datetime.now()
            # if self.ks_cron_aus_nextcall:
            #     ks_date_time_aus = self.ks_cron_aus_nextcall
            data = {
                'name': '[' + self.ks_id + '] - ' + self.ks_name + ': ' + 'WooCommerce Auto Product Stock Update from Odoo to Woo (Do Not Delete)',
                'interval_number': self.ks_cron_aus_interval_number,
                'interval_type': self.ks_cron_aus_interval_type,
                'user_id': self.ks_cron_aus_schedule_user.id,
                'model_id': self.env.ref('product.model_product_template').id,
                'state': 'code',
                'active': self.ks_aus_cron_active_permission,
                'numbercall': -1,
                'ks_woo_instance_id': self.id,
                'ks_cron_type': 'auto update stock'
            }
            if self.ks_aus_cron_id and self.ks_aus_update_permission:
                self.ks_aus_cron_id.write(data)
                self.ks_aus_update_permission = False
            if not self.ks_aus_cron_id:
                ks_aus_cron_id = self.env['ir.cron'].create(data)
                self.with_context({'ks_manage_auto_job': 'Do not run'}).write({'ks_aus_cron_id': ks_aus_cron_id.id})
                self.ks_aus_cron_id.code = 'model.ks_auto_update_stock(' + str(self.ks_aus_cron_id.id) + ')'
        else:
            if self.ks_aus_cron_id.active:
                self.ks_aus_cron_id.active = False

        if self.ks_auto_import_order:
            # ks_date_time_aio = fields.Datetime.now()
            # if self.ks_cron_aio_nextcall:
            #     ks_date_time_aio = self.ks_cron_aio_nextcall
            data = {
                'name': '[' + self.ks_id + '] - ' + self.ks_name + ': ' + 'WooCommerce Auto Order Import from Woo to Odoo (Do Not Delete)',
                'interval_number': self.ks_cron_aio_interval_number,
                'interval_type': self.ks_cron_aio_interval_type,
                'user_id': self.ks_cron_aio_schedule_user.id,
                'model_id': self.env.ref('sale.model_sale_order').id,
                'state': 'code',
                'active': self.ks_aio_cron_active_permission,
                'numbercall': -1,
                'ks_woo_instance_id': self.id,
                'ks_cron_type': 'auto import order',
            }
            if self.ks_aio_cron_id and self.ks_aio_update_permission:
                self.ks_aio_cron_id.write(data)
                self.ks_aio_update_permission = False
            if not self.ks_aio_cron_id:
                ks_aio_cron_id = self.env['ir.cron'].create(data)
                self.with_context({'ks_manage_auto_job': 'Do not run'}).write({'ks_aio_cron_id': ks_aio_cron_id.id})
                self.ks_aio_cron_id.code = 'model.ks_auto_import_order(' + str(self.ks_aio_cron_id.id) + ')'
        else:
            if self.ks_aio_cron_id.active:
                self.ks_aio_cron_id.active = False

        if self.ks_auto_update_order_status:
            # ks_date_time_auos = fields.Datetime.now()
            # if self.ks_cron_auos_nextcall:
            #     ks_date_time_auos = self.ks_cron_auos_nextcall
            data = {
                'name': '[' + self.ks_id + '] - ' + self.ks_name + ': ' + 'WooCommerce Auto Order Status Update from Odoo to Woo(Do Not Delete)',
                'interval_number': self.ks_cron_auos_interval_number,
                'interval_type': self.ks_cron_auos_interval_type,
                'user_id': self.ks_cron_auos_schedule_user.id,
                'model_id': self.env.ref('sale.model_sale_order').id,
                'state': 'code',
                'active': self.ks_auos_cron_active_permission,
                'numbercall': -1,
                'ks_woo_instance_id': self.id,
                'ks_cron_type': 'auto update order status'
            }
            if self.ks_auos_cron_id and self.ks_auos_update_permission:
                self.ks_auos_cron_id.write(data)
                self.ks_auos_update_permission = False
            if not self.ks_auos_cron_id:
                ks_auos_cron_id = self.env['ir.cron'].create(data)
                self.with_context({'ks_manage_auto_job': 'Do not run'}).write({'ks_auos_cron_id': ks_auos_cron_id.id})
                self.ks_auos_cron_id.code = 'model.ks_auto_update_order_status(' + str(self.ks_auos_cron_id.id) + ')'
        else:
            if self.ks_auos_cron_id.active:
                self.ks_auos_cron_id.active = False

    def ks_manage_auto_import_product_job(self):
        self.ks_aip_update_permission = True
        self.ks_manage_auto_job()
        return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                                   message='Auto Import Product Cron has been Successfully updated')

    def ks_manage_auto_import_order_job(self):
        self.ks_aio_update_permission = True
        self.ks_manage_auto_job()
        return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                                   message='Auto Import Order Cron has been Successfully updated')

    def ks_manage_auto_update_order_status_job(self):
        self.ks_auos_update_permission = True
        self.ks_manage_auto_job()
        return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                                   message='Auto Update Order Status Cron has been Successfully updated')

    def ks_manage_auto_update_stock_job(self):
        self.ks_aus_update_permission = True
        self.ks_manage_auto_job()
        return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                                   message='Auto Update Stock Cron has been Successfully updated')

    def _compute_count_of_woo_records(self):
        for rec in self:
            search_query = [('ks_woo_instance_id', '=', rec.id), ('ks_woo_id', '!=', False)]
            rec.ks_database_name = request.session.db
            rec.ks_current_user = self.env.user.id
            rec.ks_woo_count_orders = rec.env['sale.order'].search_count(search_query)
            rec.ks_woo_count_products = rec.env['product.template'].search_count(search_query)
            rec.ks_woo_count_coupons = rec.env['ks.woo.coupon'].search_count(search_query)
            rec.ks_woo_count_customers = rec.env['res.partner'].search_count(search_query)

    def open_form_action(self):
        view = self.env.ref('ks_woocommerce.ks_woo_instance_operation_form_view')
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommerce Operations',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_model': 'ks.woo.instance.operation',
            'view_mode': 'form',
            'context': {'default_ks_woo_instances': [(6, 0, [self.id])], 'default_woo_instance': True},
            'target': 'new',
        }

    def ks_open_woo_orders(self):
        action = self.env.ref('ks_woocommerce.action_woocommerce_sale_order').read()[0]
        action['domain'] = [('ks_woo_instance_id', '=', self.id)]
        return action

    def ks_open_woo_products(self):
        action = self.env.ref('ks_woocommerce.action_woocommerce_product_templates').read()[0]
        action['domain'] = [('ks_woo_instance_id', '=', self.id)]
        return action

    def ks_open_woo_coupons(self):
        action = self.env.ref('ks_woocommerce.action_woocommerce_coupons').read()[0]
        action['domain'] = [('ks_woo_instance_id', '=', self.id)]
        return action

    def ks_open_woo_customers(self):
        action = self.env.ref('ks_woocommerce.action_woocommerce_res_partner').read()[0]
        action['domain'] = [('ks_woo_instance_id', '=', self.id)]
        return action

    def ks_open_woo_configuration(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommerce Operations',
            'view': 'form',
            'res_id': self.id,
            'res_model': 'ks.woocommerce.instances',
            'view_mode': 'form',
        }

    def ks_open_instance_logs(self):
        action = self.env.ref('ks_woocommerce.action_woocommerce_logs').read()[0]
        action['domain'] = [('ks_woo_instance_id', '=', self.id)]
        return action

    def ks_connect_to_woo_instance(self):
        try:
            wcapi = self.ks_api_authentication()
            if wcapi.get("").status_code == 200:
                message = 'Connection Successful'
                names = 'Success'
                self.ks_instance_connected = True
                self.ks_instance_state = 'connected'
            else:
                message = (str(wcapi.get("").status_code) + ': ' + eval(wcapi.get("").text).get('message')) if len(
                    wcapi.get("").text.split(
                        "woocommerce_rest_authentication_error")) > 1 else 'Please enter the Valid WooCommerce Store URL.'
                if message == '401: Consumer key is invalid.':
                    message = "Customer Key is Invalid"
                if message == '401: Invalid signature - provided signature does not match.':
                    message = "Customer Secret Key is Invalid"
                names = 'Error'
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_status='success' if wcapi.get("").status_code in [200,
                                                                                                              201] else 'failed',
                                                         ks_type='system_status',
                                                         ks_woo_instance_id=self,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='connection',
                                                         response='Connection successful' if wcapi.get("").status_code
                                                                                             in [200,
                                                                                                 201] else message if message == 'Please enter the Valid WooCommerce Store URL.' else wcapi.get(
                                                             "").text)
        except ConnectionError:
            raise ValidationError(
                "Couldn't Connect the instance !! Please check the network connectivity or the configuration or Store "
                "URL "
                " parameters are "
                "correctly set.")
        except Exception as e:
            names = 'Error'
            message = 'Invalid WooCommerce Store URL.' if 'http' in str(
                e) else e
            self.env['ks.woo.sync.log'].ks_exception_log(record='',
                                                         type='system_status',
                                                         operation_type="connection",
                                                         instance_id=self,
                                                         operation="odoo_to_woo",
                                                         exception=message)
        return self.env['ks.message.wizard'].ks_pop_up_message(names=names, message=message)

    def ks_activate_instance(self):
        if self.ks_instance_connected and self.ks_instance_state == 'connected':
            self.ks_instance_state = 'active'
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_status='success',
                                                         ks_type='system_status',
                                                         ks_woo_instance_id=self,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='connection',
                                                         response='Activation successful')
            return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                                   message='Instance Activated')

    def ks_deactivate_instance(self):
        if self.ks_instance_connected and self.ks_instance_state == 'active':
            self.ks_instance_state = 'deactivate'
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_status='success',
                                                         ks_type='system_status',
                                                         ks_woo_instance_id=self,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='connection',
                                                         response='Deactivation successful')
            return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                                   message='Instance Deactivated')

    def ks_api_authentication(self):
        wcapi = WCAPI(
            url=self.ks_woo_store_url,
            consumer_key=self.ks_customer_key,
            consumer_secret=self.ks_customer_secret,
            wp_api=True,
            version=self.ks_wc_version,
            verify_ssl=self.ks_verify_ssl,
            timeout=50,
            query_string_auth=self.ks_auth

        )
        return wcapi

    def ks_store_record_after_export(self, odoo_record, woo_record):
        odoo_record.ks_woo_id = woo_record.get('id') or ''
        if woo_record.get('date_modified'):
            odoo_record.ks_date_updated = datetime.strptime((woo_record.get('date_modified') or False).replace('T',
                                                                                                               ' '),
                                                            DEFAULT_SERVER_DATETIME_FORMAT)
        if woo_record.get('date_created'):
            odoo_record.ks_date_created = datetime.strptime((woo_record.get('date_created') or False).replace('T',
                                                                                                              ' '),
                                                            DEFAULT_SERVER_DATETIME_FORMAT)

    def ks_store_record_after_import(self, odoo_record, woo_record, instance):
        odoo_record.ks_woo_id = woo_record.get('id') or ''
        odoo_record.ks_woo_instance_id = instance.id

    def ks_instance_status_error(self):
        return self.env['ks.message.wizard'].ks_pop_up_message(names='Error',
                                                               message="WooCommerce instance must be in "
                                                                       "active state to perform operations.")


class KsWooOrderStatus(models.Model):
    _name = 'ks.woocommerce.status'
    _description = 'WooCommerce Order Status'

    ks_woo_states = fields.Selection([('on-hold', 'On-hold'), ('pending', 'Pending'),
                                      ('processing', 'Processing'), ('completed', 'Completed')], readonly=True,
                                     string='Woo State')
    ks_sync = fields.Boolean('Sync')
    ks_odoo_state = fields.Selection([('draft', 'Quotation'), ('sale', 'Sale Order')],
                                     string='Odoo state')
    ks_create_invoice = fields.Boolean(string='Create Invoice')
    ks_set_invoice_state = fields.Selection(
        [('false', 'False'), ('draft', 'Draft'), ('open', 'Open'), ('paid', 'Paid')],
        string='Set Invoice state', default=False)
    ks_confirm_shipment = fields.Boolean(string='Confirm Shipment')
    ks_instance_id = fields.Many2one('ks.woocommerce.instances', string="WooCommerce Instance")

    @api.onchange('ks_odoo_state')
    def _onchange_ks_odoo_state(self):
        if self.ks_odoo_state == 'draft':
            self.ks_create_invoice = self.ks_confirm_shipment = False
            self.ks_set_invoice_state = 'false'

    @api.onchange('ks_create_invoice')
    def _onchnage_ks_create_invoice(self):
        if self.ks_create_invoice:
            if self.ks_odoo_state == 'draft':
                raise ValidationError('You can not create invoice if order is in Quotation State !')
        else:
            self.ks_set_invoice_state = 'false'


class ks_ir_cron_extended(models.Model):
    _inherit = 'ir.cron'

    ks_woo_instance_id = fields.Many2one('ks.woocommerce.instances')
    ks_cron_type = fields.Char()

    @api.constrains('active')
    def ks_active_inactive_(self):
        for rec in self:
            ks_instance = self.env['ks.woocommerce.instances'].browse(rec.ks_woo_instance_id.id)
            if rec.ks_cron_type == 'auto import product':
                if not rec.active:
                    ks_instance.with_context({'ks_manage_auto_job': 'Do not run'}).write({
                        'ks_aip_cron_active_permission': False
                    })
                elif rec.active:
                    ks_instance.with_context({'ks_manage_auto_job': 'Do not run'}).write({
                        'ks_aip_cron_active_permission': True
                    })
            if rec.ks_cron_type == 'auto update stock':
                if not rec.active:
                    ks_instance.with_context({'ks_manage_auto_job': 'Do not run'}).write({
                        'ks_aus_cron_active_permission': False
                    })
                elif rec.active:
                    ks_instance.with_context({'ks_manage_auto_job': 'Do not run'}).write({
                        'ks_aus_cron_active_permission': True
                    })
            if rec.ks_cron_type == 'auto update order status':
                if not rec.active:
                    ks_instance.with_context({'ks_manage_auto_job': 'Do not run'}).write({
                        'ks_auos_cron_active_permission': False
                    })
                elif rec.active:
                    ks_instance.with_context({'ks_manage_auto_job': 'Do not run'}).write({
                        'ks_auos_cron_active_permission': True
                    })
            if rec.ks_cron_type == 'auto import order':
                if not rec.active:
                    ks_instance.with_context({'ks_manage_auto_job': 'Do not run'}).write({
                        'ks_aio_cron_active_permission': False
                    })
                elif rec.active:
                    ks_instance.with_context({'ks_manage_auto_job': 'Do not run'}).write({
                        'ks_aio_cron_active_permission': True
                    })

# -- coding: utf-8 --
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models
from datetime import timedelta, time
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    sales_count_30_days = fields.Float(compute='_compute_sales_count_30_days', string='Sold 30 dd')
    sales_count_90_days = fields.Float(compute='_compute_sales_count_90_days', string='Sold 90 dd')

    # this two functions are a copy of the Odoo one, but with the days changed
    def _compute_sales_count_30_days(self):
        r = {}
        self.sales_count_30_days = 0
        if not self.user_has_groups('sales_team.group_sale_salesman'):
            return r
        date_from = fields.Datetime.to_string(
            fields.datetime.combine(fields.datetime.now() - timedelta(days=30),
                                    time.min))

        done_states = self.env['sale.report']._get_done_states()

        domain = [
            ('state', 'in', done_states),
            ('product_id', 'in', self.ids),
            ('date', '>=', date_from),
            ('custom_type', '=', 'standard'),
        ]
        for group in self.env['sale.report'].read_group(domain, ['product_id', 'product_uom_qty'],
                                                        ['product_id']):
            r[group['product_id'][0]] = group['product_uom_qty']
        for product in self:
            if not product.id:
                product.sales_count_30_days = 0.0
                continue
            product.sales_count_30_days = float_round(r.get(product.id, 0),
                                              precision_rounding=product.uom_id.rounding)
        return r

    def _compute_sales_count_90_days(self):
        r = {}
        self.sales_count_90_days = 0
        if not self.user_has_groups('sales_team.group_sale_salesman'):
            return r
        date_from = fields.Datetime.to_string(
            fields.datetime.combine(fields.datetime.now() - timedelta(days=90),
                                    time.min))

        done_states = self.env['sale.report']._get_done_states()

        domain = [
            ('state', 'in', done_states),
            ('product_id', 'in', self.ids),
            ('date', '>=', date_from),
            ('custom_type', '=', 'standard'),
        ]
        for group in self.env['sale.report'].read_group(domain, ['product_id', 'product_uom_qty'],
                                                        ['product_id']):
            r[group['product_id'][0]] = group['product_uom_qty']
        for product in self:
            if not product.id:
                product.sales_count_90_days = 0.0
                continue
            product.sales_count_90_days = float_round(r.get(product.id, 0),
                                              precision_rounding=product.uom_id.rounding)
        return r

    # we inherit the Odoo function to add in the domain ('custom_type', '=', 'standard')
    def _compute_sales_count(self):
        res = super(ProductProduct, self)._compute_sales_count()

        r = {}
        self.sales_count = 0
        if not self.user_has_groups('sales_team.group_sale_salesman'):
            return r
        date_from = fields.Datetime.to_string(
            fields.datetime.combine(fields.datetime.now() - timedelta(days=365),
                                    time.min))

        done_states = self.env['sale.report']._get_done_states()

        domain = [
            ('state', 'in', done_states),
            ('product_id', 'in', self.ids),
            ('date', '>=', date_from),
            ('custom_type', '=', 'standard'), # todo Kevin: nell'analisi ha scritto di mettere il tipo vision_account, ma nel progetto c'è scritto standard
        ]
        for group in self.env['sale.report'].read_group(domain, ['product_id', 'product_uom_qty'],
                                                        ['product_id']):
            r[group['product_id'][0]] = group['product_uom_qty']
        for product in self:
            if not product.id:
                product.sales_count = 0.0
                continue
            product.sales_count = float_round(r.get(product.id, 0),
                                              precision_rounding=product.uom_id.rounding)
        return r

    def action_view_sales(self):
        action = super(ProductProduct, self).action_view_sales()
        action['context']['search_default_standard'] = 1
        return action

    # this two functions are a copy of the Odoo one, but with the days changed and the new filter added
    def action_view_sales_30_days(self):
        action = self.env.ref('sale.report_all_channels_sales_action').read()[0]
        action['domain'] = [('product_id', 'in', self.ids)]
        action['context'] = {
            'pivot_measures': ['product_uom_qty'],
            'active_id': self._context.get('active_id'),
            'search_default_Sales': 1,
            'search_default_standard': 1,
            'active_model': 'sale.report',
            'time_ranges': {'field': 'date', 'range': 'last_30_days'},
        }
        return action

    def action_view_sales_90_days(self):
        action = self.env.ref('sale.report_all_channels_sales_action').read()[0]
        action['domain'] = [('product_id', 'in', self.ids)]
        action['context'] = {
            'pivot_measures': ['product_uom_qty'],
            'active_id': self._context.get('active_id'),
            'search_default_Sales': 1,
            'search_default_standard': 1,
            'search_default_last_90_days': 1,
            'active_model': 'sale.report',
        }
        return action

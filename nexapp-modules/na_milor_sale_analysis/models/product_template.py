# -- coding: utf-8 --
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sales_count_30_days = fields.Float(compute='_compute_sales_count_30_days', string='Sold 30 dd')
    sales_count_90_days = fields.Float(compute='_compute_sales_count_90_days', string='Sold 90 dd')

    # this two functions are a copy of the Odoo one, but with the days changed
    @api.depends('product_variant_ids.sales_count_30_days')
    def _compute_sales_count_30_days(self):
        for product in self:
            product.sales_count_30_days = float_round(sum([p.sales_count_30_days for p in product.with_context(
                active_test=False).product_variant_ids]), precision_rounding=product.uom_id.rounding)

    @api.depends('product_variant_ids.sales_count_90_days')
    def _compute_sales_count_90_days(self):
        for product in self:
            product.sales_count_90_days = float_round(sum([p.sales_count_90_days for p in product.with_context(
                active_test=False).product_variant_ids]), precision_rounding=product.uom_id.rounding)

    def action_view_sales(self):
        action = super(ProductTemplate, self).action_view_sales()
        action['context']['search_default_standard'] = 1
        return action

    # this two functions are a copy of the Odoo one, but with the days changed and the new filter added
    def action_view_sales_30_days(self):
        action = self.env.ref('sale.report_all_channels_sales_action').read()[0]
        action['domain'] = [('product_tmpl_id', 'in', self.ids)]
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
        action['domain'] = [('product_tmpl_id', 'in', self.ids)]
        action['context'] = {
            'pivot_measures': ['product_uom_qty'],
            'active_id': self._context.get('active_id'),
            'search_default_Sales': 1,
            'search_default_standard': 1,
            'search_default_last_90_days': 1,
            'active_model': 'sale.report',
        }
        return action

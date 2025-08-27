# -- coding: utf-8 --
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import fields, models, _, api
from odoo.tools.safe_eval import safe_eval


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    exported = fields.Char(string='Exported', default=False, copy=False)

    def manage_feed_data(self):
        reexport = self.env.context.get('reexport', False)
        # afterward verify that there is a logistic type environment,
        # if there is not then it is useless to continue with the function
        logistic_env = self.env['na.api.sync.env'].search([('api_type', '=', 'logistic')])
        # TODO for now these configurations are only used for exporting
        # checks that the stock picking fits the domain set in the input configuration
        input_config = logistic_env.forecast_goods
        domain = [('id', '=', self.id), ('exported', '=', False)] if not reexport \
            else [('id', '=', self.id), ('exported', '=', True)]
        input_domain = input_config.record_domain
        if input_domain:
            domain = domain + safe_eval(input_domain)
        # if it is valid then proceed with the export or import based on the configurations
        valid_stock_picking = self.search(domain)
        if valid_stock_picking:
            input_config.management_data_feed([valid_stock_picking.id])
            if input_config.type == 'export_feed':
                valid_stock_picking.exported = True
        # checks that the stock picking fits the domain set in the output configuration
        output_config = logistic_env.goods_delivery
        domain = [('id', '=', self.id), ('exported', '=', False)] if not reexport \
            else [('id', '=', self.id), ('exported', '=', True)]
        output_domain = output_config.record_domain
        if output_domain:
            domain = domain + safe_eval(output_domain)
        # if it is valid then proceed with the export or import based on the configurations
        valid_stock_picking = self.search(domain)
        if valid_stock_picking:
            output_config.management_data_feed([valid_stock_picking.id])
            if output_config.type == 'export_feed':
                valid_stock_picking.exported = True


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_confirm(self, merge=True, merge_into=False):
        res = super()._action_confirm(merge, merge_into)
        try:
            if not self.env.context.get('block_feed', False):
                self.picking_id.manage_feed_data()
        except:
            pass
        return res

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('block_feed', False) and vals.get('picking_id'):
            for picking in self.picking_id:
                picking.manage_feed_data()
        return res

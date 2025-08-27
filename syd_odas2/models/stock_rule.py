# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, SUPERUSER_ID


class StockRule(models.Model):
    _inherit = 'stock.rule'

    # INFO: In case of POs grouped by product, code below will be performed only first time.
    def _prepare_purchase_order(self, company_id, origins, values):
        result = super(StockRule, self)._prepare_purchase_order(company_id, origins, values)

        # INFO: as it's done in _prepare_purchase_order (addons\purchase_requisition_stock\models\stock.py).
        #       Probably 'values' it was not meant to be an array of values.
        values = values[0]

        origin_sale_line_id = values.get('origin_sale_line_id')
        if origin_sale_line_id:
            # INFO: sudoing to avoid multi company issue.
            so = self.env['sale.order.line'].browse(origin_sale_line_id).order_id.sudo()
            so = so.from_as2 and so or so.commercehub_sale_order_id
            result.update({
                'commercehub_sale_order_id': so.id,
                'commercehub_po': so.commercehub_po,
                'commercehub_co': so.commercehub_co,
                'as2_stream_id': so.as2_stream_id.id
            })
        return result

    # INFO: In case of POs grouped by product, only code below will be performed if a PO already exists.
    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, po):
        result = super(StockRule, self)._prepare_purchase_order_line(product_id, product_qty, product_uom, company_id, values, po)

        origin_sale_line_id = values.get('origin_sale_line_id')
        if origin_sale_line_id:
            # INFO: sudoing to avoid multi company issue.
            so = self.env['sale.order.line'].browse(origin_sale_line_id).order_id.sudo()
            so = so.from_as2 and so or so.commercehub_sale_order_id
            result.update({
                'commercehub_sale_order_id': so.id,
                'commercehub_po': so.commercehub_po,
                'commercehub_co': so.commercehub_co,
                'as2_stream_id': so.as2_stream_id.id
            })
        return result

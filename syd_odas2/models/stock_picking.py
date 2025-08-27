# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    commercehub_sale_order_id = fields.Many2one('sale.order', compute="_compute_commercehub_sale_order_id")
    commercehub_po = fields.Char('CommerceHub PO', compute="_compute_commercehub_po", store=True)
    commercehub_co = fields.Char('CommerceHub CO', compute="_compute_commercehub_co", store=True)

    as2_stream_id = fields.Many2one('odas2.stream', compute="_compute_as2_stream_id", store=True)

    @api.depends('origin_sale_line_id', 'origin_purchase_line_id')
    def _compute_commercehub_sale_order_id(self):
        for rec in self:
            rec.commercehub_sale_order_id = rec.origin_purchase_line_id.commercehub_sale_order_id or \
                                            rec.origin_sale_line_id.commercehub_sale_order_id or \
                                            rec.origin_sale_line_id.order_id  # INFO: if line direct from a CHub SO (in
                                                                              # this case commercehub_sale_order_id is
                                                                              # empty and we go for order_id).


    @api.depends('origin_sale_line_id', 'origin_purchase_line_id')
    def _compute_as2_stream_id(self):
        for rec in self:
            rec.as2_stream_id = rec.origin_purchase_line_id.as2_stream_id or \
                                rec.origin_sale_line_id.as2_stream_id

    @api.depends('origin_sale_line_id', 'origin_purchase_line_id')
    def _compute_commercehub_po(self):
        for rec in self:
            rec.commercehub_po = rec.origin_purchase_line_id.commercehub_po or rec.origin_sale_line_id.commercehub_po

    @api.depends('origin_sale_line_id', 'origin_purchase_line_id')
    def _compute_commercehub_co(self):
        for rec in self:
            rec.commercehub_co = rec.origin_purchase_line_id.commercehub_co or rec.origin_sale_line_id.commercehub_co


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    picking_type_sequence = fields.Integer('Type Sequence',related="picking_type_id.sequence",store=True)

    def action_download_packingslips_pdf(self):
        # TODO: filter sale orders by from_as2 too.
        return self.move_lines.mapped('commercehub_sale_order_id').sudo().action_download_packingslips_pdf()

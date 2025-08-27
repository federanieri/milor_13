# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _name = 'purchase.order.line'
    _inherit = ['purchase.order.line', 'odas2.stream.mixin']
    # _inherit = 'purchase.order.line'

    commercehub_sale_order_id = fields.Many2one('sale.order', ondelete='set null')
    commercehub_po = fields.Char('CommerceHub PO')
    commercehub_co = fields.Char('CommerceHub CO')


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'odas2.stream.mixin']
    # _inherit = 'purchase.order'

    # INFO: link to the original commercehub SO (e.g. when a SO is created because of inter-company operation).
    commercehub_sale_order_id = fields.Many2one('sale.order', ondelete='set null')
    commercehub_po = fields.Char('CommerceHub PO')
    commercehub_co = fields.Char('CommerceHub CO')
    cancel_request = fields.Boolean('Richiesta di Cancellazione', tracking=True)
    cancel_request_processed = fields.Boolean('Richiesta di cancellazione per ordine già evaso', tracking=True)

    @api.constrains('cancel_request','cancel_request_processed')
    def function_cancel_request(self):
        if self.commercehub_po and not self._context.get('done',None):
            self = self.with_context(done=True)
            orders = list(self.sudo().search([('commercehub_po','=',self.commercehub_po),('id','!=',self.id)])) + list(self.env['sale.order'].sudo().search([('commercehub_po','=',self.commercehub_po)]))
            for order in orders:
                order.cancel_request = self.cancel_request
                order.cancel_request_processed = self.cancel_request_processed

    def _prepare_sale_order_data(self, name, partner, company, direct_delivery_address):
        result = super(PurchaseOrder, self)._prepare_sale_order_data(name, partner, company, direct_delivery_address)
        # INFO: in case of an inter-company commercehub SO creation then set commercehub SO origin fields.
        if self.commercehub_sale_order_id:
            result.update({
                'commercehub_sale_order_id': self.commercehub_sale_order_id.id,
                'commercehub_po': self.commercehub_sale_order_id.commercehub_po,
                'commercehub_co': self.commercehub_sale_order_id.commercehub_co,
                'source_id': self.commercehub_sale_order_id.as2_stream_id.source_id.id,
                'as2_stream_id': self.commercehub_sale_order_id.as2_stream_id.id
            })
        return result

    @api.model
    def _prepare_sale_order_line_data(self, line, company, sale_id):
        result = super(PurchaseOrder, self)._prepare_sale_order_line_data(line, company, sale_id)
        result.update({
            'commercehub_sale_order_id': line.commercehub_sale_order_id.id,
            'commercehub_po': line.commercehub_sale_order_id.commercehub_po,
            'commercehub_co': line.commercehub_sale_order_id.commercehub_co,
            'as2_stream_id': line.commercehub_sale_order_id.as2_stream_id.id
        })
        return result

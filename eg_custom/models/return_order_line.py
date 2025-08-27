from odoo import models, api


class ReturnOrderLine(models.Model):
    _inherit = 'return.order.line'

    @api.model
    def create(self, vals):
        res = super(ReturnOrderLine, self).create(vals)
        if not res.origin_invoice_id:
            if bool(res.product_id) and bool(res.return_order_sheet_id.partner_id.commercial_partner_id):
                res.origin_invoice_id = res.env['account.move'].search(
                    [('invoice_line_ids.product_id', '=', res.product_id.id), (
                        'partner_id', '=', res.return_order_sheet_id.partner_id.commercial_partner_id.id),
                     ('state', '=', 'posted')], limit=1).id
            elif bool(res.origin_sale_order_line_id):
                res.origin_invoice_id = res.origin_saleorder_id.invoice_ids.ids[0]
            else:
                res.origin_invoice_id = False
        return res

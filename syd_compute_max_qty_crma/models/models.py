from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import groupby as groupbyelem
from operator import itemgetter
    
class ReturnOrderSheet(models.Model):
    _inherit = 'return.order.sheet'

    @api.constrains('state')
    def _check_state_confirm(self):
        for crma in self:
            if crma.state == 'confirm':
                for lines in [self.env['return.order.line'].concat(*g) for k, g in groupbyelem(self.return_order_line_ids.filtered(lambda x: x.origin_invoice_id), itemgetter('product_id','origin_invoice_id'))]:
                    resto = False
                    qty_to_return = sum(lines.mapped('quantity'))
                    total_qty = sum(lines.origin_invoice_id.invoice_line_ids.filtered(lambda x: x.product_id == lines.product_id).mapped('quantity'))
                    for invoice_line in lines.origin_invoice_id.invoice_line_ids.filtered(lambda x: x.product_id == lines.product_id):
                        if qty_to_return > 0:
                            qty = (qty_to_return if invoice_line.quantity >= qty_to_return else invoice_line.quantity)
                            invoice_line.qty_max_crma -= qty
                            qty_to_return -= qty

            if crma.state == 'cancel':
                for lines in [self.env['return.order.line'].concat(*g) for k, g in groupbyelem(self.return_order_line_ids.filtered(lambda x: x.origin_invoice_id), itemgetter('product_id','origin_invoice_id'))]:
                    qty_to_give_back = sum(lines.mapped('quantity'))
                    total_qty = sum(lines.origin_invoice_id.invoice_line_ids.filtered(lambda x: x.product_id == lines.product_id).mapped('quantity'))
                    for invoice_line in lines.origin_invoice_id.invoice_line_ids.filtered(lambda x: x.product_id == lines.product_id):
                        if qty_to_give_back > 0:
                            qty = (qty_to_give_back if invoice_line.quantity >= qty_to_give_back else invoice_line.quantity)
                            invoice_line.qty_max_crma += qty
                            qty_to_give_back -= qty

class ReturnOrderLine(models.Model):
    _inherit = 'return.order.line'

    @api.constrains('quantity')
    def _check_qty_to_return(self):
        for return_lines in [self.browse().concat(*g) for k, g in groupbyelem(self.filtered(lambda x: x.origin_invoice_id), itemgetter('product_id','origin_invoice_id'))]:
            invoice_lines = return_lines.origin_invoice_id.invoice_line_ids.filtered(lambda x: x.product_id == return_lines.product_id)
            if sum(invoice_lines.mapped('qty_max_crma')) == 0:
                raise ValidationError(_("You can't return any quantity of the product: %s. Please modify it." % (return_lines.product_id.name)))
            elif sum(return_lines.mapped('quantity')) > sum(invoice_lines.mapped('qty_max_crma')):
                raise ValidationError(_("You can't return more than %d quantity of the product: %s. Please modify it." % (sum(invoice_lines.mapped('qty_max_crma')), return_lines.product_id.name)))
    

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    qty_max_crma = fields.Float(string="Qty. Max CRMA")
    
class AccountMove(models.Model):
    _inherit = 'account.move'  
    
    @api.constrains('state')
    def _set_max_crma(self):
        for invoice in self:
            if invoice.state == 'posted':
                for line in invoice.invoice_line_ids:
                    line.qty_max_crma = line.quantity
                    
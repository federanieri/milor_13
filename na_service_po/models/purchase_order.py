# -*- encoding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    sequence_child = fields.Integer('Child Sequence', default=1, copy=False)

    # overwrite the function because it is no longer needed for the new flow of the child PO
    @api.onchange('parent_po_id')
    def _autopopolate(self):
        return False

    def create_purchase_order_line_from_parent(self):
        # delete all the child order lines
        for child_order_line in self.order_line:
            child_order_line.unlink()

        # add the parent order lines
        for parent_order_line in self.parent_po_id.order_line:
            self.env['purchase.order.line'].create(
                {
                    'order_id': self.id,
                    'product_template_id': parent_order_line.product_template_id.id,
                    'product_id': parent_order_line.product_id.id,
                    'product_of_service_id': parent_order_line.product_of_service_id.id,
                    'name': parent_order_line.name,
                    'product_qty': parent_order_line.product_qty,
                    'product_uom_qty': parent_order_line.product_uom_qty,
                    'product_uom': parent_order_line.product_uom.id,
                    'price_unit': 0,
                    'taxes_id': [(6, 0, parent_order_line.taxes_id.ids)],
                    'display_type': parent_order_line.display_type,
                    'date_planned': parent_order_line.date_planned,
                }
            )

    def action_view_child_po_ids(self):
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        action['domain'] = [('parent_po_id', '=', self.id)]
        action['context'] = {
            # 'active_id': self._context.get('active_id'),
            'active_model': 'purchase.order',
        }
        return action

    def button_confirm(self, pass_check=False):
        if not pass_check:
            for order in self:
                for line in order.order_line:
                    if line.price_unit == 0 and not line.display_type:
                        return {
                            'name': _('Confirm Order'),
                            'res_model': 'confirm.purchase.order',
                            'view_mode': 'form',
                            'context': {'active_id': self.id},
                            'view_id': self.env.ref('na_service_po.view_confirm_purchase_order_check').id,
                            'target': 'new',
                            'type': 'ir.actions.act_window',
                        }

        return super(PurchaseOrder, self).button_confirm()

    @api.model
    def create(self, vals):
        # if the order has a parent set the name with the children sequence
        if vals.get('parent_po_id'):
            parent_order = self.env['purchase.order'].search([('id', '=', vals['parent_po_id'])])
            if not parent_order:
                raise UserError(_("The parent order doesn't exist"))
            vals['name'] = parent_order.name + '/C' + str(parent_order.sequence_child)
            parent_order.sequence_child += 1

        res = super(PurchaseOrder, self).create(vals)
        if res.parent_po_id:
            res.create_purchase_order_line_from_parent()
        return res

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        # check if the flag closed is a value assigned now,
        # if it is not assigned or if it is assigned false, we don't have to change anything
        if vals.get('closed', ''):
            for child_order in self.child_po_ids:
                # if the child, has other child then they will hava their closed set as True
                child_order.closed = True
        return res

    def button_cancel(self):
        for order in self:
            for child_order in order.child_po_ids:
                # if the child state isn't cancel, you can't cancel the parent
                if child_order.state != 'cancel':
                    raise UserError(
                        _("You can not cancel an order if it has children orders not cancelled"))

        return super(PurchaseOrder, self).button_cancel()

    def unlink(self):
        for order in self:
            if order.child_po_ids:
                raise UserError(_('You can not delete an order if it has children orders'))
        return super(PurchaseOrder, self).unlink()

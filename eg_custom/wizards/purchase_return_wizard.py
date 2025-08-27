from odoo import fields, models


class PurchaseReturnWizard(models.TransientModel):
    _name = 'purchase.return.wizard'
    _description = 'Purchase Return Wizard'

    vendor_return_reason_id = fields.Many2one(comodel_name='vendor.return.reason')

    def purchase_create_return_order(self):
        """
        Rework Button Click when Create Return Order and Create Duplicate Picking Order
        :return:
        """
        purchase_order_id = self.env['purchase.order'].browse(self.env.context['active_id'])
        purchase_order_id.write({
            'vendor_return_reason_id': self.vendor_return_reason_id.id,
            'closed': False,
        })
        move_list = []
        picking_ids = purchase_order_id.picking_ids
        if len(picking_ids) == 1:
            picking_id = picking_ids
        else:
            picking_id = picking_ids.filtered(lambda picking_id: picking_id.rework_state == 'rework_one')
        for move_id in picking_id.move_lines:
            move_to_unreserve_ids = move_id.move_dest_ids.filtered(lambda m: m.state not in ["done", "cancel"])
            move_to_unreserve_ids._do_unreserve()
            move_list.append((0, 0, {
                'product_id': move_id.product_id.id,
                'quantity': move_id.quantity_done,
                'uom_id': move_id.product_uom.id,
                'to_refund': True,
            }))

        stock_return_picking_id = self.env['stock.return.picking'].create({
            'picking_id': picking_id.id,
            'location_id': self.env.company.default_return_location_id.id,
            'product_return_moves': move_list,
        })
        stock_return_picking_id._onchange_picking_id()
        stock_return_picking_id.create_returns()
        duplicate_created_picking_id = picking_id.sudo().copy_origins_dests()
        duplicate_created_picking_id.action_confirm()
        self.send_purchase_email_rework(purchase_order_id)
        # set Purchase Rework One or Rework Two
        if picking_id.rework_state == 'rework_one':
            purchase_order_id.purchase_order_type = 'rework_two'
            duplicate_created_picking_id.rework_state = 'rework_two'
        else:
            purchase_order_id.purchase_order_type = 'rework_one'
            duplicate_created_picking_id.rework_state = 'rework_one'
        return True

    def send_purchase_email_rework(self, purchase_id):
        template_id = self.env.ref('eg_custom.email_template_for_purchase_rework')
        template_id.send_mail(purchase_id.id, force_send=True)

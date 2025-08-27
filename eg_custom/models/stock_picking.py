from odoo import models, fields, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    bulk_validate = fields.Boolean(string='Abilita Validazione Massiva',
                                   related='picking_type_id.bulk_validate')
    rework_state = fields.Selection([('rework_one', 'Rework 1'), ('rework_two', 'Rework 2')], string='Rework Type',
                                    copy=False)

    def get_barcode_view_state(self):
        """ Return the initial state of the barcode view as a dict.
        """
        pickings = super(StockPicking, self).get_barcode_view_state()
        for picking in pickings:
            picking['actionReportBarcodesSmallQVCZplId'] = self.env.ref(
                'eg_custom.label_product_picking_qvc_code_zpl_small_new').id
        return pickings

    def action_mass_validation(self):
        """
        action server for mass validate transfer based on operation type inner boolean condition
        :return:
        """
        self._check_company()
        pickings = self.filtered(lambda x: x.bulk_validate)
        if any(picking.state not in ('assigned') for picking in pickings):
            raise UserError(_(
                'Some transfers are still waiting for goods. Please check or force their availability before setting this batch to done.'))
        picking_without_qty_done = self.env['stock.picking']
        picking_to_backorder = self.env['stock.picking']
        for picking in pickings:
            if all([x.qty_done == 0.0 for x in picking.move_line_ids]):
                # If no lots when needed, raise error
                picking_type = picking.picking_type_id
                if (picking_type.use_create_lots or picking_type.use_existing_lots):
                    for ml in picking.move_line_ids:
                        if ml.product_id.tracking != 'none':
                            raise UserError(_('Some products require lots/serial numbers.'))
                # Check if we need to set some qty done.
                picking_without_qty_done |= picking
            elif picking._check_backorder():
                picking_to_backorder |= picking
            else:
                picking.action_done()
        if picking_without_qty_done:
            view = self.env.ref('stock.view_immediate_transfer')
            wiz = self.env['stock.immediate.transfer'].create({
                'pick_ids': [(4, p.id) for p in picking_without_qty_done],
                'pick_to_backorder_ids': [(4, p.id) for p in picking_to_backorder],
            })
            return {
                'name': _('Immediate Transfer?'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'stock.immediate.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }
        if picking_to_backorder:
            return picking_to_backorder.action_generate_backorder_wizard()
        # Change the state only if there is no other action (= wizard) waiting.
        # return True

    def do_print_report_picking_complete_new(self):
        """
        method to update dates from action print
        :return:
        """
        self.write({'printed': True, 'date_printed': fields.Datetime.now(), 'user_printed_id': self.env.user.id})
        return self.env.ref('eg_custom.action_report_delivery').report_action(self)

# -*- coding: utf-8 -*-
from odoo import fields, models


class NaPurchase(models.TransientModel):
    _name = 'na.purchase'

    complete_transfers = fields.Date(string="Completa trasferimenti degli acquisti precedenti al", required=1)

    def complete_button(self):
        po = self.env['purchase.order'].search([('closed', '=', True), ('date_approve', '<', self.complete_transfers),
                                                ('state', 'in', ['purchase', 'done'])])

        for p in po:  # cycle for purchase order
            for pu in p.total_picking_ids:  # cycle for stock picking
                for m in pu.move_ids_without_package:  # cycle for all movements in stock.picking
                    if m.state not in ('done', 'cancel'):
                        m.state = 'done'
                if pu.state not in ('done', 'cancel'):
                    pu.state = 'done'

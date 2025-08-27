from odoo import models, fields, api, _, registry

import os
import sys

import logging
_logger = logging.getLogger(__name__)


class CommercehubOrder(models.Model):
    _name = 'order_table.commercehub_order'
    _description = "Commercehub Order"
    
    name = fields.Char('SO Milor Group', related='mg_so_name')
    mg_so_id = fields.Integer('SO Id')
    mg_so_name = fields.Char('Sale Order')
    mg_po_name = fields.Char('PO Milor Group')
    ms_so_id = fields.Char('SO Milor Spa Id')
    ms_so_name = fields.Char('SO Milor Spa')
    ms_po_id = fields.Integer('PO Milor Spa Id')
    ms_po_name = fields.Char('PO Milor Spa')
    commercehub_po = fields.Char('CH PO')
    commercehub_co = fields.Char('CH CO')
    state = fields.Selection([
                               ('customer','Spedito a Cliente'),
                               ('milor_group','In Magazzino America'),
                               ('sent_milor_group','Spedito a Milor Group'),
                               ('milor_spa','In Magazzino Milano'),
                               ('vendor','Da ricevere fornitore'),
                               ('error', 'Error'),
                               ('completed', 'Completed'),
                               ('in_stock', 'Prodotti di Magazzino'),
                               ('cancelled', 'Cancellato'),
                               ('cancel_request', 'Richiesta di Cancellazione'),
                               ('rework', 'Rework'),
                               ('undefined', 'Non Definito'),
                               ('cancelled_completed', 'Cancellato & Completato'),
                               ('in_transit', 'In Transito'),
                               ],
                              default = 'vendor'
                              )
    vendor_name = fields.Char(string="Fornitore")
    data_spedizione = fields.Datetime(string="Sped. Cliente")
    data_spedizione_group = fields.Datetime(string="Sped. Milor Group")
    date_approve = fields.Datetime(string="Data Confirm PO")
    date_planned_spa = fields.Datetime(string="Ric. Fornitore")
    date_planned_group = fields.Datetime(string="Ric. Milor Group")
    order_date = fields.Datetime(string="Data Ordine")
    as2_state = fields.Selection([('warning', 'Warning'), ('error', 'Error')])
    as2_state_reason = fields.Char(default='')
    last_update_to_as2 = fields.Datetime(string='Last Update To AS2')
    custom_value = fields.Char('Custom Value')
    product_name = fields.Text('Product')
    product_display_name = fields.Text('Product Name')
    without_mto = fields.Boolean('Without MTO')
    qvc_code = fields.Char('Codice QVC')
    
    @api.model
    def _init(self, automatic=True):
        self = self.sudo()
        icpSudo = self.env['ir.config_parameter'].sudo()
        milor_spa_id = int(icpSudo.get_param('eg_custom.milor_spa_id'))

        if automatic:
            cr = registry(self._cr.dbname).cursor()
            self = self.with_env(self.env(cr=cr))

        self.search([('state', 'not in', ['completed', 'cancelled_completed'])]).unlink()
        if automatic:
            self.env.cr.commit()

        chub_orders = self.search([])
        try:
            orders = self.env['sale.order'].sudo().search([
                ('from_as2', '=', True),
                ('state', 'in', ['sale', 'done', 'cancel', 'draft']),
                ('id', 'not in', chub_orders.mapped('mg_so_id'))
            ])
            for as2_order in orders:
                state = 'undefined'

                milor_spa_so = False
                milor_spa_po = False

                state_set = False

                milor_group_po = self.sudo().get_po_from_so(as2_order)
                if milor_group_po:
                    milor_spa_so = self.env['sale.order'].sudo().search([('auto_purchase_order_id', '=', milor_group_po.id)], limit=1)
                    if milor_spa_so:
                        milor_spa_po = self.sudo().get_po_from_so(milor_spa_so)

                        # if milor_spa_po.cancel_request:
                        #     state = 'cancel_request'

                        # if milor_spa_po.cancel_request:
                        #     state = 'cancel_request'

                        if milor_spa_po:
                            if milor_spa_po.state == 'purchase' and milor_spa_po.received_status == 'to_receive' and not (milor_spa_po.spedito_da_fornitore or milor_spa_po.spedito_in_galvanica) and milor_spa_po.purchase_order_type in ['personalized']:
                                if state_set:
                                    _logger.info('State already set for as2_order %s (prev: %s, next: %s)' % (as2_order, state, 'vendor'))
                                state = 'vendor'
                                state_set = True

                            if milor_spa_po.state == 'purchase' and milor_spa_po.received_status == 'to_receive' and (milor_spa_po.spedito_da_fornitore or milor_spa_po.spedito_in_galvanica) and milor_spa_po.purchase_order_type in ['personalized']:
                                if state_set:
                                    _logger.info('State already set for as2_order %s (prev: %s, next: %s)' % (as2_order, state, 'in_transit'))
                                state_set = True
                                state = 'in_transit'

                            if milor_spa_po.commercehub_po is not False and milor_spa_po.state == 'purchase' and milor_spa_po.received_status == 'to_receive' and milor_spa_po.purchase_order_type in ['rework_one', 'rework_two'] and milor_spa_po.company_id.id == milor_spa_id:
                                if state_set:
                                    _logger.info('State already set for as2_order %s (prev: %s, next: %s)' % (as2_order, state, 'rework'))
                                state_set = True
                                state = 'rework'

                            if milor_spa_po.received_status == 'received':
                                if state_set:
                                    _logger.info('State already set for as2_order %s (prev: %s, next: %s)' % (as2_order, state, 'milor_spa'))
                                state_set = True
                                state = 'milor_spa'

                        if milor_spa_so.delivery_status == 'delivered':
                            if state_set:
                                _logger.info('State already set for as2_order %s (prev: %s, next: %s)' % (as2_order, state, 'sent_milor_group'))
                            state_set = True
                            state = 'sent_milor_group'

                        if milor_group_po.received_status == 'received':
                            if state_set:
                                _logger.info('State already set for as2_order %s (prev: %s, next: %s)' % (as2_order, state, 'milor_group'))
                            state_set = True
                            state = 'milor_group'

                        if not milor_spa_po:
                            if not self.env.ref('stock.route_warehouse0_mto').id in milor_spa_so.order_line.product_id.route_ids.ids:
                                if state_set:
                                    _logger.info('State already set for as2_order %s (prev: %s, next: %s)' % (as2_order, state, 'in_stock'))
                                state_set = True
                                state = 'in_stock'

                        if milor_spa_so.state == 'cancel':
                            if state_set:
                                _logger.info('State already set for as2_order %s (prev: %s, next: %s)' % (as2_order, state, 'cancelled'))
                            state_set = True
                            state = 'cancelled'

                if as2_order.as2_state == 'error':
                    if state_set:
                        _logger.info('State already set for as2_order %s (prev: %s, next: %s)' % (as2_order, state, 'error'))
                    state_set = True
                    state = 'error'

                elif as2_order.state == 'cancel':
                    if state_set:
                        _logger.info('State already set for as2_order %s (prev: %s, next: %s)' % (as2_order, state, 'cancelled'))
                    state_set = True
                    state = 'cancelled'
                    if as2_order.last_update_to_as2:
                        if state_set:
                            _logger.info('State already set for as2_order %s (prev: %s, next: %s)' % (as2_order, state, 'cancelled_completed'))
                        state_set = True
                        state = 'cancelled_completed'

                elif as2_order.delivery_status == 'delivered':
                    if state_set:
                        _logger.info('State already set for as2_order %s (prev: %s, next: %s)' % (as2_order, state, 'customer'))
                    state_set = True
                    state = 'customer'
                    if as2_order.last_update_to_as2:
                        if state_set:
                            _logger.info('State already set for as2_order %s (prev: %s, next: %s)' % (as2_order, state, 'completed'))
                        state_set = True
                        state = 'completed'

                self.create([{
                             'mg_so_id':as2_order.id,
                             'mg_so_name':as2_order.name,
                             'mg_po_name':milor_group_po.name if milor_group_po else False,
                             'ms_so_id':milor_spa_so.id if milor_spa_so else False,
                             'ms_so_name':milor_spa_so.name if milor_spa_so else False,
                             'ms_po_id':milor_spa_po.id if milor_spa_po else False,
                             'ms_po_name':milor_spa_po.name if milor_spa_po else False,
                             'as2_state':as2_order.as2_state,
                             'as2_state_reason':as2_order.as2_state_reason,
                             'last_update_to_as2':as2_order.last_update_to_as2,
                             'data_spedizione':as2_order.effective_date if as2_order else False,
                             'order_date':as2_order.date_order if as2_order else False,
                             'date_approve':milor_spa_po.date_approve if milor_spa_po else False,
                             'commercehub_po':as2_order.commercehub_po,
                             'commercehub_co':as2_order.commercehub_co,
                             'state':state,
                             'date_planned_group':milor_group_po.date_planned if milor_group_po else False,
                             'date_planned_spa':milor_spa_po.date_planned if milor_spa_po else False,
                             'vendor_name':milor_spa_po.partner_id.name if milor_spa_po else False,
                             'data_spedizione_group':milor_spa_so.effective_date if milor_spa_so else False,
                             'custom_value': ' - '.join([ol.custom_value for ol in milor_spa_so.order_line.filtered(lambda x: x.custom_value)]) if milor_spa_so else False,
                             'product_name': ' \ '.join([ol.product_id.default_code for ol in milor_spa_so.order_line.filtered(lambda x: x.product_id)]) if milor_spa_so else False,
                             'product_display_name': ' \ '.join([ol.product_id.name for ol in milor_spa_so.order_line.filtered(lambda x: x.product_id)]) if milor_spa_so else False,
                             'qvc_code': ' \ '.join([ol.product_id.product_tmpl_id.qvc_code for ol in milor_spa_so.order_line.filtered(lambda x: x.product_id)]) if milor_spa_so else False,
                             'without_mto':(not self.env.ref('stock.route_warehouse0_mto').id in milor_spa_so.order_line.product_id.route_ids.ids) if milor_spa_so else False
                             }])
                if automatic:
                    self.env.cr.commit()
        except Exception as e:
            _logger.error('Exception %s' % str(e))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            _logger.error('Exception %s (at %s/%s)' % (str(e), fname, exc_tb.tb_lineno))
            if automatic:
                self.env.cr.rollback()
        finally:
            if automatic:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return True

    def get_po_from_so(self,order):
        for p in order.picking_ids:
            for m in p.move_lines:
                if m.created_purchase_line_id:
                    return m.created_purchase_line_id.order_id
        order = self.env['purchase.order'].sudo().search([('origin','ilike',order.name)],limit=1)
        if order:
            return order
        return False

    def view_so(self):
        action = self.sudo().env.ref('sale.action_orders').read()[0]
        action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
        action['res_id'] = self.ms_so_id
        return action
    
    def view_po(self):
        action = self.sudo().env.ref('purchase.purchase_form_action').read()[0]
        action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
        action['res_id'] = self.ms_po_id
        return action

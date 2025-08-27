# -*- coding: utf-8 -*-
import base64
import datetime
import io

import requests

import PyPDF2

from odoo import api, fields, models, registry, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import logging
_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'odas2.metadata.mixin', 'odas2.stream.mixin']

    commercehub_sale_order_id = fields.Many2one('sale.order', ondelete='set null')
    commercehub_po = fields.Char('CommerceHub PO')
    commercehub_co = fields.Char('CommerceHub CO')


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'odas2.mixin', 'odas2.metadata.mixin', 'odas2.stream.mixin']

    has_packingslip = fields.Boolean(compute="_compute_has_packingslip")

    # INFO: link to the original commercehub SO (e.g. when a SO is created because of inter-company operation).
    commercehub_sale_order_id = fields.Many2one('sale.order')
    commercehub_po = fields.Char('CommerceHub PO')
    commercehub_co = fields.Char('CommerceHub CO')
    cancel_request = fields.Boolean('Richiesta di Cancellazione', tracking=True)
    cancel_request_processed = fields.Boolean('Richiesta di cancellazione per ordine già evaso', tracking=True)

    @api.constrains('cancel_request','cancel_request_processed')
    def function_cancel_request(self):
        if self.commercehub_po and not self._context.get('done',None):
            self = self.with_context(done=True)
            orders = list(self.sudo().search([('commercehub_po','=',self.commercehub_po),('id','!=',self.id)])) + list(self.env['purchase.order'].sudo().search([('commercehub_po','=',self.commercehub_po)]))
            for order in orders:
                order.cancel_request = self.cancel_request
                order.cancel_request_processed = self.cancel_request_processed
        
    # def _create_or_write_orders(self, orders):
    #     SaleOrder = self.env['sale.order']
    #     for order in orders:
    #         sale_order = SaleOrder.search([('origin', '=',  order.get('origin')), ('state', 'in', ['sent'])], limit=1)
    #         if order.state == 'sent':
    #             SaleOrder = SaleOrder.create()
    #     return SaleOrder

    # def write(self, vals):
    #     if 'state' in vals and vals.get('state') in ['cancel','done']:
    #         for rec in self:
    #             if rec.from_as2:
    #                 vals['need_synch_to_as2'] = True
    #     return super(SaleOrder, self).write(vals)

    def action_confirm(self):
        if self.as2_state == 'error':
            raise UserError(_("AS2 State is in error!"))
        return super(SaleOrder, self).action_confirm()

    @api.depends('message_ids.attachment_ids')
    def _compute_has_packingslip(self):
        for rec in self:
            rec.has_packingslip = False
            for msg in rec.message_ids:
                for att in msg.attachment_ids:
                    if att.mimetype == 'application/pdf':
                        rec.has_packingslip = True
                        break

    @api.model
    def _cron_odas2_sync_sale_order(self, automatic=False):
        resp = None

        for company in self.env['res.company'].search([]):

            odas2_url = company.odas2_url

            try:
                if automatic:
                    cr = registry(self._cr.dbname).cursor()
                    self = self.with_env(self.env(cr=cr))

                SaleOrder = self.env['sale.order']
                recs = SaleOrder.sudo().search([('need_synch_to_as2', '=', True), ('company_id', '=', company.id)])
                for rec in recs:
                    stream_id = rec.as2_stream_id
                    data = dict(
                        access_token=rec.company_id.odas2_access_token,
                        format='hubxml',
                        sender_id=stream_id.sender_id,
                        receiver_id=stream_id.receiver_id,
                        vendor_id=stream_id.vendor_id,
                        merchant_id=stream_id.merchant_id,
                        op_code='CONFIRM_SALE_ORDER',
                        orders=rec._prepare_dict_for_as2()
                    )

                    resp = requests.post(odas2_url, json=data)
                    if resp.status_code == 200:
                        rec.write({
                            'need_synch_to_as2': False,
                            'last_update_to_as2': datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        })
                    else:
                        _logger.info('Sale Order confirm synchronization response from OdAS2 server ::: {}'.format(resp.text))

                    if automatic:
                        self.env.cr.commit()

            except Exception as e:
                if automatic:
                    self.env.cr.rollback()
                _logger.info(str(e))
                if resp:
                    _logger.info('Sale Order confirm synchronization response from AS2 server ::: {}'.format(resp.text))
                # odas2_account._log_message(str(e), _("OdAS2 : products synchronization issues."), level="info", path="/items", func="_cron_sync_odas2_products")
                self.env.cr.commit()
            finally:
                if automatic:
                    try:
                        self._cr.close()
                    except Exception:
                        pass
            return True

    def _prepare_dict_for_as2(self):
        orders = []
        for rec in self:
            # INFO: only SO with a valid commercehub_po can be confirmed.
            if rec.commercehub_po:
                order_lines = []
                for ol in self.order_line:

                    # INFO: extract needed metadata from sale.order.line (originated from PO).
                    #       [0] = merchantLineNumber
                    #       [1] = shippingCode
                    #       [2] = trackingNumber
                    md = ol.as2_metadata.split()

                    if ol.state in ['sale', 'cancel']:
                        order_lines += [{

                            # INFO: source PO line number used to track product involved.
                            'merchantLineNumber': md[0],

                            # INFO: shipping code of the carrier that took care of the good.
                            'shippingCode': md[1] if len(md) > 1 else '',

                            # INFO: tracking number passed thru the PO and used to confirm back.
                            'trackingNumber': md[2] if len(md) > 2 else '',

                            # INFO: quantity shipped: at the moment the whole quantity has been involved.
                            'trxQty': str(ol.product_qty),

                            # INFO: confirms shipping or cancellation.
                            'action': (ol.state == 'sale' and 'v_ship') or (ol.state == 'cancel' and 'v_cancel') or '',
                            'actionCode': ol.state == 'cancel' and 'merchant_request' or '',

                        }]

                orders += [{
                    # INFO: tries to catch left side of 'origin' looking for poNumber.
                    'poNumber': rec.commercehub_po,
                    'orderLines': order_lines
                }]
        return orders

    def action_mark_as2_confirm(self):
        for rec in self:
            rec.write({
                'need_synch_to_as2': True,
                # 'last_update_to_as2': False
            })
        return True

    def action_unmark_as2_confirm(self):
        for rec in self:
            rec.write({
                'need_synch_to_as2': False,
                # 'last_update_to_as2': False
            })
        return True

    def action_download_packingslips_pdf(self):
        m = PyPDF2.PdfFileMerger()
        for rec in self:
            # INFO: maybe this SO is not the original CommerceHub SO?
            if rec.commercehub_sale_order_id:
                rec = rec.commercehub_sale_order_id.sudo()
            for msg in rec.message_ids:
                for att in msg.attachment_ids:
                    if att.mimetype == 'application/pdf':
                        if att.store_fname:
                            try:
                                fb = open(att._full_path(att.store_fname), 'rb')
                            except (IOError, OSError):
                                pass
                            else:
                                m.append(fb)
        w = io.BytesIO()
        m.write(w)
        w.seek(0)
        attachment = self.env['ir.attachment'].create({
            'datas': base64.b64encode(w.read()),
            'name': 'packingslips.pdf',
            'mimetype': 'application/pdf',
        })
        w.close()
        m.close()

        # INFO: fires downloading action request.
        action = {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=" + str(attachment.id) + "&filename_field=name&field=datas&download=true&name=" + attachment.name,
            'target': 'self'
        }
        return action

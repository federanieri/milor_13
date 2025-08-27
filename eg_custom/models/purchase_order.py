import base64
import datetime
import logging
import os
import tempfile

import xlsxwriter
from dateutil.relativedelta import relativedelta

from odoo import models, fields
from odoo.tools import date_utils

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    parola_chiave = fields.Char(string='Parola Chiave')
    vendor_return_reason_id = fields.Many2one(comodel_name='vendor.return.reason', string='Vendor Return Reason')

    def _auto_confirm_purchase_order(self):
        purchase_order_ids = self.sudo().with_context(force_company=2).search([
            ('company_id', '=', 2), ('state', 'in', ['draft', 'sent', 'to approve'])
        ])
        for purchase_order_id in purchase_order_ids:
            purchase_order_id.button_confirm()

    def send_daily_email_vendor_confirmed_order(self):
        last_day = fields.Datetime.now() + relativedelta(days=-1)
        last_day_start = date_utils.start_of(last_day, 'day')
        last_day_end = date_utils.end_of(last_day, 'day')
        purchase_order_ids = self.search(
            [('state', '=', 'purchase'), ('date_approve', '>=', last_day_start), ('date_approve', '<=', last_day_end),
             ('commercehub_po', '!=', False), ('commercehub_co', '!=', False),
             ('company_id', '=', 1)])
        vendor_ids = purchase_order_ids.mapped("partner_id")
        for vendor_id in vendor_ids:
            # for purchases in vendor_purchase_order_ids:
            purchases_order = purchase_order_ids.filtered(lambda x: x.partner_id.id == vendor_id.id)
            data_id = self.create_vendor_confirm_excel_attachment(purchases_order)
            template_id = self.env.ref('eg_custom.email_template_confirmed_vendor_po').id
            template = self.env['mail.template'].browse(template_id)
            template.attachment_ids = [(6, 0, [data_id.id])]
            template.send_mail(vendor_id.id, force_send=True)
            template.attachment_ids = [(3, data_id.id)]

    def create_vendor_confirm_excel_attachment(self, purchases=False):
        """
            Create Custom Excel Attachment to add into an email template.
        """
        filename = '{}{}{}'.format('purchase_orders_', datetime.datetime.now().strftime('_%Y-%m-%d_%H-%M-%S'), '.xlsx')
        path = os.path.join(tempfile.gettempdir(), filename)
        workbook = xlsxwriter.Workbook(path)
        worksheet = workbook.add_worksheet('Confirm Purchase Orders')
        worksheet = self._generate_excel_vendor_confirm_po(worksheet, purchases, workbook)
        workbook.close()

        file = open(path, 'rb')
        vals = {'name': filename,
                'type': 'binary',
                'public': True,
                'datas': base64.b64encode(file.read())
                }
        attachment_id = self.env['ir.attachment'].sudo().create(vals)
        file.close()
        return attachment_id

    def _generate_excel_vendor_confirm_po(self, worksheet=False, purchases=False, workbook=False):
        field_labels = [
            "Date Orderline",
            "Numero Ordine (PO)",
            "Commercehub PO",
        ]

        bold = workbook.add_format({'bold': True})
        bold.set_align('center')

        worksheet.set_column(0, len(field_labels), 20)

        row = 0
        col = 0

        for label in field_labels:
            worksheet.write(row, col, label, bold)
            col += 1

        row = 1
        col = 0

        fields = []
        purchase_order_list = []
        for po in purchases:
            worksheet.set_row(row, 98)
            worksheet.write(row, 0, '{}'.format(po.date_approve))
            worksheet.write(row, 1, '{}'.format(po.name))
            worksheet.write(row, 2, '{}'.format(po.commercehub_po or ''))

            row += 1
        return worksheet

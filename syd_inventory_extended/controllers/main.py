from odoo import _
from odoo.http import request
from odoo.addons.stock_barcode.controllers.main import StockBarcodeController

import base64

import logging

from odoo.tools.pdf import merge_pdf

_logger = logging.getLogger(__name__)


class StockBarcodeControllerExt(StockBarcodeController):

    def try_open_picking(self, barcode):
        po = request.env['purchase.order'].search([
            ('name', '=', barcode),
        ], limit=1)
        if po:
            for corresponding_picking in po.total_picking_ids:
                if corresponding_picking.state == 'assigned':
                    return self.get_action(corresponding_picking.id)

                # INFO: if PO picking is done then print (download it if printnode is disabled or no printer is set).
                if corresponding_picking.state == 'done' and po.commercehub_sale_order_id:
                    user = request.env.user
                    so = po.sudo().commercehub_sale_order_id
                    printer_id = user.printnode_printer
                    if so:
                        if user.printnode_enabled or user.company_id.printnode_enabled and printer_id:
                            for msg in so.message_ids:
                                for att in msg.attachment_ids:
                                    if att.mimetype == 'application/pdf':
                                        try:
                                            _logger.info(f"Printing from CommerceHub SO: '{so.name}' / PrintNode printer: '{printer_id}'")

                                            printer_id.printnode_print_b64(
                                                att.datas.decode('ascii'), { 'title': so.name, 'type': 'qweb-pdf', },
                                                check_printer_format=False
                                            )

                                            report_id = request.env['ir.actions.report']._get_report_from_name(
                                                'syd_product_report.report_pdf_products_picking')
                                            printer_id.printnode_print(report_id=report_id.sudo(),
                                                                       objects=corresponding_picking)

                                        except (IOError, OSError):
                                            _logger.error(f"Error printing attachments thru PrintNode")

                            return {'info': _('Printing extra documents of %(barcode)s') % {
                                'barcode': barcode}}
                        else:
                            pdf_datas = [base64.decodebytes(att.datas) for att in [m.attachment_ids for m in so.message_ids] if att.mimetype == 'application/pdf']
                            pdf, pdf_tag = request.env.ref('syd_product_report.action_print_products_per_transfer_picking').\
                                render_qweb_pdf(corresponding_picking.ids)

                            attachment = request.env['ir.attachment'].create({
                                'datas': base64.b64encode(merge_pdf(pdf_datas + [pdf])),
                                'name': 'packingslips_products_picking.pdf',
                                'mimetype': 'application/pdf',
                            })

                            _logger.info(f"Downloading from CommerceHub SO: '{so.name}'")
                            # INFO: returns downloading action request.
                            return {'action': {
                                'type': 'ir.actions.act_url',
                                'url': "web/content/?model=ir.attachment&id=" + str(
                                    attachment.id) + "&filename_field=name&field=datas&download=true&name=" + attachment.name,
                                'target': 'self'
                            }}

        so = request.env['sale.order'].search([
            ('name', '=', barcode),
        ], limit=1)
        if so:
            for corresponding_picking in so.total_picking_ids:
                if corresponding_picking.state == 'assigned':
                    return self.get_action(corresponding_picking.id)
        picking_ids = request.env['stock.picking'].search([
            ('carrier_tracking_ref', '=', barcode),
        ])
        for corresponding_picking in picking_ids:
                if corresponding_picking.state == 'assigned':
                    return self.get_action(corresponding_picking.id)
        return super(StockBarcodeControllerExt,self).try_open_picking(barcode)



import base64

import xlrd

from odoo import models, fields
from odoo.exceptions import Warning


class ProposalSaleLineImportWizard(models.TransientModel):
    _name = 'proposal.sale.line.import.wizard'
    _description = 'Proposal Sale Line Import Wizard'

    select_file = fields.Binary(string='Select File')
    file_name = fields.Char(string='File Name')

    def download_sample_file(self):
        attachment = self.env.ref("eg_sale_proposal_import.ir_attachment_import_sample_excel_proposal_sale_line")
        if not attachment:
            raise Warning("Not find file!!!")
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment.id),
            'target': 'new',
            'nodestroy': False,
        }

    def import_proposal_sale_lines(self):
        if not self.select_file:
            raise Warning("Please Select file")
        if self.file_name and self.file_name[-3:] != 'xls' and self.file_name[-4:] != 'xlsx':
            raise Warning("Only allow to XLS file")
        values = []
        header = []
        if self.file_name and self.file_name[-3:] != 'xls' and self.file_name[-4:] != 'xlsx':
            raise Warning("File type and upload file will be different")
        workbook = xlrd.open_workbook(file_contents=base64.decodebytes(self.select_file))
        sheet = workbook.sheets()[0]
        for row in range(sheet.nrows):
            dict_of_product = {}
            for col in range(sheet.ncols):
                value = sheet.cell(row, col).value
                if row == 0:
                    header.append(value)
                else:
                    dict_of_product[header[col]] = value
            if dict_of_product:
                values.append(dict_of_product)
        if values:
            if values[0].get("Sku") or values[0].get("Barcode"):
                if not values[0].get("Quantity") or not values[0].get('Price Unit'):
                    raise Warning(
                        "Please check the file header string it should be Sku or Barcode, Price Unit, Quantity for the format please download file from the wizard. ")
            else:
                raise Warning(
                    "Please check the file header string it should be Sku or Barcode, Price Unit, Quantity for the format please download file from the wizard. ")
        product_list = []
        for value in values:
            sku = value.get("Sku")
            barcode = value.get("Barcode")
            if sku or barcode:
                product_id = None
                if sku:
                    if isinstance(sku, float) or isinstance(sku, int):
                        sku = str(int(sku))
                    product_id = self.env["product.product"].search([("default_code", "=", sku)])
                elif barcode:
                    if isinstance(barcode, float) or isinstance(barcode, int):
                        barcode = str(int(barcode))
                    product_id = self.env["product.product"].search([('barcode', '=', barcode)])
                if not product_id:
                    product_list.append("{}".format(sku if sku else barcode))
        if product_list:
            raise Warning("This Product are not available in Odoo : {}".format(product_list))
        proposal_sale_order_id = self.env["proposal.sale.order"].browse(self._context.get("active_id"))
        if proposal_sale_order_id:
            for value in values:
                sku = value.get("Sku")
                barcode = str(value.get("Barcode")).split('.')[0]
                if sku or barcode:
                    product_id = None
                    if sku:
                        if isinstance(sku, float) or isinstance(sku, int):
                            sku = str(int(sku))
                        product_id = self.env["product.product"].search([("default_code", "=", sku)], limit=1)
                    elif not sku:
                        if isinstance(barcode, float) or isinstance(barcode, int):
                            barcode = str(int(barcode))
                        product_id = self.env["product.product"].search([("barcode", "=", barcode)], limit=1)
                    proposal_sale_order_line_id = self.env["proposal.sale.order.line"].search(
                        [("product_id", "=", product_id.id), ("porder_id", "=", proposal_sale_order_id.id)], limit=1)
                    if proposal_sale_order_line_id:
                        proposal_sale_order_line_id.write({
                            'qty_proposed': value.get('Quantity'),
                            'lst_price': value.get('Price Unit')
                        })
                        continue
                    line_dict = {
                        'porder_id': proposal_sale_order_id.id,
                        'product_id': product_id.id,
                        'qty_proposed': value.get('Quantity'),
                        'price_proposed': value.get('Price Unit'),
                    }
                    proposal_sale_order_line_obj = self.env['proposal.sale.order.line']
                    proposal_sale_order_line_id = self.env["proposal.sale.order.line"].new(line_dict)
                    proposal_sale_order_line_id._onchange_productid_qty()
                    proposal_sale_order_line_id.product_id_change()
                    proposal_sale_order_line_id.product_qty_change()
                    proposal_sale_order_line_id.qty_proposed = value.get('Quantity')
                    proposal_sale_order_line_id.price_proposed = value.get('Price Unit')
                    proposal_sale_order_line_value = proposal_sale_order_line_id._convert_to_write(
                        proposal_sale_order_line_id._cache)
                    proposal_sale_order_line_obj.create(proposal_sale_order_line_value)

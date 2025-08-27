from odoo import api, exceptions, fields, models


class WizardSaleOrderImport(models.TransientModel):
    _name = "syd_pepperi.wizard_import_sale_order"
    _description = 'Import Sale Order'

    trans_id = fields.Char(string='ID Pepperi')

    def confirm(self):
        res = self.env['sale.order'].na_get_order_by_id(pepperi_id=self.trans_id)
        return res

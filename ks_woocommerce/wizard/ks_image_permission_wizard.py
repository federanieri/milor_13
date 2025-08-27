# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


class KsImagePermissionWizard(models.TransientModel):
    _name = "ks.image.permission.wizard"
    _description = "Take permission while importing individual product"

    ks_import_product_with_images = fields.Boolean(string="Execute Operation with Images")
    ks_import_product_without_images = fields.Boolean(string="Execute Operation without Images")
    ks_product_template = fields.Char()
    ks_export_operation = fields.Integer()

    def ks_execute_permission_operation(self):
        ks_product_temp = self.ks_product_template[1:-1].split(',')
        ks_product_temp_ = []
        for id in ks_product_temp:
            ks_product_temp_.append(int(id))
        if not self.ks_import_product_without_images and not self.ks_import_product_with_images:
            raise UserError(_('Please select atleast one operation.'))
        ks_product_temp_ids = self.env['product.template'].search([]).filtered(lambda x: x.id in ks_product_temp_)
        if self.ks_import_product_with_images:
            ks_image_permission = True
        if self.ks_import_product_without_images:
            ks_image_permission = False
        if not self.ks_export_operation:
            return ks_product_temp_ids.ks_update_product_to_odoo()
        if self.ks_export_operation:
            return ks_product_temp_ids.ks_update_product_to_woo()

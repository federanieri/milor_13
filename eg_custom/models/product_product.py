from odoo import models, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_archive(self):
        if not self.env.user.has_group('eg_custom.product_archive_group'):
            raise UserError(_('You do not have rights to archive products.'))
        else:
            res = super(ProductProduct, self).action_archive()
            return res

    def action_unarchive(self):
        if not self.env.user.has_group('eg_custom.product_archive_group'):
            raise UserError(_('You do not have rights to archive products.'))
        else:
            res = super(ProductProduct, self).action_unarchive()
            return res

from odoo import models, _, fields
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_published = fields.Boolean(track_visibility='onchange')

    def action_archive(self):
        if not self.env.user.has_group('eg_custom.product_archive_group'):
            raise UserError(_('You do not have rights to archive products.'))
        else:
            res = super(ProductTemplate, self).action_archive()
            return res

    def action_unarchive(self):
        if not self.env.user.has_group('eg_custom.product_archive_group'):
            raise UserError(_('You do not have rights to archive products.'))
        else:
            res = super(ProductTemplate, self).action_unarchive()
            return res

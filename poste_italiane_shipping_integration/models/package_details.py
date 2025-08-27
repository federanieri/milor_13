from odoo import models, fields


class PackageDetails(models.Model):
    _inherit = 'product.packaging'

    package_carrier_type = fields.Selection(selection_add=[("poste_italiane_provider", "Poste Italiane")])

from odoo import models, fields, api, _

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def take_name(self):
        result = self.name_get()
        name = ''
        try: 
            name = result[-1][-1]
        except: 
            name = self.name
        return name
    
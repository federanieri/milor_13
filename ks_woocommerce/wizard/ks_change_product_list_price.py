# -*- coding: utf-8 -*-

from odoo import api, fields, models


class KsProductChangeListPrice(models.TransientModel):
    _name = "ks.change.product.price"
    _description = "Change Product List Price"

    ks_instance_id = fields.Many2one('ks.woocommerce.instances', string='Woo Instance', readonly=True)
    ks_currency_id = fields.Many2one('res.currency', readonly=True)
    ks_price_list_id = fields.Many2one('product.pricelist', readonly=True)
    ks_changelist_ids = fields.One2many('ks.product.price', 'ks_change_price_id')

    def ks_change_price(self):
        """ Changes the Standard Price of Product and creates an account move accordingly. """
        print(self)
        for ks_changelist in self.ks_changelist_ids:
            instance_id = self.ks_instance_id
            pricelist_item = ks_changelist.ks_pricelist_item_id
            ks_pricelists = instance_id.ks_woo_pricelist_ids
            if not ks_pricelists:
                ks_pricelists = self.ks_price_list_id
            if ks_changelist.ks_product_id.ks_woo_product_type == 'simple':
                ks_changelist.ks_product_id.write({'list_price': ks_changelist.ks_new_price})
            if ks_changelist.ks_pricelist_item_id:
                for ks_pricelist in ks_pricelists:
                    if ks_pricelist.id == self.ks_price_list_id.id:
                        pricelist_item.fixed_price = ks_changelist.ks_new_price
                    else:
                        conversion_rate = ks_pricelist.currency_id.rate / self.ks_price_list_id.currency_id.rate
                        ks_pricelist_item = ks_pricelist.item_ids.search([
                            ('product_id', '=', ks_changelist.ks_product_id.id),
                            ('ks_instance_id', '=', instance_id.id), ('pricelist_id', '=', ks_pricelist.id)])
                        ks_pricelist_item.fixed_price = ks_changelist.ks_new_price * conversion_rate
        return {'type': 'ir.actions.act_window_close'}


class KsChangeListPrice(models.TransientModel):
    _name = "ks.product.price"
    _description = "Change Product Price"

    ks_new_price = fields.Float('New Price', digits='Product Price',  required=True)
    ks_old_price = fields.Float('Old Price', digits='Product Price',  required=True)
    ks_product_id = fields.Many2one('product.product')
    ks_product_tmpl_id = fields.Many2one('product.template')
    ks_change_price_id = fields.Many2one('ks.change.product.price')
    ks_pricelist_item_id = fields.Many2one('product.pricelist.item')

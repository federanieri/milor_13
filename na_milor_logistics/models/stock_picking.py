from odoo import fields, models, api


class NaStockPicking(models.Model):
    _inherit = 'stock.picking'

    na_ordernum = fields.Char(string='NA Order num',
                              help='Campo compute per rimuovere / dal nome ordine',
                              compute='_compute_na_ordernum',
                              store=True)

    @api.depends('name')
    def _compute_na_ordernum(self):
        for rec in self:
            if rec.name:
                rec.na_ordernum = rec.name.replace('/', '')

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PepperiMixin(models.AbstractModel):
    _name = 'pepperi.mixin'
    _description = 'Pepperi Mixin'

    from_pepperi = fields.Boolean(string='From Pepperi')
    to_pepperi = fields.Boolean(string='To Pepperi')
    last_update_from_pepperi = fields.Datetime(string='Last Update From Pepperi')
    last_update_to_pepperi = fields.Datetime(string='Last Update To Pepperi')
    modification_datetime = fields.Char('ModificationDateTime', readonly=True)
    need_synch_to_pepperi = fields.Boolean(help='Technical field used to determine weather record need to update on pepperi or not')

    def _pepperi_fields(self):
        return []

    def write(self, vals):
        res = super(PepperiMixin, self).write(vals)
        if any(f in self._pepperi_fields() for f in vals.keys()):
            self.filtered(lambda r: r.to_pepperi).need_synch_to_pepperi = True
        return res

    @api.model
    def create(self, vals):
        res = super(PepperiMixin, self).create(vals)
        if any(f in self._pepperi_fields() for f in vals.keys()):
            self.filtered(lambda r: r.to_pepperi).need_synch_to_pepperi = True
        return res

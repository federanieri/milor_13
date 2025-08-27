# -*- coding: utf-8 -*-

from odoo import api, fields, models


class OdAS2Mixin(models.AbstractModel):
    _name = 'odas2.mixin'
    _description = 'odas2 Mixin'

    as2_state = fields.Selection([('warning', 'Warning'), ('error', 'Error')])
    as2_state_reason = fields.Char(default='')

    # INFO: no need to sync from from AS2 (because AS2 is a push technology) but when data arrives then updates
    #       from_as2 and last_update_from_as2.
    from_as2 = fields.Boolean(string='From AS2', dafault=False)
    last_update_from_as2 = fields.Datetime(string='Last Update From AS2')

    to_as2 = fields.Boolean(string='To AS2', dafault=False)
    last_update_to_as2 = fields.Datetime(string='Last Update To AS2')
    need_synch_to_as2 = fields.Boolean(
        dafault=False, help='Technical field used to determine weather record need to update on AS2 server or not')

    def _to_as2_fields(self):
        return []

    def write(self, vals):
        res = super(OdAS2Mixin, self).write(vals)
        # INFO: checks if sensitive fields are changed.
        if any(f in self._to_as2_fields() for f in vals.keys()):
            # INFO: sets/unsets need_synch_to_as2 according to to_as2 field (no need to synch if to_as2 field is unset).
            for rec in self:
                rec.need_synch_to_as2 = rec.to_as2
        return res

    @api.model
    def create(self, vals):
        res = super(OdAS2Mixin, self).create(vals)
        if any(f in self._to_as2_fields() for f in vals.keys()):
            # INFO: sets/unsets need_synch_to_as2 according to to_as2 field (no need to synch if to_as2 field is unset).
            for rec in self:
                rec.need_synch_to_as2 = rec.to_as2
        return res


class OdAS2MetadataMixin(models.AbstractModel):
    _name = 'odas2.metadata.mixin'
    _description = 'odas2 Metadata Mixin'

    as2_metadata = fields.Text(string="Metadata", help="Techical field to store extra data from AS2 in json format.")


class OdAS2StreamMixin(models.AbstractModel):
    _name = 'odas2.stream.mixin'
    _description = 'odas2 Stream Mixin'

    as2_stream_id = fields.Many2one('odas2.stream')


class OdAS2StreamsMixin(models.AbstractModel):
    _name = 'odas2.streams.mixin'
    _description = 'odas2 Streams Mixin'

    as2_stream_ids = fields.Many2many('odas2.stream')


# -- coding: utf-8 --
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class NaApiSyncConfigFields(models.Model):
    _name = 'na.api.sync.config.fields'
    _order = 'sequence, id'

    sequence = fields.Integer(string="Sequence", default=10)
    config_id = fields.Many2one('na.api.sync.config', string='Configuration', required=True,
                                ondelete='cascade')
    ext_system_field = fields.Char(string='External System Field')
    # TODO: Manage exception and errors for subfield
    ext_system_subfield = fields.Char(string='External System Subfield')
    model_id = fields.Many2one('ir.model', related='config_id.model_id', readonly=True)
    odoo_field_id = fields.Many2one('ir.model.fields', string='Odoo Field',
                                    ondelete='cascade')
    odoo_subfield = fields.Char(string='Odoo Subfield')
    odoo_field_ttype = fields.Selection(related='odoo_field_id.ttype', string='Field Type')
    field_config_id = fields.Many2one('na.api.sync.config', string='Configuration Field')
    exclusive_use = fields.Selection([('get', 'GET'), ('post', 'POST')], string='Exclusive Use',
                                     help='if the selection is left blank, '
                                          'the field will be used in both get and post calls ')
    check_field = fields.Boolean(string='Check Field')
    # filed added for the advance management
    length = fields.Integer(string='Length')
    fixed_value = fields.Char(string='Fixed Value')
    filler_align = fields.Selection([('right', 'Right'), ('left', 'Left')], string="Filler Align",
                                    default='right', required=True)
    value_align = fields.Selection([('right', 'Right'), ('left', 'Left')],
                                   string="Value Align", default='left', required=True)
    filler = fields.Char(string='Filler')
    decimal = fields.Integer('Decimal Number', default=0)
    vir = fields.Selection([(',', ','), ('.', '.')], string='Separator')

    # TODO: commentato temporaneamente vedere come gestire per i subfield
    # @api.constrains('ext_system_field')
    # def check_ext_system_field(self):
    #     for record in self:
    #         not_unique = record.config_id.api_fields_ids.filtered(
    #             lambda f: f.ext_system_field == record.ext_system_field and f.id != record.id)
    #         if not_unique:
    #             raise ValidationError(
    #                 _('The External System Field field must be only one for each api sync config.'))

    # @api.constrains('odoo_field_id')
    # def check_odoo_field_id(self):
    #     for record in self:
    #         not_unique = record.config_id.api_fields_ids.filtered(
    #             lambda f: f.odoo_field_id == record.odoo_field_id and f.id != record.id
    #             and f.odoo_field_id)
    #         not_unique = not_unique.filtered(lambda f: f.odoo_subfield == record.odoo_subfield
    #                                          and f.odoo_field_id)
    #         if not_unique:
    #             raise ValidationError(
    #                 _('The Odoo Field field must be only one for each api sync config.'))

    @api.constrains('check_field')
    def check_check_field(self):
        for record in self:
            check = record.config_id.api_fields_ids.filtered(
                lambda f: f.check_field)
            if len(check) > 1:
                raise ValidationError(
                    _('The check field must be only one for each api sync config.'))

    def clean_value_format(self, val):
        # check the format of the value and fix it based on the configuration
        if type(val) in [float, int]:
            # if it is a number, I check the format.
            val = str(format(float(val), f'.{self.decimal}f'))
            if not self.vir:
                val = val.replace(',', '').replace('.', '')
            else:
                val = val.replace(',', self.vir).replace('.', self.vir)
        # afterward we go to fix all the spaces by filling them with the filler from the line.
        val = str(val).replace('False', '').replace(
            '&nbsp;', '').replace('&nbsp', '')
        return val

    def pad_field_value(self, value):
        # the function goes to trim the string based on length or
        # add a filler to reach the configured length
        field_value = value
        length = self.length
        # if the length was not entered and is 0, then keep the normal length of the file
        if length == 0:
            return field_value
        value_align = self.value_align
        if len(value) > length:
            # in case the value is longer than the available length we go to cut
            # it according to its alignment.
            if value_align == 'right':
                diff = len(value) - length
                field_value = value[diff:]
            elif value_align == 'left':
                field_value = value[0:length]
        # only after cleaning the data we go to add the filler
        filler = self.filler or None
        # the string &nbsp corresponds to the space.
        filler = ' ' if filler == '&nbsp' else filler
        if filler is None or len(value) >= length:
            return field_value
        # we go to fill in the spaces that are left over through filler, and through
        # the alignment of the filler we figure out whether to put them to the right or left.
        filler_align = self.filler_align
        if filler_align == 'right':
            field_value = value.ljust(length, filler)
        elif filler_align == 'left':
            field_value = value.rjust(length, filler)
        return field_value

    def reformat_value(self, value):
        if not value:
            return value
        val_str = self.clean_value_format(value)
        # get the padded value
        val = self.pad_field_value(val_str)
        return val

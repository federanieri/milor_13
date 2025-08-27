from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import datetime, date


class NaDiscount(models.Model):
    _name = 'na.discount'

    partner_id = fields.Many2one('res.partner')
    discount_percentage = fields.Float(string="Sconto %", required=True)
    discount_start = fields.Date(string='Inizio validità sconto', required=True)
    discount_end = fields.Date(string='Fine validità sconto', required=True)

    @api.model
    def create(self, vals):
        partner_lines = self.env['res.partner'].search([('id', '=', vals['partner_id'])]).discount_line
        for line in partner_lines:
            line_start = line.discount_start
            line_end = line.discount_end
            new_line_start = datetime.strptime(vals['discount_start'], '%Y-%m-%d').date()
            new_line_end = datetime.strptime(vals['discount_end'], '%Y-%m-%d').date()
            if line_start <= new_line_start <= line_end:
                self.overlap_error()
            elif line_start <= new_line_end <= line_end:
                self.overlap_error()
            elif new_line_start <= line_start and new_line_end >= line_end:
                self.overlap_error()
            if new_line_start > new_line_end:
                self.impossible_dates_error()

        res = super(NaDiscount, self).create(vals)
        return res

    @api.model
    def write(self, vals):
        dates = {'discount_start', 'discount_end'}.intersection({key for key in vals.keys()})
        if dates:
            partner_lines = self.partner_id.discount_line
            for line in partner_lines:
                line_start = line.discount_start
                line_end = line.discount_end
                for date in dates:
                    date_obj = datetime.strptime(vals[date], '%Y-%m-%d').date()
                    if line_start <= date_obj <= line_end:
                        self.overlap_error()
            if vals.get('discount_start', False):
                start_obj = datetime.strptime(vals['discount_start'], '%Y-%m-%d').date()
                if start_obj > self.discount_end:
                    self.impossible_dates_error()
            if vals.get('discount_end', False):
                end_obj = datetime.strptime(vals['discount_end'], '%Y-%m-%d').date()
                if end_obj < self.discount_start:
                    self.impossible_dates_error()
            if start_obj and end_obj:
                if start_obj < self.discount_start and end_obj > self.discount_end:
                    self.overlap_error()
        res = super(NaDiscount, self).write(vals)
        return res

    def overlap_error(self):
        raise UserError("ATTENZIONE!:\n"
                        "Il periodo di validità dello sconto inserito si sovrappone a uno sconto esistente!\n"
                        "Verificare le date di validità")

    def impossible_dates_error(self):
        raise UserError("ATTENZIONE!\n"
                        "Il periodo di validità richiesto è errato!\n"
                        "Verificare le date inserite")
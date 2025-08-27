from odoo import fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    custom_type = fields.Selection([('vision_account', 'Conto Visione'),
                                    ('standard', 'Ordine standard')], string='Custom Type', readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['custom_type'] = ", s.custom_type as custom_type"
        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)

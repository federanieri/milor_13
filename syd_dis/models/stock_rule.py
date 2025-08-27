# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _, SUPERUSER_ID

import logging

_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _process_txt_stl(self, company_id, values, po, line=False, product_id=False):
        if company_id.dis_project_id:
            if not product_id:
                product_id = values and values.get('product_id')
                product_id = line and line.product_id or product_id and self.env['product.product'].sudo().browse(product_id)
            supplier_id = values and values.get('supplier')
            supplier_id = supplier_id and supplier_id.name or po.partner_id
            _logger.info(f"Supplier: <{supplier_id}>.")
            if supplier_id and supplier_id.need_txt_stl:
                _logger.info(f"txt_type: <{product_id.txt_type}>.")
                if product_id.txt_type in ['txt1', 'txt2']:
                    custom_value = line and line.custom_value or values and values.get('custom_value') or ''
                    size = product_id.with_context(lang=None).product_template_attribute_value_ids.\
                               filtered(lambda self: self.attribute_id.name in
                                                     ['SIZE USA', 'SIZE', 'Size', 'SIZE UK', 'SIZE FR']).name or ''
                    if product_id.txt_type == 'txt1':
                        txt = '%s;%s;%s;;%s;;;%s;;%s;;%s;;;;;;;;;;;;;;;;;;;;;;;;%s;%s;%s;' % (
                            po.date_order.strftime('%Y-%m-%d'),
                            (po.date_order + timedelta(days=7)).strftime('%Y-%m-%d'),
                            po.commercehub_po or '',
                            po.name,
                            product_id.commercehub_code or '',
                            product_id.name or '',
                            custom_value or '',
                            product_id.product_tmpl_id.metal_code_title_id.name or '',
                            product_id.plating_id.name or '',
                            size,
                        )
                    # INFO: builds a TXT to generate a STL file.
                    if product_id.txt_type == 'txt2':
                        valid_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789()'
                        custom_value = ''.join([c for c in custom_value if c in valid_chars])
                        txt = '%s|%s|%s|%s|%s|%s|%s' % (
                            po.name,
                            product_id.qvc_code or '',
                            product_id.milor_code or '',
                            size,
                            custom_value or '',
                            product_id.plating_id.name or '',
                            supplier_id.fm_code or ''
                        )
                    ProjectTask = self.env['project.task'].sudo()
                    pt_id = ProjectTask.create([{
                        'name': po.name,
                        'project_id': po.company_id.dis_project_id.id,
                        'txt': txt,
                        'stl_file': False,
                    }])
                    return {'dis_task_id': pt_id.id}
        return {}

    # INFO: In case of POs first created.
    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, po):
        result = super(StockRule, self)._prepare_purchase_order_line(product_id, product_qty, product_uom, company_id, values, po)

        result.update(self._process_txt_stl(company_id, values, po, False, product_id))
        return result

    # INFO: In case of POs grouped by product for example.
    def _update_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, line):
        result = super(StockRule, self)._update_purchase_order_line(product_id, product_qty, product_uom, company_id, values, line)
        result.update(self._process_txt_stl(company_id, values, line.order_id, line))
        return result

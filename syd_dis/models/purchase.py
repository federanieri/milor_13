# -*- coding: utf-8 -*-

from odoo import api, fields, models, registry, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    has_txt_type = fields.Char(compute='_compute_has_txt_type', store=True)

    @api.depends('order_line.product_id')
    def _compute_has_txt_type(self):
        for rec in self:
            # INFO: scans oder_line.product_id for txt_type (discard False txt_type).
            txt_types = [x for x in rec.order_line.product_id.mapped('txt_type') if x]
            # INFO: sets has_txt_type with last one txt_type set.
            rec.has_txt_type = txt_types and txt_types[-1] or False


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    dis_task_id = fields.Many2one('project.task')
    dis_task_stl_file = fields.Binary(related='dis_task_id.stl_file', readonly=True, store=False)

    def action_generate_txt_stl(self):
        if self.company_id.dis_project_id:
            result = self.env['stock.rule'].sudo()._process_txt_stl(self.env.company, False, self.order_id, self, product_id=False)
            if result.get('dis_task_id'):
                self.dis_task_id = result['dis_task_id']
        return True

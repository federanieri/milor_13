import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class KsSpecificReocrdImport(models.TransientModel):
    _name = "ks.specific.record.import"

    ks_woo_instance = fields.Many2one('ks.woocommerce.instances', string='WooCommerce Instance', required=True)
    ks_model = fields.Many2one('ir.model', string="Model Name", required=True,
                               domain="[('model', 'in', ['product.template','res.partner',"
                                      "'product.category', 'sale.order', 'ks.woo.product.tag'])]")
    ks_model_name = fields.Char('Model Name', related='ks_model.model', readonly=True, store=True)
    ks_all_records_ids = fields.Char("Record Woo Id(s)")
    ks_value_example = fields.Char(default="For multiple record separate Woo Id(s) using '|'. For example: 111|222|333",
                                   readonly=True)

    @api.onchange('ks_model')
    def check_fields_value(self):
        if not self.ks_model:
            self.ks_all_records_ids = False

    def ks_import_specific_record(self):
        instance_id = self.env['ks.woocommerce.instances'].search([('id', '=', self.ks_woo_instance.id)], limit=1)
        if not self.ks_all_records_ids:
            return self.env['ks.message.wizard'].ks_pop_up_message(names='Info',
                                                                   message="Please provide Woo Id of record for import.")
        if self.ks_all_records_ids:
            numeric_list = [str(k) for k in range(10)]
            woo_record_ids = self.ks_all_records_ids.split('|')
            for i in woo_record_ids:
                for j in i:
                    if j not in numeric_list:
                        return self.env['ks.message.wizard'].ks_pop_up_message(names='Info',
                                                                               message="Please enter valid Woo Id of record for import.")

        if instance_id.ks_instance_state == 'active' and self.ks_model.id == self.env.ref('base.model_res_partner').id:
            self.import_specific_customer(instance_id)
        if instance_id.ks_instance_state == 'active' and self.ks_model.id == self.env.ref(
                'product.model_product_template').id:
            self.import_specific_product(instance_id)
        if instance_id.ks_instance_state == 'active' and self.ks_model.id == self.env.ref('sale.model_sale_order').id:
            self.import_specific_sale_order(instance_id)
        if instance_id.ks_instance_state == 'active' and self.ks_model.id == self.env.ref(
                'product.model_product_category').id:
            self.import_specific_category(instance_id)
        if instance_id.ks_instance_state == 'active' and self.ks_model.id == self.env.ref(
                'ks_woocommerce.model_ks_woo_product_tag').id:
            self.import_specific_product_tag(instance_id)
        return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                               message="Please refer logs for further details")

    def import_specific_customer(self, instance_id):
        if self.ks_all_records_ids:
            woo_order_ids = self.ks_all_records_ids.split('|')
            woo_ids_list = [int(i) for i in woo_order_ids if i != '']
        wcapi = self.ks_woo_instance.ks_api_authentication()
        ks_wcapi_status = wcapi.get("").status_code
        for woo_id in woo_ids_list:
            try:
                if ks_wcapi_status in [200, 201]:
                    customer_response = wcapi.get("customers/%s" % woo_id)
                    if customer_response.status_code in [200, 201]:
                        customer = self.env['res.partner'].search(
                            [('ks_woo_id', '=', woo_id), ('ks_woo_instance_id', '=', instance_id.id)])
                        if customer:
                            res = "updated"
                        else:
                            res = "created"
                        customer = self.env['res.partner'].ks_manage_customer_woo_data(instance_id,
                                                                                       customer_response.json())
                        customer = self.env['res.partner'].search(
                            [('ks_woo_id', '=', woo_id), ('ks_woo_instance_id', '=', instance_id.id)])
                        self.env['ks.woo.sync.log'].create_log_param(
                            ks_woo_id=woo_id,
                            ks_status='success',
                            ks_type='customer',
                            ks_woo_instance_id=instance_id,
                            ks_operation='woo_to_odoo',
                            ks_operation_type='fetch',
                            response="Customer " + "[" + customer.name + "] with " + "Woo id: " + str(woo_id) + " is "
                                                                                                                "successfully " + res,
                        )
                    else:
                        if woo_id > (2 ** 31 - 1):
                            self.env['ks.woo.sync.log'].create_log_param(
                                ks_woo_id=False,
                                ks_status='failed',
                                ks_type='customer',
                                ks_woo_instance_id=instance_id,
                                ks_operation='woo_to_odoo',
                                ks_operation_type='fetch',
                                response="Please provide appropriate Woo Id " + str(woo_id),
                            )
                        else:
                            self.env['ks.woo.sync.log'].create_log_param(
                                ks_woo_id=woo_id,
                                ks_status='failed',
                                ks_type='customer',
                                ks_woo_instance_id=instance_id,
                                ks_operation='woo_to_odoo',
                                ks_operation_type='fetch',
                                response="No record found for Woo Id " + str(woo_id),
                            )

            except Exception as e:
                self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="customer",
                                                             operation_type="import",
                                                             instance_id=instance_id,
                                                             operation="woo_to_odoo", exception=e)

    def import_specific_product(self, instance_id):
        if self.ks_all_records_ids:
            woo_order_ids = self.ks_all_records_ids.split('|')
            woo_ids_list = [int(i) for i in woo_order_ids if i != '']
        wcapi = self.ks_woo_instance.ks_api_authentication()
        ks_wcapi_status = wcapi.get("").status_code
        for woo_id in woo_ids_list:
            try:
                if ks_wcapi_status in [200, 201]:
                    product_response = wcapi.get("products/%s" % woo_id)
                    if product_response.status_code in [200, 201]:
                        product = self.env['product.template'].search(
                            [('ks_woo_id', '=', woo_id), ('ks_woo_instance_id', '=', instance_id.id)])
                        if product:
                            res = "updated"
                        else:
                            res = "created"
                        product = self.env['product.template'].ks_mangae_woo_product(product_response.json(),
                                                                                     wcapi, instance_id)
                        product = self.env['product.template'].search(
                            [('ks_woo_id', '=', woo_id), ('ks_woo_instance_id', '=', instance_id.id)])
                        self.env['ks.woo.sync.log'].create_log_param(
                            ks_woo_id=woo_id,
                            ks_status='success',
                            ks_type='product',
                            ks_woo_instance_id=instance_id,
                            ks_operation='woo_to_odoo',
                            ks_operation_type='fetch',
                            response="Product " + "[" + product.name + "] with " + "Woo id: " + str(woo_id) + " is "
                                                                                                              "successfully " + res,
                        )
                    else:
                        if woo_id > (2 ** 31 - 1):
                            self.env['ks.woo.sync.log'].create_log_param(
                                ks_woo_id=False,
                                ks_status='failed',
                                ks_type='product',
                                ks_woo_instance_id=instance_id,
                                ks_operation='woo_to_odoo',
                                ks_operation_type='fetch',
                                response="Please provide appropriate Woo Id " + str(woo_id),
                            )
                        else:
                            self.env['ks.woo.sync.log'].create_log_param(
                                ks_woo_id=woo_id,
                                ks_status='failed',
                                ks_type='product',
                                ks_woo_instance_id=instance_id,
                                ks_operation='woo_to_odoo',
                                ks_operation_type='fetch',
                                response="No record found for Woo Id " + str(woo_id),
                            )
            except Exception as e:
                self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="product",
                                                             operation_type="import",
                                                             instance_id=instance_id,
                                                             operation="woo_to_odoo", exception=e)

    def import_specific_sale_order(self, instance_id):
        if self.ks_all_records_ids:
            woo_order_ids = self.ks_all_records_ids.split('|')
            woo_ids_list = [int(i) for i in woo_order_ids if i != '']
        wcapi = self.ks_woo_instance.ks_api_authentication()
        # order_status = ','.join(instance.ks_order_status.mapped('status'))
        ks_wcapi_status = wcapi.get("").status_code
        ks_order_status = []
        for value in instance_id.ks_import_order_state_config:
            if value.ks_sync:
                ks_order_status.append(value.ks_woo_states)
        for woo_id in woo_ids_list:
            try:
                if ks_wcapi_status in [200, 201]:
                    woo_order_response = wcapi.get("orders/%s" % woo_id)
                    if woo_order_response.json()['status'] in ks_order_status:
                        if woo_order_response.status_code in [200, 201]:
                            sale_order = self.env['sale.order'].search(
                                [('ks_woo_id', '=', woo_id), ('ks_woo_instance_id', '=', instance_id.id)])
                            if sale_order:
                                res = "updated"
                            else:
                                res = "created"

                            sale_order = self.env['sale.order'].ks_manage_sale_order_data(woo_order_response.json(),
                                                                                          wcapi,
                                                                                          instance_id)
                            sale_order = self.env['sale.order'].search(
                                [('ks_woo_id', '=', woo_id), ('ks_woo_instance_id', '=', instance_id.id)])
                            if res == "updated":
                                self.env['ks.woo.sync.log'].create_log_param(
                                    ks_woo_id=woo_id,
                                    ks_status='success',
                                    ks_type='order',
                                    ks_woo_instance_id=instance_id,
                                    ks_operation='woo_to_odoo',
                                    ks_operation_type='fetch',
                                    response="Order " + "[" + sale_order.name + "] with " + "Woo id: " + str(
                                        woo_id) + " is "
                                                  "successfully " + res,
                                )
                        else:
                            if woo_id > (2 ** 31 - 1):
                                self.env['ks.woo.sync.log'].create_log_param(
                                    ks_woo_id=False,
                                    ks_status='failed',
                                    ks_type='order',
                                    ks_woo_instance_id=instance_id,
                                    ks_operation='woo_to_odoo',
                                    ks_operation_type='fetch',
                                    response="Please provide appropriate Woo Id " + str(woo_id),
                                )
                            else:
                                self.env['ks.woo.sync.log'].create_log_param(
                                    ks_woo_id=woo_id,
                                    ks_status='failed',
                                    ks_type='order',
                                    ks_woo_instance_id=instance_id,
                                    ks_operation='woo_to_odoo',
                                    ks_operation_type='fetch',
                                    response="No record found for Woo Id " + str(woo_id),
                                )
                    else:
                        self.env['ks.woo.sync.log'].create_log_param(
                            ks_woo_id=False,
                            ks_status='failed',
                            ks_type='order',
                            ks_woo_instance_id=instance_id,
                            ks_operation='woo_to_odoo',
                            ks_operation_type='fetch',
                            response="You Cannot import this Order because their status Not match with instnace",
                        )

            except Exception as e:
                self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="order",
                                                             operation_type="import",
                                                             instance_id=instance_id,
                                                             operation="woo_to_odoo", exception=e)

    def import_specific_product_tag(self, instance_id):
        if self.ks_all_records_ids:
            woo_order_ids = self.ks_all_records_ids.split('|')
            woo_ids_list = [int(i) for i in woo_order_ids if i != '']
        wcapi = self.ks_woo_instance.ks_api_authentication()
        ks_wcapi_status = wcapi.get("").status_code
        for woo_id in woo_ids_list:
            try:
                if ks_wcapi_status in [200, 201]:
                    woo_tag_response = wcapi.get("products/tags/%s" % woo_id)
                    if woo_tag_response.status_code in [200, 201]:
                        product_tag = self.env['ks.woo.product.tag'].search(
                            [('ks_woo_id', '=', woo_id), ('ks_woo_instance_id', '=', instance_id.id)])
                        if product_tag:
                            res = "updated"
                        else:
                            res = "created"
                        product_tag = self.env['ks.woo.product.tag'].ks_manage_product_tags(woo_tag_response.json(),
                                                                                            instance_id)
                        product_tag = self.env['ks.woo.product.tag'].search(
                            [('ks_woo_id', '=', woo_id), ('ks_woo_instance_id', '=', instance_id.id)])
                        self.env['ks.woo.sync.log'].create_log_param(
                            ks_woo_id=woo_id,
                            ks_status='success',
                            ks_type='tags',
                            ks_woo_instance_id=instance_id,
                            ks_operation='woo_to_odoo',
                            ks_operation_type='fetch',
                            response="Tag " + "[" + product_tag.ks_name + "] with " + "Woo id: " + str(woo_id) + " is "
                                                                                                                 "successfully " + res,
                        )
                    else:
                        if woo_id > (2 ** 31 - 1):
                            self.env['ks.woo.sync.log'].create_log_param(
                                ks_woo_id=False,
                                ks_status='failed',
                                ks_type='tags',
                                ks_woo_instance_id=instance_id,
                                ks_operation='woo_to_odoo',
                                ks_operation_type='fetch',
                                response="Please provide appropriate Woo Id " + str(woo_id),
                            )
                        else:
                            self.env['ks.woo.sync.log'].create_log_param(
                                ks_woo_id=woo_id,
                                ks_status='failed',
                                ks_type='tags',
                                ks_woo_instance_id=instance_id,
                                ks_operation='woo_to_odoo',
                                ks_operation_type='fetch',
                                response="No record found for Woo Id " + str(woo_id),
                            )
            except Exception as e:
                self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="tags",
                                                             operation_type="import",
                                                             instance_id=instance_id,
                                                             operation="woo_to_odoo", exception=e)

    def import_specific_category(self, instance_id):
        if self.ks_all_records_ids:
            woo_order_ids = self.ks_all_records_ids.split('|')
            woo_ids_list = [int(i) for i in woo_order_ids if i != '']
        wcapi = self.ks_woo_instance.ks_api_authentication()
        ks_wcapi_status = wcapi.get("").status_code
        for woo_id in woo_ids_list:
            try:
                if ks_wcapi_status in [200, 201]:
                    woo_category_response = wcapi.get("products/categories/%s" % woo_id)
                    if woo_category_response.status_code in [200, 201]:
                        product_category = self.env['product.category'].search(
                            [('ks_woo_id', '=', woo_id), ('ks_woo_instance_id', '=', instance_id.id)])
                        if product_category:
                            res = "updated"
                        else:
                            res = "created"
                        product_category = self.env['product.category'].ks_update_category_woocommerce(wcapi,
                                                                                                       instance_id,
                                                                                                       woo_category_response.json())
                        product_category = self.env['product.category'].search(
                            [('ks_woo_id', '=', woo_id), ('ks_woo_instance_id', '=', instance_id.id)])

                        self.env['ks.woo.sync.log'].create_log_param(
                            ks_woo_id=woo_id,
                            ks_status='success',
                            ks_type='category',
                            ks_woo_instance_id=instance_id,
                            ks_operation='woo_to_odoo',
                            ks_operation_type='fetch',
                            response="Tag " + "[" + product_category.name + "] with " + "Woo id: " + str(
                                woo_id) + " is "
                                          "successfully " + res,
                        )
                    else:
                        if woo_id > (2 ** 31 - 1):
                            self.env['ks.woo.sync.log'].create_log_param(
                                ks_woo_id=False,
                                ks_status='failed',
                                ks_type='category',
                                ks_woo_instance_id=instance_id,
                                ks_operation='woo_to_odoo',
                                ks_operation_type='fetch',
                                response="Please provide appropriate Woo Id " + str(woo_id),
                            )
                        else:
                            self.env['ks.woo.sync.log'].create_log_param(
                                ks_woo_id=woo_id,
                                ks_status='failed',
                                ks_type='category',
                                ks_woo_instance_id=instance_id,
                                ks_operation='woo_to_odoo',
                                ks_operation_type='fetch',
                                response="No record found for Woo Id " + str(woo_id),
                            )
            except Exception as e:
                self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="category",
                                                             operation_type="import",
                                                             instance_id=instance_id,
                                                             operation="woo_to_odoo", exception=e)

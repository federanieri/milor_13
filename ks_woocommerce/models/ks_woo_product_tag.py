# -*- coding: utf-8 -*-

from odoo import models, fields, api
from requests.exceptions import ConnectionError
import datetime


class KsProductTag(models.Model):
    _name = 'ks.woo.product.tag'
    _description = 'WooCommerce Tags'
    _rec_name = 'ks_name'

    ks_name = fields.Char('Name', required=True)
    ks_woo_id = fields.Integer('WooCommerce Id', default=0, readonly=True)
    ks_slug = fields.Char('Slug')
    ks_description = fields.Text(string='Description')
    ks_export_in_woo = fields.Boolean('Exported in woo', readonly=True, compute='_compute_export_in_woo', store=True)
    ks_woo_instance_id = fields.Many2one('ks.woocommerce.instances', string='Instance', required=True)
    ks_company = fields.Many2one('res.company', 'Company', related='ks_woo_instance_id.ks_company')

    ks_sync_date = fields.Datetime('Modified On', readonly=True,
                                   help="Sync On: Date on which the record has been modified")
    ks_last_exported_date = fields.Datetime('Last Synced On',readonly=True)
    ks_sync_status = fields.Boolean('Sync Status', compute='sync_update', default=False)

    def sync_update(self):
        for rec in self:
            if rec.ks_last_exported_date and rec.ks_sync_date:
                ks_reduced_ks_sync_time = rec.ks_last_exported_date - datetime.timedelta(seconds=30)
                ks_increased_ks_sync_time = rec.ks_last_exported_date + datetime.timedelta(seconds=30)
                if rec.ks_sync_date > ks_reduced_ks_sync_time and rec.ks_sync_date < ks_increased_ks_sync_time:
                    rec.ks_sync_status = True
                else:
                    rec.ks_sync_status = False
            else:
                rec.ks_sync_status = False

    def write(self, values):
        for rec in self:
            if rec.ks_woo_id:
                values.update({'ks_sync_date': datetime.datetime.now()})
        super(KsProductTag, self).write(values)

    # To show the product tag values are exported in woo
    @api.depends('ks_woo_id')
    def _compute_export_in_woo(self):
        for rec in self:
            rec.ks_export_in_woo = bool(rec.ks_woo_id)

    @api.model
    def ks_update_product_tag_to_odoo(self):
        ks_rec_failed_list = []
        for rec in self:
            instance_id = self.env['ks.woocommerce.instances'].search([('id', '=', rec.ks_woo_instance_id.id)], limit=1)
            if instance_id.ks_instance_state == 'active':
                try:
                    wcapi = rec.ks_woo_instance_id.ks_api_authentication()
                    if wcapi.get("").status_code in [200, 201]:
                        woo_tag_response = wcapi.get("products/tags/%s" % rec.ks_woo_id)
                        if woo_tag_response.status_code in [200, 201]:
                            rec.ks_manage_product_tags(woo_tag_response.json(), instance_id)
                        else:
                            self.env['ks.woo.sync.log'].create_log_param(
                                ks_woo_id=False,
                                ks_status='failed',
                                ks_type='tags',
                                ks_woo_instance_id=instance_id,
                                ks_operation='woo_to_odoo',
                                ks_operation_type='fetch',
                                response=str(woo_tag_response.status_code) + eval(woo_tag_response.text).get('message'),
                            )
                except ConnectionError:
                    if rec.id not in ks_rec_failed_list:
                        ks_rec_failed_list.append(rec)
                    self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                        type='tags',
                                                                        operation='woo_to_odoo')
                except Exception as e:
                    if rec.id not in ks_rec_failed_list:
                        ks_rec_failed_list.append(rec)
                    self.env['ks.woo.sync.log'].ks_exception_log(record=rec, type="tags",
                                                                 operation_type="create" if rec.ks_woo_id else "update",
                                                                 instance_id=rec.ks_woo_instance_id,
                                                                 operation="odoo_to_woo", exception=e)
            else:
                return 'error'
        return ks_rec_failed_list

    def ks_update_product_tag_to_odoo_wizard(self):
        ks_failed_instance_list = []
        ks_failed_product_id = []
        for rec in self:
            ks_failed_list = rec.ks_update_product_tag_to_odoo()
            if ks_failed_list == 'error':
                format_info = 'The instance must be in active state or instance field should be updated to perform the operations'
                format_string = ks_message_string = ''
                log = 'Import Status'
            else:
                for record in ks_failed_list:
                    ks_failed_product_id.append(record.ks_name)
                    ks_failed_instance_list.append(record['ks_woo_instance_id'].display_name)
                log = 'Import Status'
                format_string = ks_message_string = ''
                if len(ks_failed_product_id) != 0:
                    ks_message_string = '\n\nList of Failed Records:\n'
                    format_string = 'Name:\t' + str(ks_failed_product_id) + '\n' + 'Instance:\t' + str(
                        ks_failed_instance_list)
                format_info = 'Import Operation has been performed, Please refer logs for further details.'
            return self.env['ks.message.wizard'].ks_pop_up_message(names=log,
                                                                   message=format_info + ks_message_string + format_string)


    # Added to queues
    @api.model
    def ks_update_product_tag_to_woo(self):
        ks_rec_failed_list = []
        ks_list = False
        for each_record in self:
            json_data = self._ks_prepare_odoo_product_tag_data(each_record)
            if each_record.ks_woo_instance_id and each_record.ks_woo_instance_id.ks_instance_state == 'active':
                try:
                    wcapi = each_record.ks_woo_instance_id.ks_api_authentication()
                    if wcapi.get('').status_code in [200, 201]:
                        if each_record.ks_woo_id:
                            record_exist = wcapi.get("products/tags/%s" % each_record.ks_woo_id)
                            if record_exist.status_code == 404:
                                ks_list = self.ks_create_tag_on_woo(wcapi, json_data, each_record)
                            else:
                                ks_list = self.ks_update_tag_on_woo(wcapi, json_data, each_record)
                        else:
                            ks_list = self.ks_create_tag_on_woo(wcapi, json_data, each_record)
                    else:
                        self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                                     ks_status='success' if wcapi.get("").status_code in [200,
                                                                                                                          201] else 'failed',
                                                                     ks_type='system_status',
                                                                     ks_woo_instance_id=each_record.ks_woo_instance_id,
                                                                     ks_operation='odoo_to_woo',
                                                                     ks_operation_type='connection',
                                                                     response='Connection successful' if wcapi.get("").status_code in [200, 201] else wcapi.get("").text)

                except ConnectionError:
                    self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=each_record.ks_woo_instance_id,
                                                                        type='tags',
                                                                        operation='odoo_to_woo',
                                                                        ks_woo_id=each_record.ks_woo_id)
                except Exception as e:
                    if each_record.id not in ks_rec_failed_list:
                        ks_rec_failed_list.append(each_record)
                    self.env['ks.woo.sync.log'].ks_exception_log(record=each_record, type="tags",
                                                                 operation_type="create" if each_record.ks_woo_id else "update",
                                                                 instance_id=each_record.ks_woo_instance_id,
                                                                 operation="odoo_to_woo", exception=e)
            else:
                self.env['ks.woo.sync.log'].ks_no_instance_log(each_record, 'tags')
                return 'error'
        return ks_rec_failed_list if len(ks_rec_failed_list) > 0 else (ks_list if type(ks_list) is list else [])

    def ks_update_product_tag_to_woo_wizard(self):
        ks_failed_instance_list = []
        ks_failed_product_id = []
        for rec in self:
            ks_failed_list = rec.ks_update_product_tag_to_woo()
            if ks_failed_list == 'error':
                format_info = 'The instance must be in active state or instance field should be updated to perform the operations'
                format_string = ks_message_string = ''
                log = 'Export Status'
            else:
                for record in ks_failed_list:
                    ks_failed_product_id.append(record.ks_name)
                    ks_failed_instance_list.append(record['ks_woo_instance_id'].display_name)
                log = 'Export Status'
                format_string = ks_message_string = ''
                if len(ks_failed_product_id) != 0:
                    ks_message_string = '\n\nList of Failed Records:\n'
                    format_string = 'Name:\t' + str(ks_failed_product_id) + '\n' + 'Instance:\t' + str(
                        ks_failed_instance_list)
                format_info = 'Export Operation has been performed, Please refer logs for further details.'
        return self.env['ks.message.wizard'].ks_pop_up_message(names=log,
                                                                   message=format_info + ks_message_string + format_string)

    def ks_update_tag_on_woo(self, wcapi, json_data, each_record):
        ks_rec_failed_list = []
        try:
            woo_tag_response = wcapi.put("products/tags/%s" % each_record.ks_woo_id, json_data)
            if woo_tag_response.status_code in [200, 201]:
                status = 'success'
            else:
                status = 'failed'
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=each_record.ks_woo_id,
                                                         ks_status=status,
                                                         ks_type='tags',
                                                         ks_woo_instance_id=each_record.ks_woo_instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='update',
                                                         response='Tag [' + each_record.ks_name + '] has been succesfully updated' if status == 'success' else 'The update operation failed for Tag [' + each_record.ks_name + '] due to ' + eval(woo_tag_response.text).get('message'))
            if status == 'success':
                each_record.ks_sync_date = datetime.datetime.now()
                each_record.ks_last_exported_date = each_record.ks_sync_date
                each_record.sync_update()
            else:
                if each_record.id not in ks_rec_failed_list:
                    ks_rec_failed_list.append(each_record)
        except ConnectionError:
            self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=each_record.ks_woo_instance_id,
                                                                type='tags',
                                                                operation='odoo_to_woo',
                                                                ks_woo_id=each_record.ks_woo_id)
        except Exception as e:
            if each_record.id not in ks_rec_failed_list:
                ks_rec_failed_list.append(each_record)
            self.env['ks.woo.sync.log'].ks_exception_log(record=each_record, type="customer",
                                                         operation_type="update", instance_id=each_record.ks_woo_instance_id,
                                                         operation="odoo_to_woo", exception=e)
        return ks_rec_failed_list

    def ks_create_tag_on_woo(self, wcapi, json_data, each_record):
        ks_rec_failed_list = []
        try:
            woo_tag_response = wcapi.post("products/tags", json_data)
            ks_woo_id = False
            if woo_tag_response.status_code in [200, 201]:
                woo_tag_data = woo_tag_response.json()
                each_record.ks_slug = woo_tag_data.get('slug')
                each_record.ks_woo_id = woo_tag_data.get('id')
                ks_woo_id = woo_tag_data.get('id')
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=ks_woo_id,
                                                         ks_status='success' if woo_tag_response.status_code in [200,
                                                                                                              201] else 'failed',
                                                         ks_type='tags',
                                                         ks_woo_instance_id=each_record.ks_woo_instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='create',
                                                         response='Tag [' + each_record.ks_name + '] has been succesfully exported ' if woo_tag_response.status_code in [
                                                             200,
                                                             201] else 'The export operation failed for Tag [' + each_record.ks_name + '] due to ' + eval(
                                                             woo_tag_response.text).get('message'))
            if woo_tag_response.status_code in [200, 201]:
                each_record.ks_sync_date = datetime.datetime.now()
                each_record.ks_last_exported_date = each_record.ks_sync_date
                each_record.sync_update()
            else:
                if each_record.id not in ks_rec_failed_list:
                    ks_rec_failed_list.append(each_record)
            return ks_rec_failed_list if len(ks_rec_failed_list) > 0 else each_record
        except ConnectionError:
            self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=each_record.ks_woo_instance_id,
                                                                type='tags',
                                                                operation='odoo_to_woo')
        except Exception as e:
            if each_record.id not in ks_rec_failed_list:
                ks_rec_failed_list.append(each_record)
            self.env['ks.woo.sync.log'].ks_exception_log(record=each_record, type="tags",
                                                         operation_type="create", instance_id=each_record.ks_woo_instance_id,
                                                         operation="odoo_to_woo", exception=e)
        return ks_rec_failed_list

    # Added to queues
    def ks_manage_product_tags(self, each_record, instance_id):
        tag_exist_in_odoo = self.search([('ks_woo_id', '=', each_record.get('id')),
                                         ('ks_woo_instance_id', '=', instance_id.id)], limit=1)
        woo_formated_data = self._ks_prepare_woo_product_tag_data(each_record, instance_id)
        if tag_exist_in_odoo:
            tag_exist_in_odoo.write(woo_formated_data)
            ks_operation_type = 'update'
        else:
            tag_exist_in_odoo = self.create(woo_formated_data)
            ks_operation_type = 'create'
        self.env['ks.woo.sync.log'].create_log_param(
            ks_woo_id=each_record.get('id'),
            ks_status='success',
            ks_type='tags',
            ks_woo_instance_id=instance_id,
            ks_operation='woo_to_odoo',
            ks_operation_type=ks_operation_type,
            response='Tag [' + tag_exist_in_odoo.ks_name + '] has been succesfully created' if ks_operation_type == 'create' else 'Tag [' + tag_exist_in_odoo.ks_name + '] has been succesfully updated',
        )
        tag_exist_in_odoo.ks_sync_date = datetime.datetime.now()
        tag_exist_in_odoo.ks_last_exported_date = tag_exist_in_odoo.ks_sync_date
        tag_exist_in_odoo.sync_update()

    def ks_sync_product_tag_to_woo(self, wcapi, instance_id):
        multi_api_call = True
        per_page = 100
        page = 1
        while (multi_api_call):
            try:
                woo_tag_response = wcapi.get("products/tags", params={"per_page": per_page, "page": page})
                if woo_tag_response.status_code in [200, 201]:
                    all_woo_tag_records = woo_tag_response.json()
                    for each_record in all_woo_tag_records:
                        self.ks_manage_product_tags(each_record, instance_id)
                else:
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='failed',
                        ks_type='tags',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='fetch',
                        response=str(woo_tag_response.status_code) + eval(woo_tag_response.text).get('message'),
                    )
                total_api_calls = woo_tag_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                else:
                    multi_api_call = False
            except ConnectionError:
                self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                    type='tags',
                                                                    operation='woo_to_odoo')

    def _ks_prepare_woo_product_tag_data(self, json_data, instance_id):
        data = {
            "ks_name": json_data.get('name') or '',
            "ks_slug": json_data.get('slug') or '',
            "ks_description": json_data.get('description') or '',
            "ks_woo_id": json_data.get('id') or '',
            "ks_woo_instance_id": instance_id.id
        }
        return data

    def _ks_prepare_odoo_product_tag_data(self, record):
        data = {
            "name": record.ks_name,
            "slug": record.ks_slug or '',
            "description": record.ks_description or ''
        }
        return data

    def update_tag_on_odoo(self, json_data, instance_id):
        if json_data:
            tag_ids = []
            for each_tag in json_data:
                tag_exist_in_odoo = self.search([('ks_woo_id', '=', each_tag.get('id')),
                                                ('ks_woo_instance_id', '=', instance_id.id)], limit=1)
                woo_formated_data = self._ks_prepare_woo_product_tag_data(each_tag, instance_id)
                if tag_exist_in_odoo:
                    tag_exist_in_odoo.update({
                        'ks_name': each_tag.get('name'),
                        'ks_slug': each_tag.get('slug')
                    })
                    tag_ids.append(tag_exist_in_odoo.id)
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=each_tag.get('id'),
                        ks_status='success',
                        ks_type='tags',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='update',
                        response='Tag [' + tag_exist_in_odoo.ks_name + '] has been succesfully updated',
                    )
                else:
                    new_tag_record = self.create(woo_formated_data)
                    tag_ids.append(new_tag_record.id)
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=each_tag.get('id'),
                        ks_status='success',
                        ks_type='tags',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response='Tag [' + new_tag_record.ks_name + '] has been succesfully created',
                    )
            return tag_ids

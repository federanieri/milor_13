# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from requests.exceptions import ConnectionError
import datetime

from . import ks_json_data

ATTRIBUTE_DATA = ks_json_data.ATTRIBUTE_DATA
ATTRIBUTE_VALUE_DATA = ks_json_data.ATTRIBUTE_VALUE_DATA


class KsProductAttributeInherit(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin', 'product.attribute']
    _name = 'product.attribute'

    ks_woo_id = fields.Integer('WooCommerce Id', readonly=True, default=0, track_visibility='onchange')
    ks_slug = fields.Char('Slug')
    ks_export_in_wo = fields.Boolean('Exported in woo', readonly=True, compute='_compute_export_in_woo', store=True)
    ks_woo_instance_id = fields.Many2one('ks.woocommerce.instances', 'Woo Instance', track_visibility='onchange')
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
        super(KsProductAttributeInherit, self).write(values)

    # To show the product attributes are exported in woo
    @api.depends('ks_woo_id')
    def _compute_export_in_woo(self):
        for rec in self:
            rec.ks_export_in_wo = bool(rec.ks_woo_id)

    def create_json_data(self):
        for rec in self:
            json_data = rec._create_json_data(ATTRIBUTE_DATA)
            return json_data

    def create_woo_json_data(self, woo_attribute_data):
        json_data = self._create_data_from_json(ATTRIBUTE_DATA, woo_attribute_data)
        return json_data

    @api.model
    def ks_update_product_attribute_to_odoo(self):
        ks_rec_failed_list = []
        for rec in self:
            instance_id = self.env['ks.woocommerce.instances'].search([('id', '=', rec.ks_woo_instance_id.id)], limit=1)
            if instance_id.ks_instance_state == 'active':
                try:
                    wcapi = rec.ks_woo_instance_id.ks_api_authentication()
                    if wcapi.get("").status_code in [200, 201]:
                        attribute_response = wcapi.get("products/attributes/%s" % rec.ks_woo_id)
                        if attribute_response.status_code in [200, 201]:
                            rec.ks_update_product_attribute_from_woo(attribute_response.json(), wcapi, instance_id)
                        else:
                            if rec.id not in ks_rec_failed_list:
                                ks_rec_failed_list.append(rec)
                            self.env['ks.woo.sync.log'].create_log_param(
                                ks_woo_id=False,
                                ks_status='failed',
                                ks_type='attribute',
                                ks_woo_instance_id=instance_id,
                                ks_operation='woo_to_odoo',
                                ks_operation_type='fetch',
                                response=str(attribute_response.status_code) + eval(attribute_response.text).get('message'),
                            )
                except ConnectionError:
                    self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id, type='attribute',
                                                                        operation='woo_to_odoo')
                except Exception as e:
                    if rec.id not in ks_rec_failed_list:
                        ks_rec_failed_list.append(rec)
                    self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="attribute_value",
                                                                 operation_type="import", instance_id=instance_id,
                                                                 operation="woo_to_odoo", exception=e)
            else:
                return 'error'

        return ks_rec_failed_list


    def ks_update_product_attribute_to_odoo_wizard(self):
        ks_failed_instance_list = []
        ks_failed_product_id = []
        for rec in self:
            ks_failed_list = rec.ks_update_product_attribute_to_odoo()
            if ks_failed_list == 'error':
                format_info = 'The instance must be in active state or instance field should be updated to perform the operations'
                format_string = ks_message_string = ''
                log = 'Import Status'
            else:
                for record in ks_failed_list:
                    ks_failed_product_id.append(record.name)
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


    # Sync the product attribute and its values from woo to Odoo (Create and Update)
    def ks_sync_product_attribute_woocommerce(self, wcapi, instance_id):
        try:
            attribute_response = wcapi.get("products/attributes")
            if attribute_response.status_code in [200, 201]:
                all_woo_attributes_records = attribute_response.json()
                for each_record in all_woo_attributes_records:
                    self.ks_update_product_attribute_from_woo(each_record, wcapi, instance_id)
            else:
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='failed',
                    ks_type='attribute',
                    ks_woo_instance_id=instance_id,
                    ks_operation='woo_to_odoo',
                    ks_operation_type='fetch',
                    response=str(attribute_response.status_code) + eval(attribute_response.text).get('message'),
                )
        except ConnectionError:
            self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id, type='attribute',
                                                                operation='woo_to_odoo')

    def ks_create_update_attribute(self, each_record, attribute_values, instance_id, attribute_value_response, product_data=False):
        attr_exist_in_odoo = self.search([('ks_woo_id', '=', each_record.get('id')),
                                          ('ks_woo_instance_id', '=', instance_id.id)], limit=1)
        woo_formated_data = self._prepare_woo_product_attribute_data(each_record)
        woo_attr_data = self.create_woo_json_data(woo_formated_data)
        try:
            if each_record:
                if attr_exist_in_odoo:
                    attr_exist_in_odoo.write(woo_attr_data)
                    ks_operation_type = 'update'
                    current_att = attr_exist_in_odoo  # update that attribute
                else:
                    current_att = self.create(woo_attr_data)
                    ks_operation_type = 'create'
                    current_att.ks_woo_id = each_record.get('id')
                    current_att.ks_woo_instance_id = instance_id.id

                current_att.ks_sync_date = datetime.datetime.now()
                current_att.ks_last_exported_date = current_att.ks_sync_date
                current_att.sync_update()

                if current_att:
                    attr_val = []
                    # current_att.update({'value_ids': False})
                    for each_atr_val in attribute_values:
                        attr_val_exist_in_odoo = self.env['product.attribute.value'].search(
                            [('ks_woo_id', '=', each_atr_val.get('ks_woo_id')),
                             ('attribute_id', '=', current_att.id)])
                        each_atr_val.update({'attribute_id': current_att.id})
                        if attr_val_exist_in_odoo:
                            # attr_val_exist_in_odoo.update({
                            #     'name': each_atr_val.get('name'),
                            #     'ks_slug': each_atr_val.get('ks_slug'),
                            # })
                            attr_val.append(attr_val_exist_in_odoo.id)
                            operation_type = 'update'
                        else:
                            attr_val_exist_in_odoo = self.env['product.attribute.value'].create(each_atr_val)
                            attr_val.append(attr_val_exist_in_odoo.id)
                            operation_type = 'create'
                        self.env['ks.woo.sync.log'].create_log_param(
                            ks_woo_id=current_att.ks_woo_id,
                            ks_status='success',
                            ks_type='attribute_value',
                            ks_woo_instance_id=instance_id,
                            ks_operation='woo_to_odoo',
                            ks_operation_type=operation_type,
                            response='Attribute value [' + attr_val_exist_in_odoo.name + '] of Attribute [' + current_att.name + '] has been succesfully created' if operation_type == 'create' else 'Attribute value [' + attr_val_exist_in_odoo.name + '] of Attribute [' + current_att.name + '] has been succesfully updated',
                        )
                    current_att.update({'value_ids': attr_val})
                    # if product_data:
                    #     product_data.attribute_line_ids.value_ids = attr_val
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=current_att.ks_woo_id,
                    ks_status='success',
                    ks_type='attribute',
                    ks_woo_instance_id=instance_id,
                    ks_operation='woo_to_odoo',
                    ks_operation_type=ks_operation_type,
                    response='Attribute [' + current_att.name + '] has been succesfully created' if ks_operation_type == 'create' else 'Attribute [' + current_att.name + '] has been succesfully updated',
                )
            else:
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='failed',
                    ks_type='attribute_value',
                    ks_woo_instance_id=instance_id,
                    ks_operation='woo_to_odoo',
                    ks_operation_type='fetch',
                    response=str(attribute_value_response.status_code) + eval(attribute_value_response.text).get(
                        'message'),
                )
        except ConnectionError:
            self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id, type='attribute_value',
                                                                operation='woo_to_odoo')

    def ks_update_product_attribute_from_woo(self, each_record, wcapi, instance_id, product_data=False):
        ks_rec_failed_list = []
        multi_api_call = True
        per_page = 100
        page = 1
        attribute_values = []
        while (multi_api_call):
            try:
                attribute_value_response = wcapi.get("products/attributes/%s/terms" % each_record.get('id'),
                                                     params={"per_page": per_page, "page": page})
                if attribute_value_response.status_code in [200, 201]:
                    all_woo_attr_value_records = attribute_value_response.json()
                    if all_woo_attr_value_records:
                        woo_attr_val_data = self._prepare_woo_product_attribute_value_data(all_woo_attr_value_records)
                    else:
                        woo_attr_val_data = []
                    attribute_values.extend(woo_attr_val_data)
                total_api_calls = attribute_value_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                else:
                    multi_api_call = False
            except ConnectionError:
                self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id, type='attribute_value',
                                                                    operation='woo_to_odoo')
            except Exception as e:
                if each_record.id not in ks_rec_failed_list:
                    ks_rec_failed_list.append(each_record)
                self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="attribute_value",
                                                             operation_type="import", instance_id=instance_id,
                                                             operation="woo_to_odoo", exception=e)
        if len(attribute_values) > 0:
            self.ks_create_update_attribute(each_record, attribute_values, instance_id, attribute_value_response, product_data)

    # Export the new product attribute from odoo to Woo
    # Added to queue
    def ks_update_product_attribute_to_woo(self):
        ks_rec_failed_list = []
        for rec in self:
            if rec.ks_woo_instance_id and rec.ks_woo_instance_id.ks_instance_state == 'active':
                json_data = rec.create_json_data()
                data = rec._prepare_product_attribute_data(json_data)
                try:
                    wcapi = rec.ks_woo_instance_id.ks_api_authentication()
                    if wcapi.get('').status_code in [200, 201]:
                        if rec.ks_woo_id and rec.ks_woo_id != -1:
                            record_exist_status = wcapi.get("products/attributes/%s" % rec.ks_woo_id)
                            if record_exist_status.status_code == 404:
                                self.ks_create_attribute_on_woo(wcapi, data, json_data, rec, rec.ks_woo_instance_id)
                            else:
                                woo_product_attribute_response = wcapi.put("products/attributes/%s" % rec.ks_woo_id,
                                                                           data)
                                if woo_product_attribute_response.status_code in [200, 201]:
                                    status = 'success'
                                    woo_product_attribute_record = woo_product_attribute_response.json()
                                    self.ks_manage_attribute_values(wcapi, woo_product_attribute_record, json_data, rec)
                                    rec.ks_slug = woo_product_attribute_record.get('slug')
                                else:
                                    status = 'failed'
                                self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=rec.ks_woo_id,
                                                                             ks_status=status,
                                                                             ks_type='attribute',
                                                                             ks_woo_instance_id=rec.ks_woo_instance_id,
                                                                             ks_operation='odoo_to_woo',
                                                                             ks_operation_type='update',
                                                                             response='Attribute [' + rec.name + '] has been succesfully updated' if status == 'success' else 'The update operation failed for Attribute [' + rec.name + '] due to ' + eval(
                                                                                 woo_product_attribute_response.text).get(
                                                                                 'message'))
                                rec.ks_sync_date = datetime.datetime.now()
                                rec.ks_last_exported_date = rec.ks_sync_date
                                rec.sync_update()

                        else:
                            if rec.ks_woo_id == -1:
                                self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=rec.ks_woo_id,
                                                                             ks_status='failed',
                                                                             ks_type='attribute',
                                                                             ks_woo_instance_id=rec.ks_woo_instance_id,
                                                                             ks_operation='odoo_to_woo',
                                                                             ks_operation_type='update',
                                                                             response="The attribute [" + rec.name + "] update is failed because private attribute cannot be updated.")
                                if rec.id not in ks_rec_failed_list:
                                    ks_rec_failed_list.append(rec)
                            else:
                                self.ks_create_attribute_on_woo(wcapi, data, json_data, rec, rec.ks_woo_instance_id)
                    else:
                        self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                                     ks_status='success' if wcapi.get(
                                                                         "").status_code in [
                                                                                                200,
                                                                                                201] else 'failed',
                                                                     ks_type='system_status',
                                                                     ks_woo_instance_id=rec.ks_woo_instance_id,
                                                                     ks_operation='odoo_to_woo',
                                                                     ks_operation_type='connection',
                                                                     response='Connection successful' if wcapi.get(
                                                                         "").status_code in [200, 201] else wcapi.get(
                                                                         "").text)
                except ConnectionError:
                    self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=rec.ks_woo_instance_id,
                                                                        type='attribute',
                                                                        operation='odoo_to_woo',
                                                                        ks_woo_id=rec.ks_woo_id)
                except Exception as e:
                    if rec.id not in ks_rec_failed_list:
                        ks_rec_failed_list.append(rec)
                    self.env['ks.woo.sync.log'].ks_exception_log(record=rec, type="attribute",
                                                                 operation_type="create" if rec.ks_woo_id else "update",
                                                                 instance_id=rec.ks_woo_instance_id,
                                                                 operation="odoo_to_woo", exception=e)
            else:
                self.env['ks.woo.sync.log'].ks_no_instance_log(rec, 'attribute')
                return 'error'
        return ks_rec_failed_list

    def ks_update_product_attribute_to_woo_wizard(self):
        ks_failed_instance_list = []
        ks_failed_product_id = []
        for rec in self:
            ks_failed_list = rec.ks_update_product_attribute_to_woo()
            if ks_failed_list == 'error':
                format_info = 'The instance must be in active state or instance field should be updated to perform the operations'
                format_string = ks_message_string = ''
                log = 'Export Status'
            else:
                for record in ks_failed_list:
                    ks_failed_product_id.append(record.name)
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

    def ks_create_attribute_on_woo(self, wcapi, data, json_data, rec, instance_id):
        try:
            woo_product_attribute_response = wcapi.post("products/attributes", data)
            ks_woo_id = False
            if woo_product_attribute_response.status_code in [200, 201]:
                woo_product_attribute_record = woo_product_attribute_response.json()
                self.ks_manage_attribute_values(wcapi, woo_product_attribute_record, json_data, rec)
                rec.ks_woo_id = ks_woo_id = woo_product_attribute_record.get('id')
                rec.ks_slug = woo_product_attribute_record.get('slug')
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=ks_woo_id,
                                                         ks_status='success' if woo_product_attribute_response.status_code in [
                                                             200,
                                                             201] else 'failed',
                                                         ks_type='attribute',
                                                         ks_woo_instance_id=rec.ks_woo_instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='create',
                                                         response='Attribute [' + rec.name + '] has been succesfully exported ' if woo_product_attribute_response.status_code in [
                                                             200,
                                                             201] else 'The export operation failed for Attribute [' + rec.name + '] due to ' + eval(
                                                             woo_product_attribute_response.text).get('message'))
            if woo_product_attribute_response.status_code in [
                200,
                201]:
                rec.ks_sync_date = datetime.datetime.now()
                rec.ks_last_exported_date = rec.ks_sync_date
                rec.sync_update()
        except ConnectionError:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_status='failed',
                                                         ks_type='system_status',
                                                         ks_woo_instance_id=instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='connection',
                                                         response="Couldn't Connect the Instance[ %s ] at time of Attribute "
                                                                  "Updation !! Please check the network connectivity"
                                                                  " or the configuration parameters are not "
                                                                  "correctly set" % instance_id.ks_name)

    def ks_manage_attribute_values(self, wcapi, woo_product_attribute_record, json_data, rec):
        if json_data[0].get('product_attribute_value'):
            current_attribute_id = woo_product_attribute_record.get('id')
            rec.ks_woo_id = woo_product_attribute_record.get('id')
        for each_value in json_data[0].get('product_attribute_value'):
            odoo_att_value_record = self.env['product.attribute.value'].search(
                [('id', '=', each_value.get('id'))])
            woo_attribute_value_data = rec._prepare_product_attribute_values_data(each_value)
            if odoo_att_value_record.ks_woo_id:
                try:
                    record_exist_status = wcapi.get("products/attributes/%s/terms/%s" % (
                        current_attribute_id, odoo_att_value_record.ks_woo_id))
                    if record_exist_status.status_code == 404:
                        self.ks_create_attribute_val_on_woo(wcapi, current_attribute_id, woo_attribute_value_data,
                                                            odoo_att_value_record, rec.ks_woo_instance_id)
                    else:
                        self.ks_update_attribute_val_on_woo(wcapi, current_attribute_id, woo_attribute_value_data,
                                                            odoo_att_value_record, rec.ks_woo_instance_id)
                except ConnectionError:
                    self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=rec.ks_woo_instance_id,
                                                                        type='attribute',
                                                                        operation='odoo_to_woo',
                                                                        ks_woo_id=rec.ks_woo_id)
            else:
                self.ks_create_attribute_val_on_woo(wcapi, current_attribute_id, woo_attribute_value_data,
                                                    odoo_att_value_record, rec.ks_woo_instance_id)

    def ks_create_attribute_val_on_woo(self, wcapi, current_attribute_id, woo_attribute_value_data,
                                       odoo_att_value_record, instance_id):
        try:
            each_attr_value_response = wcapi.post("products/attributes/%s/terms" % current_attribute_id,
                                                  woo_attribute_value_data)
            ks_woo_id = False
            if each_attr_value_response.status_code in [200, 201]:
                odoo_att_value_record.ks_woo_id = ks_woo_id = each_attr_value_response.json().get('id')
                odoo_att_value_record.ks_slug = each_attr_value_response.json().get('slug')
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=ks_woo_id,
                                                         ks_status='success' if each_attr_value_response.status_code in [
                                                             200,
                                                             201] else 'failed',
                                                         ks_type='attribute_value',
                                                         ks_woo_instance_id=odoo_att_value_record.attribute_id.ks_woo_instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='create',
                                                         response='Attribute value [' + odoo_att_value_record.name + '] of Attribute [' + odoo_att_value_record.attribute_id.name + ']  has been succesfully exported ' if each_attr_value_response.status_code in [
                                                             200,
                                                             201] else 'The export operation failed for Attribute value [' + odoo_att_value_record.name + '] of Attribute [' + odoo_att_value_record.attribute_id.name + ']  due to ' + eval(
                                                             each_attr_value_response.text).get('message'))
        except ConnectionError:
            self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                type='attribute_value',
                                                                operation='odoo_to_woo')

    def ks_update_attribute_val_on_woo(self, wcapi, current_attribute_id, woo_attribute_value_data,
                                       odoo_att_value_record, instance_id):
        try:
            each_attr_value_response = wcapi.put("products/attributes/%s/terms/%s" % (
                current_attribute_id, odoo_att_value_record.ks_woo_id),
                                                 woo_attribute_value_data)
            if each_attr_value_response.status_code in [200, 201]:
                odoo_att_value_record.ks_slug = each_attr_value_response.json().get('slug')
                status = 'success'
            else:
                status = 'failed'
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=odoo_att_value_record.ks_woo_id,
                                                         ks_status=status,
                                                         ks_type='attribute_value',
                                                         ks_woo_instance_id=odoo_att_value_record.attribute_id.ks_woo_instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='update',
                                                         response='Attribute value [' + odoo_att_value_record.name + '] of Attribute [' + odoo_att_value_record.attribute_id.name + '] has been succesfully updated' if status == 'success' else 'The update operation failed for Attribute value [' + odoo_att_value_record.name + '] of Attribute [' + odoo_att_value_record.attribute_id.name + '] due to ' + eval(
                                                             each_attr_value_response.text).get('message'))
        except ConnectionError:
            self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                type='attribute_value',
                                                                operation='odoo_to_woo')

    def _prepare_product_attribute_data(self, json_data):
        data = {
            "name": json_data[0].get('name'),
            "slug": json_data[0].get('ks_slug') if json_data[0].get('ks_slug') else json_data[0].get('name') or '',
        }
        return data

    def _prepare_product_attribute_values_data(self, json_data):
        data = {
            'name': json_data.get('value'),
            "slug": json_data.get('ks_slug') if json_data.get('ks_slug') else json_data.get('name') or '',
        }
        return data

    # Prepare Woo Product Atrribute Data for woo to Odoo
    def _prepare_woo_product_attribute_data(self, json_data):
        data = {
            "name": json_data.get('name'),
            "ks_slug": json_data.get('slug') or '',
            "display_type": json_data.get('display_type'),
            'test':'test'
        }
        return data

    def _prepare_woo_product_attribute_value_data(self, json_data):
        data = []
        for rec in json_data:
            data.append({
                "ks_woo_id": rec.get('id'),
                "name": rec.get('name'),
                "ks_slug": rec.get('slug') or ''
            })
        return data


class KsProductAttributeValuesInherit(models.Model):
    _inherit = 'product.attribute.value'

    ks_woo_id = fields.Integer('WooCommerce Id', readonly=True)
    ks_slug = fields.Char('Slug')
    ks_export_in_wo = fields.Boolean('Exported in woo', readonly=True, compute='_compute_export_in_woo', store=True)

    _sql_constraints = [
        ('value_company_uniq', 'unique (id)',
         "You cannot create two values with the same name for the same attribute.")
    ]

    # To show the product attribute values are exported in woo
    @api.depends('ks_woo_id')
    def _compute_export_in_woo(self):
        for rec in self:
            rec.ks_export_in_wo = bool(rec.ks_woo_id)

    @api.model
    def create(self, vals):
        ks_value_name = list(self.env['product.attribute.value'].search([]).mapped('name'))
        ks_value_ks_woo_id = list(self.env['product.attribute.value'].search([]).mapped('ks_woo_id'))
        ks_value_attribute_id = list(self.env['product.attribute.value'].search([]).mapped('attribute_id'))
        ks_value_ks_slug = list(self.env['product.attribute.value'].search([]).mapped('ks_slug'))
        if vals.get('name') in ks_value_name and vals.get('attribute_id') in ks_value_attribute_id and vals.get('ks_slug') in \
                ks_value_ks_slug and vals.get('ks_woo_id') in ks_value_ks_woo_id:
            raise ValidationError(
                _("You cannot create two values with the same name for the same attribute and same slug."))
        else:
            return super(KsProductAttributeValuesInherit, self).create(vals)
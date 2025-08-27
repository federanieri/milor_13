# -- coding: utf-8 --
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
import json
import os
import gc
import ftplib
import fnmatch
import io
import re
from odoo import fields, models, _, api
from odoo.exceptions import UserError
from datetime import datetime
import xml.etree.ElementTree as ET
import requests
from xml.dom import minidom
from odoo.tools.safe_eval import safe_eval
import xmltodict
from os import listdir
from os.path import isfile, join


class NaApiSyncConfig(models.Model):
    _name = 'na.api.sync.config'

    name = fields.Char(string='Name', required=True)
    env_id = fields.Many2one('na.api.sync.env', string='Environment', required=True)
    type = fields.Selection(selection=[('fc', 'Fields Configuration'),
                                       ('con', 'Connect to external API'),
                                       ('exp', 'Expose API from Odoo'),
                                       ('both', 'Connect to external API and expose from Odoo'),
                                       ('import_feed', 'Import from Data Feed'),
                                       ('export_feed', 'Export Data Feed')],
                            string='Type', required=True)
    api_tag = fields.Char(string='API Tag', help='Tag used to identify the API exposed by Odoo'
                                                 ' when called, if not set the API will not be callable via XML-RPC.'
                                                 'This field cannot contain spaces.')
    model_id = fields.Many2one('ir.model', string='Model', ondelete='cascade', required=True)
    model_name = fields.Char(string='Model Name', related='model_id.model')
    record_domain = fields.Char(string='Domain Value')
    get_endpoint = fields.Char(string='Endpoint GET')
    post_endpoint = fields.Char(string='Endpoint POST')
    feed_url = fields.Char(string='Feed URL')
    feed_suffix = fields.Char(string='Feed Suffix')
    feed_format = fields.Selection(selection=[('json', 'JSON'), ('xml', 'XML')],
                                   string='Feed Format')
    feed_xml_root_tag = fields.Char(string='XML Root Tag',
                                    help='Root tag, which will contain all the information.')
    feed_xml_element_tag = fields.Char(
        string='XML Element Tag',
        help='In case only one element is passed, insert only the element tag and not the root.')
    feed_data_exchange_mode = fields.Selection(selection=[('api', 'API'), ('ftp', 'FTP')],
                                               string='Feed Data Exchange Mode')
    feed_file_path = fields.Char(string='Feed File Path')
    feed_file_name = fields.Char(string='Feed File Name')
    feed_file_name_add_date = fields.Boolean(string='Add Date to Name')
    feed_file_name_date = fields.Char(
        string='Date Format',
        help='Enter the date format that will be added to the file name, for example: %Y-%m-%d')
    # TODO: Il download sincrono, quindi quando si lancia la funzione _run_api_sync non è implementato
    feed_file_async_get = fields.Boolean(string='Async Feed File Download', help='Download Feed File with a dedicated routine,'
                                                                              ' helpful for large files')
    feed_file_keep = fields.Boolean(string='Keep just most recent file', help='Keeps just more recent feed file.')
    feed_latest_dl_file = fields.Char(string='Latest Downloaded Feed File')
    api_fields_ids = fields.One2many('na.api.sync.config.fields', 'config_id',
                                     string='Definition Fields')
    api_actions_ids = fields.One2many('na.api.sync.config.actions', 'config_id',
                                      string='API Actions')
    return_json = fields.Boolean('Return JSON', help='Does not automatically import data but'
                                                     '_run_api_sync returns JSON response to be'
                                                     ' elaborated externally (for instance do some'
                                                     ' work and then import with import_record'
                                                     ' function')
    advanced_field_management = fields.Boolean(
        string='Advanced Field Management', copy=False, default=False,
        help='Activating this flag enables advanced field management, '
             'which allows for precise manipulation of data.')
    ftp_hostname = fields.Char('FTP Hostname')
    ftp_username = fields.Char('FTP Username')
    ftp_password = fields.Char('FTP Password')
    ftp_folder = fields.Char('FTP Folder')

    autoremove = fields.Boolean(
        'Auto. Remove Files',
        help='If you check this option you can choose to automaticly remove the files after xx days')
    days_to_keep = fields.Integer(
        'Remove after x days',
        help="Choose after how many days the files should be deleted. For example:\nIf you fill in 5 the files will be removed after 5 days.",
        required=True)
    remove_feed_file_name = fields.Char(string='To Remove Feed File Name')

    _sql_constraints = [
        ('check_api_tag', 'UNIQUE (api_tag)', 'This API Tag already exists.')
    ]

    def _cron_autoremove_files(self):
        feeds = self.search([('type', '=', 'import_feed')])
        for rec in feeds:
            if rec.autoremove:
                directory = rec.feed_file_path
                # Loop over all files in the directory.
                for f in os.listdir(directory):
                    fullpath = os.path.join(directory, f)
                    # Only delete the ones wich are from the current database
                    # (Makes it possible to save different databases in the same folder)
                    if rec.remove_feed_file_name in fullpath:
                        timestamp = os.stat(fullpath).st_ctime
                        createtime = datetime.fromtimestamp(timestamp)
                        now = datetime.now()
                        delta = now - createtime
                        if delta.days >= rec.days_to_keep:
                            # Only delete files (which are .dump and .zip), no directories.
                            if os.path.isfile(fullpath) and (".xml" in f or '.XML' in f):
                                os.remove(fullpath)
                                self.env['na.api.sync.log'].create({
                                    'env_id': rec.env_id.id,
                                    'config_id': rec.id,
                                    'log_msg': f"Old file deleted: {fullpath}"
                                })

    def _cron_download_async_feed(self):
        feeds = self.search([('type', '=', 'import_feed'), ('feed_file_async_get', '=', True)])
        for f in feeds:
            f.download_feed_file(mode=f.feed_data_exchange_mode)

    def download_feed_file(self, mode, full_url=None):
        write_list = []

        if self.feed_file_keep and self.feed_latest_dl_file:
            file_path = os.path.join(self.feed_file_path, self.feed_latest_dl_file)
            # Controlla se il percorso è un file
            if os.path.isfile(file_path):
                # Elimina il file
                os.remove(file_path)
                self.env['na.api.sync.log'].create({
                    'env_id': self.env_id.id,
                    'config_id': self.id,
                    'log_msg': f"File deleted: {file_path}"
                })
        if mode == 'api':
            if not full_url:
                full_url = self.feed_url + self.feed_suffix
            response = requests.get(full_url, stream=True)
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        write_list.append(chunk)

                # Extract the filename from the URL
                filename = full_url.split('/')[-1]
                # Combine the folder path and filename
                file_path = os.path.join(self.feed_file_path, filename)
                # Write the content of the response to the file
                with open(file_path, 'wb') as f:
                    # Read and write the file in chunks
                    for chunk in write_list:
                        f.write(chunk)
                    # Close the file and progress bar
                    f.close()
                self.feed_latest_dl_file = filename
                self.env['na.api.sync.log'].create({
                    'env_id': self.env_id.id,
                    'config_id': self.id,
                    'log_msg': f"File downloaded and saved as: {file_path}"
                })
            else:
                self.env['na.api.sync.log'].create({
                    'env_id': self.env_id.id,
                    'config_id': self.id,
                    'log_msg': f"Failed to download file: {response.status_code}"
                })
        elif mode == 'ftp':
            ftp = ftplib.FTP(self.ftp_hostname, self.ftp_username, self.ftp_password)

            ftp.cwd(self.ftp_folder)

            # List all files in the directory
            files = ftp.nlst()

            # Iterate over the files and read each one
            for file in files:
                if fnmatch.fnmatch(file, '*.XML') or fnmatch.fnmatch(file, '*.xml'):
                    file_path = os.path.join(self.feed_file_path, file)
                    ftp_response = ftp.retrbinary(f'RETR {file}', open(file_path, 'wb').write)
                    if '226' in ftp_response:
                        self.feed_latest_dl_file = file
                        self.env['na.api.sync.log'].create({
                            'env_id': self.env_id.id,
                            'config_id': self.id,
                            'log_msg': f"File downloaded and saved as: {file_path}"
                        })
                        ftp.delete(file)
                    else:
                        self.env['na.api.sync.log'].create({
                            'env_id': self.env_id.id,
                            'config_id': self.id,
                            'log_msg': f"Failed to download file: {file_path}\n"
                                       f"Response: {ftp_response}"
                        })

            ftp.quit()

    def xml_to_dict(self, element=None, file_path=None):
        # function to transform a file XML into a dictionary
        # if the element is passed check that directly,
        # if it is not passed go get the xml file in the folder where it is saved
        file_paths = []

        # file_path = '/home/utente/Downloads/Milor/TestFiles/Import/RMGLCATES_20240720175026948.XML'
        if element is None:
            if not file_path:
                for file in [f for f in listdir(self.feed_file_path) if isfile(join(self.feed_file_path, f))]:
                    if fnmatch.fnmatch(file, '*.XML') or fnmatch.fnmatch(file, '*.xml'):
                        file_path = os.path.join(self.feed_file_path, file)
                        file_paths.append(file_path)

        if not file_paths:
            file_paths.append(file_path)
        # read the file and transform it in a dict
        xml_dicts = []
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    my_xml = file.read()
                xml_dict = xmltodict.parse(my_xml)
                # clean the dict
                root_tag = self.feed_xml_root_tag
                element_tag = self.feed_xml_element_tag
                if root_tag:
                    xml_dict = xml_dict[root_tag]
                if element_tag:
                    xml_dict = xml_dict[element_tag]
                xml_dicts.append(xml_dict)

            except Exception as e:
                self.env['na.api.sync.log'].create({
                    'env_id': self.env_id.id,
                    'config_id': self.id,
                    'log_msg': f"There was an exception while handling the data feed: {e}"
                })
        return xml_dicts

    def parse_string(self, string):
        string = re.sub('&lt;', '<', string)
        string = re.sub('&gt;', '>', string)
        return string

    def pretty_print(self, elem):
        # function to verify the xml
        rough_string = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        reparsed = reparsed.toprettyxml(indent="  ")
        reparsed = self.parse_string(reparsed)
        return reparsed

    def dict_to_xml(self, data_array, elem_tag=None, root_tag=None):
        # TODO verificare se è necessaria l'aggiunta di un Header
        root = elem = None
        # get all values related to tags and Header,
        # if they are passed as function parameters then prioritize those
        root_tag = root_tag or self.feed_xml_root_tag
        elem_tag = elem_tag or self.feed_xml_element_tag
        # if there is more than one element, but the root tag is not passed we cannot create the xml
        if len(data_array) > 1 and not root_tag:
            self.env['na.api.sync.log'].create({
                'env_id': self.env_id.id,
                'config_id': self.id,
                'log_msg': "Multiple elements were passed, but the root tag is missing."
            })
            return None
        # then add the root tag
        if root_tag:
            root = ET.Element(root_tag)
        for data in data_array:
            # for each element of the dictionary array creates the parent tag
            elem = ET.Element(elem_tag)
            for key, val in data.items():
                child = None
                if isinstance(val, list):
                    try:
                        # adds the information based on the sub-configuration
                        config = val[0]
                        config_root = config.feed_xml_root_tag
                        config_elem = config.feed_xml_element_tag
                        sub_dict = val[1] if isinstance(val[1], list) else [val[1]]
                        # that way if there are multiple elements, without the root tag
                        # we can handle them without any problems
                        if len(sub_dict) > 1 and not config_root:
                            for d in sub_dict:
                                child = config.dict_to_xml([d], config_elem, config_root)
                                elem.append(child)
                        else:
                            child = config.dict_to_xml(
                                sub_dict, config_elem, config_root)
                            elem.append(child)
                    except Exception as e:
                        pass
                # add each dict
                if child is None:
                    child = ET.Element(key)
                    child.text = str(val)
                    elem.append(child)
            if root is not None:
                root.append(elem)
        # return the root or the elem, root in case the array > 1, elem in the other
        return root or elem

    def export_feed_file(self, record_ids=None):
        try:
            model = self.model_id.model
            if not record_ids:
                domain = []
                record_domain = self.record_domain
                if record_domain:
                    domain = domain + safe_eval(record_domain)
                record_ids = self.env[model].search(domain).ids
            api_fields = self.api_fields_ids
            # get the records that we have to send
            records = self.env[model].browse(record_ids)
            data = []
            # for each record that we have to send create a dict
            for record in records:
                data_dict = self.export_record(record, api_fields)
                # append the whole record information to the list
                data.append(data_dict)
            final_data = None
            if self.feed_format == 'xml':
                # through this function transforms the data dictionary into an XML
                xml = self.dict_to_xml(data)
                if xml is None:
                    return None
                final_data = xml
                # through this function the xml element is transformed into a readable string
                xml_print = self.pretty_print(xml)
                self.env['na.api.sync.log'].create({
                    'env_id': self.env_id.id,
                    'config_id': self.id,
                    'log_msg': f"Information created:\n {str(xml_print)}"
                })
            return final_data
        except Exception as e:
            self.env['na.api.sync.log'].create({
                'env_id': self.env_id.id,
                'config_id': self.id,
                'log_msg': f"There was an exception while getting the information: {e}"
            })
            return None

    def get_file_name(self, file_name=None):
        # function that returns the name of a file,
        # purposefully made so that it can be inherited and forced the desired value
        if file_name:
            return file_name
        file_name = self.feed_file_name
        if self.feed_file_name_add_date:
            now = datetime.now()
            now_str = now.strftime(self.feed_file_name_date)
            file_name = file_name + now_str
        return file_name

    def management_data_feed(self, records_ids=None):
        try:
            # this function handles data feeds, whether they are to be exported
            # or imported based on the record configurations
            for record in self:
                operation_type = record.type
                # IMPORT FEED
                if operation_type == 'import_feed':
                    if record.feed_format == 'xml':
                        return record.xml_to_dict()
                    # TODO: add feed_format == 'json'
                # EXPORT FEED
                elif operation_type == 'export_feed':
                    final_data = record.export_feed_file(records_ids)
                    if final_data is None:
                        return
                    if record.feed_data_exchange_mode == 'ftp':
                        ftp = ftplib.FTP(
                            record.ftp_hostname, record.ftp_username, record.ftp_password)

                        ftp.cwd(record.ftp_folder)
                        # you get the path and file name,
                        # then based on the file type you add the extension
                        # folder_path = record.feed_file_path
                        filename = record.get_file_name()
                        if record.feed_format == 'xml':
                            filename += '.xml'
                            # file_path = os.path.join(folder_path, filename)
                            # saves the xml in the final path
                            xml_str = ET.tostring(final_data, encoding='utf-8', method='xml')
                            xml_str = xml_str.decode('utf-8')
                            xml_str = self.parse_string(xml_str)
                            bio = io.BytesIO(xml_str.encode())

                            ftp.storbinary(f"STOR {filename}", bio)
                        ftp.quit()
                    return True
        except Exception as e:
            self.env['na.api.sync.log'].create({
                'env_id': self.env_id.id,
                'config_id': self.id,
                'log_msg': f"There was an exception while handling the data feed: {e}"
            })
            return None

    @api.onchange('type')
    def _check_type(self):
        for rec in self:
            if ((rec.type == 'both' and rec.env_id.api_type in
                 ['con', 'exp', 'import_feed', 'export_feed']) or
                    (rec.type == 'con' and rec.env_id.api_type in
                     ['exp', 'import_feed', 'export_feed']) or
                    (rec.type == 'exp' and rec.env_id.api_type in
                     ['con', 'import_feed', 'export_feed'])):
                raise UserError(_('This type is not supported by your environment API Type'))

    # API Tag cannot have spaces
    @api.onchange('api_tag')
    def _remove_space_api_tag(self):
        for rec in self:
            if rec.api_tag:
                rec.api_tag = rec.api_tag.replace(" ", "").replace("\n", "")

    # Function to be called via XML-RPC to import data in Odoo
    def import_from_api(self, api_tag, data, action_tag=None):
        api_config = self.search([('api_tag', '=', api_tag)])
        if api_config:
            odoo_action = api_config.api_actions_ids.filtered(
                lambda a: a.name == action_tag)
            api_fields = api_config.api_fields_ids.filtered(
                lambda f: not f.exclusive_use or f.exclusive_use == 'get')
            if isinstance(data, list):
                for rec in data:
                    odoo_rec = api_config.import_record(rec, api_fields)
                    if odoo_action:
                        odoo_action.action_id.with_context(active_id=odoo_rec.id,
                                                           active_model=api_config.model_id.model).run()
            else:
                odoo_rec = api_config.import_record(data, api_fields)
                if odoo_action:
                    odoo_action.action_id.with_context(active_id=odoo_rec.id,
                                                       active_model=api_config.model_id.model).run()
        else:
            raise UserError(_('API Tag not found'))

    def get_rec_to_update(self, data, api_fields):
        if isinstance(data, str):
            data = json.loads(data)
        sync_config_check_field = api_fields.filtered(lambda f: f.check_field)
        if not sync_config_check_field:
            return None
        elif sync_config_check_field.ext_system_field in data:
            model = api_fields[0].model_id.model
            existing_record = self.env[model].search(
                [(sync_config_check_field.odoo_field_id.name, '=',
                  data[sync_config_check_field.ext_system_field])])
            if len(existing_record) > 1:
                raise UserError(_('More the one record found for the value %s' % data[sync_config_check_field.ext_system_field]))
            return existing_record
        else:
            return None

    # Function to process a record from API to Odoo based on config
    def process_record(self, rdata, api_fields, create_data=True):
        if isinstance(rdata, str):
            rdata = json.loads(rdata)
        vals_list = {}
        for field in rdata:
            # if the records are present in the api sync config field model in the
            # external field  we add them to the values, if not we skip them
            if field in api_fields.mapped('ext_system_field'):
                config_field = api_fields.filtered(
                    lambda x: x.ext_system_field == field and not x.ext_system_subfield)
                config_field_type = config_field.odoo_field_ttype
                config_field_name = config_field.odoo_field_id.name
                # Skip insertion of id in the dict because it is used just
                # to identify record to update
                if config_field_name == 'id':
                    continue
                if config_field_type == 'many2one':
                    if config_field.field_config_id:
                        f_config_fields = config_field.field_config_id.api_fields_ids
                        f_data = rdata[field]
                        f_dict = self.process_record(f_data, f_config_fields, create_data)
                        rec_to_update = self.get_rec_to_update(f_data, f_config_fields)
                        if rec_to_update:
                            rec_to_update.update(f_dict)
                            if config_field_name:
                                vals_list[config_field_name] = rec_to_update.id
                        else:
                            if config_field_name:
                                vals_list[config_field_name] = self.env[config_field.field_config_id.model_id.model].create(f_dict).id
                    else:
                        # search if we found a record with that name, if not we create a
                        # record with that name
                        relation = config_field.odoo_field_id.relation
                        # to improve search, use subfield,
                        # for creation for now leave it as it was before
                        new_record = self.env[relation].search(
                            [(config_field.odoo_subfield, '=', rdata[field])])
                        if not new_record and create_data:
                            new_record = self.env[relation].create(
                                {'name': rdata[field]})
                        if config_field_name:
                            vals_list[config_field_name] = new_record[0].id if new_record else False
                # TODO: many2many e one2many si possono aggiornare e aggiungere ma non eliminare
                elif config_field_type in ['one2many', 'many2many']:
                    # get the api sync config of the one2many field, for example
                    # the lines of a sale order
                    cmp_config_fields = config_field.field_config_id.api_fields_ids
                    item_vals_array = []
                    # component contains the dict of the record that we have to create
                    for component in rdata[field]:
                        item_vals_dict = self.process_record(component, cmp_config_fields, create_data)
                        # add the component create with command.create / update and its values
                        rec_to_update = self.get_rec_to_update(component, cmp_config_fields)
                        if rec_to_update:
                            item_vals_array.append((1, rec_to_update.id, item_vals_dict))
                        else:
                            item_vals_array.append((0, 0, item_vals_dict))
                    if config_field_name:
                        vals_list[config_field_name] = item_vals_array
                else:
                    # adds this check so as not to create a dictionary with non-existent fields
                    if config_field_name:
                        if config_field_type in ['float', 'int']:
                            vals_list[config_field_name] = float(rdata[field].replace(',', '.'))
                        else:
                            vals_list[config_field_name] = rdata[field]
                # management of subfields
                config_subfields = api_fields.filtered(
                    lambda x: x.ext_system_field == field and x.ext_system_subfield)
                for subfield in config_subfields:
                    # TODO: Per il momento gestisco solo campi semplici (char / integer / float)
                    config_field_name = subfield.odoo_field_id.name
                    # adds this check so as not to create a dictionary with non-existent fields
                    if config_field_name:
                        vals_list[config_field_name] = rdata[field][subfield.ext_system_subfield]
        return vals_list

    def import_record(self, rdata, api_fields):
        try:
            # check if we already imported this partner then we update/create it
            vals_list = self.process_record(rdata, api_fields)
            rec_to_update = self.get_rec_to_update(rdata, api_fields)
            if rec_to_update:
                rec = rec_to_update.update(vals_list)
            else:
                rec = self.env[self.model_id.model].create(vals_list)
            self.env.cr.commit()
            gc.collect()
            return rec
        except Exception as e:
            raise UserError(_('NA API Sync Error: %s' % str(e)))

    def export_record(self, record, api_fields):
        # the function has been updated to also use advanced management fields,
        # in case the flag is active
        data_dict = {}
        # cycle all the fields created in the api sync config
        for field in api_fields:
            field_type = field.odoo_field_ttype
            odoo_field = field.odoo_field_id
            fixed_value = field.fixed_value
            ext_field = field.ext_system_field
            field_name = field.odoo_field_id.name
            # if there is the default value enter that
            if self.advanced_field_management and not odoo_field and fixed_value:
                value = fixed_value
                if self.advanced_field_management and value:
                    value = field.reformat_value(value)
                # if it's a normal field, we just add it to the dict the way it is
                data_dict[field.ext_system_field] = value
            # if it's a many2one get the field in the subfield
            elif field_type == 'many2one':
                value = record[odoo_field.name] if record[odoo_field.name] else False
                if field.odoo_subfield:
                    # in case there is more than one subfield
                    subfields = field.odoo_subfield.split('.')
                    value = record[odoo_field.name]
                    # if we have for example state_id.code, first we are going to get
                    # the state then we are going to get the code
                    for subfield in subfields:
                        value = value[subfield] if value else False
                # If there is config ID create dict, else insert subfield
                if field.field_config_id:
                    f_dict = self.export_record(
                        value, field.field_config_id.api_fields_ids) if value else False
                    data_dict[field.ext_system_field] = f_dict
                else:
                    if self.advanced_field_management and value:
                        value = field.reformat_value(value)

                    if self.advanced_field_management and not value and fixed_value:
                        value = field.reformat_value(fixed_value)
                    data_dict[field.ext_system_field] = value
            # for the one2many or many2many, we cycle their API config
            elif field_type in ['one2many', 'many2many']:
                # component records contains the field, for example if the main record
                # is a sale order and we want to add the lines,
                # then component record will contain sale order line.
                component_array = []
                # Recursive function for export record
                for component_record in record[odoo_field.name]:
                    component_dict = self.export_record(component_record,
                                                        field.field_config_id.api_fields_ids)
                    component_array.append(component_dict)
                data_dict[field.ext_system_field] = component_array
            # if there is a configuration, but no field attached,
            # it goes and gets the dictionary based on the record itself
            elif not odoo_field and field.field_config_id:
                sub_dict = self.export_record(record, field.field_config_id.api_fields_ids)
                data_dict[field.ext_system_field] = sub_dict
            # TODO forse in futuro sarebbe bene aggiungere una gestione di diversi formati data
            #  guardare come viene gestito su na_fixed_track_files
            elif field_type in ['datetime']:
                if record[odoo_field.name]:
                    data_dict[field.ext_system_field] = record[odoo_field.name].strftime("%Y-%m-%d %H:%M:%S")
                else:
                    data_dict[field.ext_system_field] = ''
            elif field_type in ['date']:
                if record[odoo_field.name]:
                    data_dict[field.ext_system_field] = record[odoo_field.name].strftime("%Y-%m-%d")
                else:
                    data_dict[field.ext_system_field] = ''
            else:
                value = record[
                    odoo_field.name] if odoo_field else False
                if self.advanced_field_management and value:
                    value = field.reformat_value(value)

                if self.advanced_field_management and not value and fixed_value:
                    value = field.reformat_value(fixed_value)
                # if it's a normal field, we just add it to the dict the way it is
                data_dict[field.ext_system_field] = value
            # at the end of everything if the format is XML and we have added a dictionary, create
            # an array with the data dictionary and configuration so that we add after the tags
            if field.config_id.feed_format == 'xml' and field.field_config_id and data_dict[field.ext_system_field]:
                data_dict[field.ext_system_field] = [data_dict[field.ext_system_field]]
                data_dict[field.ext_system_field].insert(0, field.field_config_id)
        return data_dict

    # when there is an error return False and add the message to the logs
    def _run_api_sync(self, method, record_ids=None, call_suffix=None, payload=""):
        method_lower = method.lower()
        # create the log
        api_logger = self.env['na.api.sync.log'].create({
            'env_id': self.env_id.id,
            'config_id': self.id,
            'method': method_lower,
        })
        response = ''
        try:
            if method_lower not in ['get', 'post']:
                api_logger.log_msg = 'The method should be GET or POST.'
                return False
            if method_lower == 'get' and not self.get_endpoint:
                api_logger.log_msg = ('The GET Endpoint is not configured, '
                                      'you can do it in the API Sync menu')
                return False
            if method_lower == 'post' and not self.post_endpoint:
                api_logger.log_msg = ('The POST Endpoint is not configured, '
                                      'you can do it in the API Sync menu')
                return False
            api_fields = self.api_fields_ids.filtered(
                lambda f: not f.exclusive_use or f.exclusive_use == method_lower)
            # authentication
            headers = self.env_id.get_headers(api_logger)
            # get function
            if method_lower == 'get':
                if call_suffix:
                    url = self.get_endpoint + call_suffix
                else:
                    url = self.get_endpoint
                response = requests.get(url, headers=headers, data=payload)
                # check the response status
                if response.status_code != 200:
                    api_logger.log_msg = 'There was an error during the request to the API, error code: ' + str(response.status_code)
                    return False
                # transform the data in json
                response_data = response.json()
                if not self.return_json:
                    for response_sing in response_data:
                        self.import_record(response_sing, api_fields)
                else:
                    return response_data
            # post function
            elif method_lower == 'post':
                data = []
                data_dict = {}
                if call_suffix:
                    url = self.post_endpoint + call_suffix
                else:
                    url = self.post_endpoint
                # If there is payload, data set in payload is passed
                if not payload:
                    if not record_ids:
                        api_logger.log_msg = 'Error: record_ids must be passed to function'
                        return False
                    # get the records that we have to send
                    records = self.env[self.model_id.model].browse(record_ids)
                    # for each record that we have to send create a dict
                    for record in records:
                        data_dict = self.export_record(record, api_fields)
                        # append the whole record information to the list
                        data.append(data_dict)
                    if len(data) > 1:
                        response = requests.post(url, headers=headers,
                                                 data="{" + str(data) + "}")
                    else:
                        response = requests.post(url, headers=headers,
                                                 data=str(data_dict))
                else:
                    response = requests.post(url, headers=headers, data=payload)
                # check the response status
                if response.status_code != 200:
                    api_logger.log_msg = ('There was an error during the request to the API, '
                                          'error code: ') + str(response.status_code)
                    return False
                if self.return_json:
                    return response.json()
            # TODO: Loggare la risposta anche in caso di return JSON?
            api_logger.log_msg = 'No Error - ' + (str(response.content) if response else '')
            return True
        except Exception as e:
            api_logger.log_msg = 'There was an error: %s.', e
            return False

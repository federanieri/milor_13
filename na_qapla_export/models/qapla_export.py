# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models, fields, api
import os
import tempfile
import pysftp
import csv
from datetime import datetime, timedelta, time


class QaplaLogger(models.Model):
    _name = 'qapla.export'

    name = fields.Char(string="Configuration")
    active_custom = fields.Boolean(string="Active", default="True")
    domain_custom = fields.Text(string="Selection Domain")
    file_name = fields.Char(string="File name",
                            help="Please set file name with extension .csv. Insert {date} as placeholder")

    def export_csv(self, dir, days=0):
        logger = self.env['qapla.logger']
        active_exports = self.env['qapla.export'].search([('active_custom', '=', True)])
        for export_config in active_exports:
            try:
                domain = eval(export_config.domain_custom) if export_config.domain_custom else []
                # date_limit_fake = datetime(2024, 6, 6, 18, 24, 13)
                # date_limit = date_limit_fake - timedelta(days=1)
                # fixme metti apposto prima di caricamento
                date_limit = datetime.now() - timedelta(days=1)
                domain += [('date_done', '>=', date_limit), ('state', '=', 'done')]

                picking_ok = []
                order_ids = self.get_pack_orders(domain)
                csv_data = []
                for picking in order_ids:
                    errors = self.check_picking(picking)
                    if not errors:
                        csv_data.append(self.get_csv_data(picking))
                        picking_ok.append(picking.name)
                    else:
                        error_str = '<strong>Errors Picking {}:</strong><br>'.format(picking.name)
                        for error in errors:
                            error_str += error
                        logger.create_log(name="Mandatory Fields Missing", text=error_str,
                                          error=True)

                if csv_data:
                    try:
                        with tempfile.NamedTemporaryFile(mode='w', delete=False, newline='',
                                                         suffix='.csv') as temp_csv:
                            csv_writer = csv.writer(temp_csv, delimiter=';')
                            csv_writer.writerows(csv_data)
                            temp_csv_path = temp_csv.name

                        date = datetime.today().strftime('%Y%m%d')
                        file_name = export_config.file_name.replace("{date}", date)
                        file_path = os.path.join(tempfile.gettempdir(), file_name)
                        os.rename(temp_csv_path, file_path)
                    except Exception as e:
                        logger.create_log(name="{}: Error during file creation".format(
                            export_config.name), text=str(e), error=True)
                        continue

                    try:
                        ftp_host = self.env['ir.config_parameter'].sudo().get_param(
                            'qapla_ftp_host')
                        ftp_user = self.env['ir.config_parameter'].sudo().get_param(
                            'qapla_ftp_user')
                        ftp_pass = self.env['ir.config_parameter'].sudo().get_param(
                            'qapla_ftp_password')
                        cnopts = pysftp.CnOpts()
                        cnopts.hostkeys = None

                        with pysftp.Connection(host=ftp_host, username=ftp_user, password=ftp_pass,
                                               cnopts=cnopts) as sftp:
                            sftp.cwd(dir)
                            sftp.put(file_path)

                        picking_ok_str = '<br>'.join(f'- {picking}' for picking in picking_ok)
                        logger.create_log(
                            name="{}: Pickings successfully exported".format(export_config.name),
                            text=picking_ok_str)
                    except Exception as e:
                        logger.create_log(name="{}: Error during connection with FTP Server".format(
                            export_config.name), text=str(e), error=True)
            except Exception as e:
                logger.create_log(name="{}: Unexpected error in export".format(export_config.name),
                                  text=str(e), error=True)

    def get_pack_orders(self, additional_domain=None):
        picking_obj = self.env['stock.picking']
        picking_ids = picking_obj.search(additional_domain)
        return picking_ids

    def check_picking(self, picking_id):
        errors = []
        if not picking_id.carrier_id:
            errors.append('- No carrier set;<br>')
        if picking_id.carrier_id and not picking_id.carrier_id.qapla_trans:
            errors.append('- No quapla code on carrier;<br>')
        if not picking_id.carrier_tracking_ref:
            errors.append('- No tracking number;<br>')
        if not picking_id.date_done:
            errors.append('- No date done;<br>')
        return errors

    def is_gls(self, carrier):
        if carrier.delivery_type == 'gls_italy':
            return True
        return False

    def format_date(self, datetime_obj):
        return datetime_obj.strftime('%Y-%m-%d')

    def get_csv_data(self, picking_id):
        data = []
        carrier = picking_id.carrier_id
        data.append(carrier.qapla_trans)  # 1.Codice corriere
        tracking = picking_id.carrier_tracking_ref
        if self.is_gls(carrier):
            if 'BAT/OUT' in picking_id.name:
                tracking = 'V6' + tracking
            else:
                tracking = 'M4' + tracking
        data.append(tracking)  # 2.Tracking number
        data.append(self.format_date(picking_id.date_done))  # 3.Data spedizione
        data.append(
            picking_id.origin.replace(';', ',') if picking_id.origin else '')  # 4.Riferimento
        data.append(self.format_date(
            picking_id.scheduled_date) if picking_id.scheduled_date else '')  # 5.Data Ordine
        data.append(picking_id.partner_id.name.replace(';',
                                                       ',') if picking_id.partner_id else '')  # 6.Nome e Cognome
        data.append(
            picking_id.partner_id.street.replace(';',
                                                 ',') if picking_id.partner_id and picking_id.partner_id.street else '')  # 7.Indirizzo
        data.append(
            picking_id.partner_id.city.replace(';',
                                               ',') if picking_id.partner_id and picking_id.partner_id.city else '')  # 8.Località
        data.append(
            picking_id.partner_id.zip.replace(';',
                                              ',') if picking_id.partner_id and picking_id.partner_id.zip else '')  # 9.CAP
        data.append(
            picking_id.partner_id.state_id.name.replace(';',
                                                        ',') if picking_id.partner_id and picking_id.partner_id.state_id else '')  # 10.Provincia
        data.append(
            picking_id.partner_id.country_id.name.replace(';',
                                                          ',') if picking_id.partner_id and picking_id.partner_id.country_id else '')  # 11.Nazione
        data.append(picking_id.partner_id.email.replace(';',
                                                        ',') if picking_id.partner_id and picking_id.partner_id.email else '')  # 12.Email
        phone = ''
        if picking_id.partner_id:
            if picking_id.partner_id.phone:
                phone = picking_id.partner_id.phone
            elif picking_id.partner_id.mobile:
                phone = picking_id.partner_id.mobile
        data.append(phone.replace(';', ','))  # 13.Telefono
        # data.append(picking_id.salesman_partner_id.name.replace(';',
        #                                                         ',') if picking_id.salesman_partner_id else '')  # 14.Agente
        data.append(picking_id.salesman_partner_id.email.replace(';',
                                                                 ',') if picking_id.salesman_partner_id and picking_id.salesman_partner_id.email else '')  # 14.Agente
        data.append('')  # 15.Importo
        qapla_1 = picking_id.carrier_id.qapla_1
        data.append('1' if qapla_1 else '')  # 16.POD
        data.append('')  # 17.Custom 1
        data.append('')  # 18.Custom 2
        data.append('')  # 19.Custom 3
        data.append('')  # 20.Note
        data.append(
            self.format_date(
                picking_id.scheduled_date) if picking_id.scheduled_date else '')  # 21.Data consegna
        data.append('')  # 22.Tag
        data.append('')  # 23.Origine
        data.append(len(picking_id.package_ids))  # 24.Colli
        data.append(picking_id.shipping_weight if picking_id.shipping_weight else '')  # 25.Peso
        return data

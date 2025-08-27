from odoo import fields, models, api, _
import requests, csv, base64, json
import logging
from datetime import date
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_onpage_product = fields.Boolean(string='Is OnPage Product', track_visibility='onchange')

    def check_products_requirements(self):
        self.ensure_one()

        if bool('from_template' in self._context) and bool(self._context.get('from_template')):
            if not bool(self.collection_id):
                raise ValidationError(
                    _('This product cannot be upload in OnPage because: The COLLECTION is NOT set for this product.'))
            elif not bool(self.collection_id.brand_id):
                raise ValidationError(
                    _('This product cannot be uploaded in OnPage because: The collection selected has NO BRAND SET'))

    def na_onpage_set_false(self):
        for rec in self:
            rec.is_onpage_product = False

    def list_generator(self, list):
        for element in list:
            yield element

    def create_datas_list(self, products):
        products_list = []

        # Operazioni per recuperare dai parametri di sistema i dati per gestire gli attributi prodotto
        config_sudo = self.env['ir.config_parameter'].sudo()
        one_size_att_id = config_sudo.get_param('one_size_attribute')
        one_size_val_id = config_sudo.get_param('one_size_value')
        one_size_id_code = str(one_size_att_id) + "_" + str(one_size_val_id)
        one_size_name = self.env['product.attribute.value'].search([('id', '=', one_size_val_id)]).name
        size_ids_str = config_sudo.get_param('size_attributes')
        stone_ids_str = config_sudo.get_param('stone_attributes')
        plat_ids_str = config_sudo.get_param('plating_attributes')
        size_att_ids = json.loads(size_ids_str)
        stone_att_ids = json.loads(stone_ids_str)
        plating_att_ids = json.loads(plat_ids_str)

        # Il ciclo esaminerà i prodotti della search precedente uno alla volta e creerà una lista con tutti i relativi dati da inviare a onpage
        for product in products:
            entry_list = []

            # Verifica per controllare che ogni attributo sia valorizzato o in caso contrario venga impostato come nullo nella lista
            if product.categ_id:
                entry_list.extend([str(product.categ_id.id), str(product.categ_id.complete_name)])
            else:
                entry_list.extend(["", ""])
            if product.genre_id:
                entry_list.extend([str(product.genre_id.id), str(product.genre_id.name)])
            else:
                entry_list.extend(["", ""])
            if product.product_brand_id:
                entry_list.extend([str(product.product_brand_id.id), str(product.product_brand_id.name)])
            else:
                entry_list.extend(["", ""])
            if product.collection_id:
                entry_list.extend([str(product.collection_id.id), str(product.collection_id.name)])
            else:
                entry_list.extend(["", ""])
            entry_list.append(str(product.product_tmpl_id.id))
            entry_list.append(str(product.name))
            if product.product_tmpl_id.default_code:
                entry_list.append(str(product.product_tmpl_id.default_code))
            else:
                entry_list.append("")
            if product.default_code:
                entry_list.append(str(product.default_code))
            else:
                entry_list.append("")
            if product.barcode:
                entry_list.append(str(product.barcode))
            else:
                entry_list.append("")
            if product.price2:
                entry_list.append('{:.2f}'.format(product.price2))
            else:
                entry_list.append("")
            if product.price7:
                entry_list.append('{:.2f}'.format(product.price7))
            else:
                entry_list.append("")
            if product.price8:
                entry_list.append('{:.2f}'.format(product.price8))
            else:
                entry_list.append("")
            if product.weight_gr:
                entry_list.append('{:.2f}'.format(product.weight_gr))
            else:
                entry_list.append("")
            if product.packaging_code_id:
                entry_list.append(str(product.packaging_code_id.default_code))
            else:
                entry_list.append("")
            if product.length_cm:
                entry_list.append(product.length_cm)
            else:
                entry_list.append("")
            if product.extension_cm:
                entry_list.append(product.extension_cm)
            else:
                entry_list.append("")

            # Entrata vuota per campo larghezza, il cliente chiede per il momento di valorizzare sempre vuoto questo campo
            entry_list.append("")

            # Alcuni dati vengono recuperati dagli attributi del prodotto
            # ATTENZIONE!! Nelle righe successive i dati vengono inseriti in posizioni specifiche.
            # Nel caso in cui la struttura del file venga modificata, aggiunta rimozione o spostamento di colonne, sarà
            # necessario ricontrollare e aggiornare gli inserimenti di dati affinchè vadano nelle colonne corrette
            attr_objs = product.product_template_attribute_value_ids
            if attr_objs:

                # Inserimento dati iniziale nella lista
                # Questi dati verranno aggiornati dal ciclo for nel caso uno o più attributi siano presenti
                entry_list.extend(["", "", "", "", "", one_size_id_code, one_size_name])
                for attribute in attr_objs:
                    att_id = attribute.attribute_id.id

                    # Attributo dimensione anello e taglia
                    if att_id in size_att_ids:
                        taglia_obj = self.env['product.attribute.value'].search(
                            [('id', '=', attribute.product_attribute_value_id.id)])
                        taglia_name = taglia_obj.name
                        taglia_id = taglia_obj.id
                        entry_list[21] = taglia_name

                        # I campi id derivanti da attributo sono una combinazione dell'id dell'attributo e dell'id del valore
                        # Questa soluzione risulta necessaria per la presenza di più attributi con lo stesso nome
                        entry_list[26] = str(att_id) + "_" + str(taglia_id)
                        entry_list[27] = taglia_name
                        continue

                    # Attributo pietra
                    elif att_id in stone_att_ids:
                        pietra_obj = self.env['product.attribute.value'].search(
                            [('id', '=', attribute.product_attribute_value_id.id)])
                        pietra_name = pietra_obj.name
                        pietra_id = pietra_obj.id
                        entry_list[22] = str(att_id) + "_" + str(pietra_id)
                        entry_list[23] = pietra_name
                        continue

                    # Attributo placcatura
                    elif att_id in plating_att_ids:
                        placcatura_obj = self.env['product.attribute.value'].search(
                            [('id', '=', attribute.product_attribute_value_id.id)])
                        placcatura_name = placcatura_obj.name
                        placcatura_id = placcatura_obj.id
                        entry_list[24] = str(att_id) + "_" + str(placcatura_id)
                        entry_list[25] = placcatura_name
                        continue

            # Nel caso in cui il campo product_template_attribute_value_ids non sia valorizzato verranno inserite delle entrate vuote
            # Il campo taglia id e taglia nome avrà dei valori standard nel caso non sia presente l'attributo taglia nel prodotto
            else:
                entry_list.extend(["", "", "", "", "", one_size_id_code, one_size_name])
            if product.metal_id:
                entry_list.insert(26, str(product.metal_id.id))
                entry_list.insert(27, str(product.metal_id.name))
            else:
                entry_list.insert(26, "")
                entry_list.insert(27, "")
            if product.metal_code_title_id:
                entry_list.insert(28, str(product.metal_id.id))
                entry_list.insert(29, str(product.metal_id.name))
            else:
                entry_list.insert(28, "")
                entry_list.insert(29, "")
            if product.out_of_collection_variant:
                entry_list.append(True)
            else:
                entry_list.append("")
            entry_list.append(str(product.id))
            if product.na_stone_color:
                entry_list.extend([str(product.na_stone_color.id), str(product.na_stone_color.color)])
            else:
                entry_list.extend(["", ""])
            # TODO: testare
            if product.free_qty:
                entry_list.append(str(product.free_qty))
            else:
                entry_list.append("")

            # La lista con i dati del prodotto viene aggiunta alla lista definitiva
            products_list.extend([entry_list])
        return products_list

    def na_onpage_send(self):
        trigger_user_id = self.env.user.id
        for rec in self:
            rec.is_onpage_product = True
        templates_ids = self.mapped('id')
        products = self.env['product.product'].search([('product_tmpl_id', 'in', templates_ids)])
        headers_list = [
            'categoria id', 'categoria nome', 'genere id', 'genere nome', 'brand id', 'brand nome',
            'collezione id', 'collezione nome', 'prod id', 'prod nome', 'prod codice', 'var sku',
            'var barcode', 'var prezzo 1', 'var prezzo 2', 'var prezzo 3', 'var peso', 'var packing',
            'var lunghezza', 'var lunghezza extender', 'var larghezza',
            'var diametro anello', 'pietra id', 'pietra nome', 'placcatura id', 'placcatura nome',
            'metallo id', 'metallo nome', 'titolo metallo id', 'titolo metallo nome', 'taglia id',
            'taglia nome', 'variant_out_of_collection', 'variant_id', 'colore pietra id', 'colore pietra', 'giacenza'
        ]
        file_name_model = 'Onpage_product_export_' + str(date.today()) + ".csv"
        config_sudo = self.env['ir.config_parameter'].sudo()
        path = config_sudo.get_param('path_onpage_attachments')
        onpage_token = config_sudo.get_param('onpage_token')
        if not path:
            raise UserError(
                "Attenzione! Il path per gli allegati non è stato configurato. Si prega di contattare l'amministratore.")
        if not onpage_token:
            raise UserError(
                "Attenzione! Il token per l'invio dati a Onpage non è stato configurato. Si prega di contattare l'amministratore.")
        if path[-1] != '/':
            file_name_path = '/' + file_name_model
        else:
            file_name_path = file_name_model
        file_name = path + file_name_path
        file = open(file_name, 'w', newline='')
        writer = csv.writer(file)
        writer.writerow(headers_list)
        datas_list = self.create_datas_list(products)
        for line in self.list_generator(datas_list):
            writer.writerow(line)
        file.close()

        # Creazione del file csv allegato
        try:
            with open(file_name, 'rb') as csv_file:
                datas = base64.b64encode(csv_file.read())
        except Exception as e:
            pass
        self.env['ir.attachment'].create({
            'name': file_name_model,
            'type': 'binary',
            'datas': datas,
            'description': 'onpage_datas'
        })

        outcome = 'sent'
        error_message = ""

        # Invio a onpage tramite API
        try:
            url = f"https://app.onpage.it/api/import/with-config/{onpage_token}"
            res = requests.post(url, files={
                'file': open(file_name),
            })
            if res.status_code != 200:
                error_msg = res.content.decode("utf-8")
                error_details = f"L'importazione non è stata completata correttamente lo stato è {str(res.status_code)}, il messaggio è {error_msg}"
                _logger.error(error_details)
                outcome = 'error_onpage'
                error_message = error_details
        except Exception as e:
            _logger.error("L'invio del file csv non è riuscito correttamente :%s", e)
            outcome = 'error_odoo'
            error_message = e

        self.env['na.onpage.log'].create({
            'outcome': outcome,
            'error_message': error_message,
            'trigger_user': trigger_user_id,
        })
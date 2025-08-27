# -*- coding: utf-8 -*-
import logging
import json

from odoo import models, fields, api, registry, _

_logger = logging.getLogger(__name__)

THRON_DATETIME_TZ = "%Y-%m-%dT%H:%M:%SZ"

# meta fields
# key - thron field
# value - odoo field
FIELDS_MAPPING = {
    'keywords': 'keywords',
    'meta-title': 'title',
    'meta-descrizione': 'meta_description',
    'descrizione-pietra': 'stone_description',
    'descrizione-placcatura': 'plating_description',
    'descrizione-collezione': 'collection_description',
    'descrizione-lunga': 'general_description',
    'quando-utilizzarlo': 'when_use',
    'descrizione-tecnica-usata': 'technical_description',
    'bullet-point':'bullet_points'
}

# probably use ISO code?
LANG_MAPPING = {
    'en_US': 'en',
    'it_IT': 'it',
    'fr_FR': 'fr'
}


class ProductProduct(models.Model):
    # Private Attributes
    _inherit = 'product.product'

    # ---------------------
    # Field Declarations
    # ---------------------

    is_thron_product = fields.Boolean(string='Is Thron Product')
    thron_id = fields.Char(string="Thron Product ID")
    thron_create_date = fields.Datetime(string="Created on thron")
    thron_write_date = fields.Datetime(string="Updated on thron")
    thron_meta_data_json = fields.Text(string="metadata")

    # --------------
    # Helper Methods
    # --------------

    def _get_content_request_data(self, thron_ids):
        data = {
            "criteria": {
                "linkedProducts": {
                    "ids": thron_ids
                }
            },
            "responseOptions": {
                "resultsPageSize": 100,
                "returnDetailsFields": [
                    "locales"
                ]
            }
        }
        return data

    def _prepare_product_post_data(self):
        self.ensure_one()
        lang = self.env.context.get('lang')
        lang = LANG_MAPPING.get(lang, 'en')
        return {
            "name": [{"lang": lang, "value": self.name}],
            "description": [{"lang": lang, "value": self.description_sale or ''}],
            "aliases": [
                {"value": self.barcode or '', "description": "EAN", "unique": False},
                {"value": self.milor_upc_code or '', "description": "UPC", "unique": False},
                {"value": self.milor_extension_code or '', "description": "CODICEESTENSIONE", "unique": False},
                {"value": self.milor_packaging_code or '', "description": "Codice Prodotto Packaging", "unique": False},
                {"value": self.default_code, "description": "CODICECOMPLETO", "unique": True},
            ],
            "tags": [
                {
                    "id": self.categ_id.thron_id,
                    "classificationId": "CATEGORIA"
                }
            ],
        }

    def _prepare_product_update_data(self, item):
        data = {}
        lang = self.env.context.get('lang')
        lang = LANG_MAPPING.get(lang, 'en')
        thron_meta_fields = FIELDS_MAPPING.keys()
        for meta in item.get('metadata', []):
            for key, value in meta.items():
                if value['key'] in thron_meta_fields:
                    if not value.get('lang'):
                        data[FIELDS_MAPPING[value['key']]] = value['value']
                    elif value.get('lang') and not isinstance(data.get(FIELDS_MAPPING[value['key']]), dict):
                        data[FIELDS_MAPPING[value['key']]] = {value['lang']: value['value']}
                    else:
                        data[FIELDS_MAPPING[value['key']]][value['lang']] = value['value']
        names = item.get('name', [])
        if names:
            data['name_lang'] = {}
        for name in names:
            data['name_lang'][name['lang']]=name['value']
            
        descriptions = item.get('description', [])
        if descriptions:
            data['description_lang'] = {}
        for description in descriptions:
            data['description_lang'][description['lang']]=description['value']    
        # process json data
        for key, value in data.items():
            if isinstance(value, dict):
                data[key] = json.dumps(value)
        
        if item.get('metadata'):
            data['thron_meta_data_json'] = json.dumps(item['metadata'])
        if item.get('id'):
            data['thron_id'] = item.get('id')
        data['is_thron_product'] = True

        return data

    @api.model
    def _cron_sync_post_products(self, automatic=False, thron_account=False):
        if not thron_account:
            thron_account = self.env['thron.account'].search([], limit=1)
        if not thron_account:
            _logger.info('No Thron Account Found')
            return True

        try:
            if automatic:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))

            for product in self.search([('is_thron_product', '=', True), ('thron_id', '=', False)]):
                data = product._prepare_product_post_data()
                response = thron_account.create_products(data)
                if response.get('id'):
                    product.write({
                        'thron_id': response['id'],
                    })
                if automatic:
                    self.env.cr.commit()

        except Exception as e:
            if automatic:
                self.env.cr.rollback()
            _logger.error("%s"%(str(e)),exc_info=True)
            thron_account._log_message(str(e), _("Thron : products synchronization issues."), level="info", path="/products", func="_cron_sync_post_products")
            self.env.cr.commit()
        finally:
            if automatic:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return True
    
    
    
    @api.model
    def _cron_sync_get_products(self, automatic=False, thron_account=False,product_ids=False):
        if not thron_account:
            thron_account = self.env['thron.account'].search([], limit=1)
        if not thron_account:
            _logger.info('No Thron Account Found')
            return True

        try:
            if automatic:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))
            date = thron_account.last_product_update_date or fields.Datetime.now()
            if not product_ids:
                data = {"lastModified": {"after": date.strftime(THRON_DATETIME_TZ)}}
            else:
                data = {"aliases": {"op": "equal","values": [p.default_code for p in product_ids]}}
            next_page = True
            while next_page:
                thron_items = thron_account.search_products(data)
                cursor = thron_items.get('paging', {}).get('next', False)
                if cursor:
                    data = {"cursor": cursor}
                else:
                    next_page = False

                items = thron_items.get('items', [])
                for item in items:
                    domain = [('thron_id', '=', item.get('id'))]
                    if item.get('aliases'):
                        alias = [i['value'] for i in item['aliases'] if i['description'] == 'CODICECOMPLETO']
                        if alias:
                            domain = [('default_code', '=', alias[0])]
                    # TODO: add last modified date in domain? to ignore on last update?
                    product = self.search(domain, limit=1)
                    if product:
                        product_data = self._prepare_product_update_data(item)
                        product.write(product_data)

                        if automatic:
                            self.env.cr.commit()

            thron_account.last_product_update_date = fields.Datetime.now()

        except Exception as e:
            if automatic:
                self.env.cr.rollback()
            _logger.error("%s"%(str(e)),exc_info=True)
            thron_account._log_message(str(e), _("Thron : products synchronization issues."), level="info", path="/products", func="_cron_sync_get_products")
            self.env.cr.commit()
        finally:
            if automatic:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return True

    def clean_get_thron_image(self):
        self.ept_image_ids.filtered(lambda a : a.content_id ).unlink()
        self.get_thron_image()
    
    def get_thron_image(self):
        self._cron_sync_get_content(domain=[('id','in',self.ids)])
        
    def get_thron_content(self):
        self._cron_sync_get_products(product_ids=self)

    @api.model
    def _cron_sync_get_content(self, automatic=False, thron_account=False,domain=[]):
        if not thron_account:
            thron_account = self.env['thron.account'].search([], limit=1)
        if not thron_account:
            _logger.info('No Thron Account Found')
            return True

        try:
            if automatic:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))
            ProductImage = self.env['common.product.image.ept']
            ProductVideo = self.env['product.image']
            # TODO: check how much product we can process in 1 cycle?
            products = self.search([('is_thron_product', '=', True)]+domain)
            # Find some better way, doing request on every product is not good,
            # but add this moment thron does not return product id alongs with content when we do content request with
            # multiple product id
            val = 1
            for product in products:
                _logger.info("%d:%s"%(val,product.thron_id))
                val+=1
                data = self._get_content_request_data([product.thron_id])
                contents = thron_account.search_content(data)
                if contents.get('resultCode') != 'OK':
                    _logger.info('Thron: something went wrong, could not get content for {} - {}'.format(product.name, product.thron_id))
                else:
                    for item in reversed([i for i in contents.get('items', []) if i['contentType'] == 'IMAGE']):
                        name = item['id'] + '.jpg'
                        if item.get('details') and item['details'].get('locales'):
                            name = item['details']['locales'][0]['name']
                        i_data = {
                            'name': name,
                            'url': '{}/delivery/public/image/{}/{}/{}/{}/{}/{}'.format(
                                thron_account.thron_public_api_url,
                                thron_account.thron_client_id,
                                item['id'],
                                thron_account.thron_public_api_key,
                                'std',
                                '0x0',
                                name),
                            'content_id': item['id'],
                            'product_id': product.id,
                            'template_id': product.product_tmpl_id.id
                        }
                        if not ProductImage.search_count([('product_id', '=', product.id), ('content_id', '=', item['id'])]):
                            ProductImage.create(i_data)
                        else :
                            p = ProductImage.search([('product_id', '=', product.id), ('content_id', '=', item['id'])],limit=1)
                            p.write({
                                     'name':name
                                     })
                    for item in reversed([i for i in contents.get('items', []) if i['contentType'] == 'VIDEO']):
                        name = item['id']
                        if item.get('details') and item['details'].get('locales'):
                            name = item['details']['locales'][0]['name']
                        i_data = {
                            'name': name,
                            'video_url': '{}/delivery/public/video/{}/{}/{}/{}/{}'.format(
                                thron_account.thron_public_api_url,
                                thron_account.thron_client_id,
                                item['id'],
                                thron_account.thron_public_api_key,
                                'WEBHD',
                                name),
                            'content_id': item['id'],
                            'product_variant_id': product.id,
                            'product_tmpl_id': product.product_tmpl_id.id,
                            'get_default_image':True
                        }
                        if not ProductVideo.search_count([('product_variant_id', '=', product.id), ('content_id', '=', item['id'])]):
                            ProductVideo.create(i_data)

                    if automatic:
                        self.env.cr.commit()

        except Exception as e:
            if automatic:
                self.env.cr.rollback()
            _logger.error("%s"%(str(e)),exc_info=True)
            thron_account._log_message(str(e), _("Thron : products synchronization issues."), level="info", path="/xcontents/resources/content/search", func="_cron_sync_get_content")
            self.env.cr.commit()
        finally:
            if automatic:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return True


class ProductImage(models.Model):
    # Private attributes
    _inherit = 'product.image'

    # ------------------
    # Fields Declaration
    # ------------------
    content_id = fields.Char(string='Content ID')

class ProductImageEpt(models.Model):
    # Private attributes
    _inherit = 'common.product.image.ept'

    # ------------------
    # Fields Declaration
    # ------------------
    content_id = fields.Char(string='Content ID')


class ProductCategory(models.Model):
    # Private Attributes
    _inherit = 'product.category'

    # ------------------
    # Fields Declaration
    # ------------------

    thron_id = fields.Char(string='Thron ID')




# {"items":[{"id":"5f032948900ce9769754f2d7","created":"2020-07-06T13:38:16.046Z","lastModified":"2020-08-07T13:27:13.785Z","aliases":[{"value":"V323505","description":"CODICEMILOR","unique":false},{"value":"WSBB00001","description":"CODICEWEB","unique":false},{"value":"WSBB/PZ","description":"CODICEPRODOTTOCONTABILITA","unique":false},{"value":"B","description":"CODICEESTENSIONE","unique":false},{"value":"8057094776429","description":"EAN","unique":false},{"value":"WSBB00001.B","description":"CODICECOMPLETO","unique":true}],"metadata":[{"string":{"key":"descrizione-lunga","classificationId":"t83zxj","value":" ","lang":"it"}},{"string":{"key":"descrizione-lunga","classificationId":"t83zxj","value":" ","lang":"en"}},{"string":{"key":"descrizione-lunga","classificationId":"t83zxj","value":" ","lang":"fr"}},{"string":{"key":"peso-category","classificationId":"t83zxj","value":"500"}},{"string":{"key":"selezione-per-hts","classificationId":"t83zxj","value":"BRONZALLURE BAG"}},{"string":{"key":"codice-hts","classificationId":"t83zxj","value":"4202.11.0000"}},{"string":{"key":"dazio","classificationId":"t83zxj","value":"8"}},{"string":{"key":"unita-di-misura","classificationId":"t83zxj","value":"PZ."}},{"string":{"key":"product-status","classificationId":"t83zxj","value":"NEW"}}],"tags":[{"id":"44fe902daa104dad840ee457c9d37ff7","classificationId":"t83zxj","ancestors":["41161aaf6201488fb41199003dc964ee"],"name":[{"lang":"en","value":"BRONZALLURE"},{"lang":"it","value":"BRONZALLURE"}]},{"id":"d0be85d644c44a349fdc77b73ed63994","classificationId":"t83zxj","ancestors":["fcc55cc91b794f55a66cef073c533356","4bbb5cfa2a404958ac04d76b10a41b10"],"name":[{"lang":"it","value":"ONE SIZE"}]},{"id":"37aadb1015f8430b852a074a6abef7a2","classificationId":"t83zxj","ancestors":["236de0aaa0c64f3b9ff1741c118736e3"],"name":[{"lang":"en","value":"WOMAN"},{"lang":"it","value":"WOMAN"}]},{"id":"ca6285671797458ab36dea444c3455b1","classificationId":"t83zxj","ancestors":["30dcb59a71ce4fab8eb1cfbb120ffb28"],"name":[{"lang":"en","value":"ROSE GOLD"},{"lang":"it","value":"ROSE GOLD"}]},{"id":"76a757502a0446c3a661e2d491c76b91","classificationId":"t83zxj","ancestors":["27246d5fdf6e451ebd13af4cbbfaf266"],"name":[{"lang":"en","value":"BRONZALLURE BAG"},{"lang":"it","value":"BRONZALLURE BAG"}]},{"id":"f8b119457ec04997ab881457b3ccfec0","classificationId":"t83zxj","ancestors":["2b10eb813cc34f92aa87bad58f371185"],"name":[{"lang":"en","value":"ACCESSORIES"},{"lang":"it","value":"ACCESSORIES"}]},{"id":"5514d3e24f524a5f9578c255ccf116f9","classificationId":"t83zxj","ancestors":["1d8a5a57b2344d89af8ef371b576e3e2"],"name":[{"lang":"en","value":"BRONZALLURE"},{"lang":"it","value":"BRONZALLURE"}]}]},{"id":"5f036263900ce9769755041a","created":"2020-07-06T17:41:55.281Z","lastModified":"2020-08-07T13:27:31.434Z","name":[{"lang":"it","value":"Bracciale con Medaglia"},{"lang":"en","value":"Rolo Bracelet with Gemstone Pendant"},{"lang":"fr","value":"BRACELET AVEC MEDAILLE"}],"description":[{"lang":"it","value":"<p>Il <strong>bracciale con medaglia</strong> icona in Golden Rose con catena a rolo' e ciondolo a disco, racchiuso in una cornice placcata oro rosa 18 kt, riporta un monogramma della B di Bronzallure sul retro. Ottima vestibilit&agrave; per un gioiello che puo' essere al tempo stesso casual e elegante. E' disponibile nelle varianti madreperla bianca e rosa, onice, malachite, lapis e amazzonite. La nuova variante in corniola rossa, della famglia dei quarzi calcedoni conferisce note speziate a tutti i tuoi outfit, stagione dopo stagione. E ancora la rodolite, rosa acceso con le tipiche venature estremamente femminili e le tonalit&agrave; rasserenanti color turchese della magnesite. Infine, metallica la pirite, con le tipiche iridescenze color canna di fucile.</p>"},{"lang":"en","value":"<p>Made from the flawless this Rolo Bracelet with Gemstone is paired with our exclusive 18KT Golden Rose plating, the rose gold alloy. The iconic B monogram medal embellishes one side of this delicate design, recently restyled to include a nice openwork of Bronzallure MILANO signature letter and new wearable dimensions for the everyday fit. The round rolo is also extremely comfortable and adjustable with a wide choice of certified natural gemstones: from the organic iridescence of white and pink mother of pearl, to the magnetic hues of black onyx, to vivacious malachite, amazonite and lapis. The new Red Carnelian variation, from the family of chalcedony confers earthy vibes to your seasonless outfits. The dark pink red rhodolite are ultra feminine; extra new features and shades include the soothing turquoise tones of magnesite and the timeless gunmetal iridescence of pyrite, a new sophisticated ideal morning to night.</p>"},{"lang":"fr","value":"<p>Le bracelet avec m&eacute;daille ic&ocirc;ne en Goldenr Rose avec cha&icirc;ne rolo et un pendentif &agrave; disque, enferm&eacute; dans un cadre plaqu&eacute; or rose 18 carats, montre un monogramme B de Bronzallure sur le revers. Excellent ajustement pour un bijou qui peut &ecirc;tre &agrave; la fois d&eacute;contract&eacute; et &eacute;l&eacute;gant. Il est disponible en blanc et rose nacr&eacute;, onyx, malachite, lapis et amazonite. La nouvelle variante en cornaline rouge, de la famille des quartz de calc&eacute;doine donne des notes &eacute;pic&eacute;es &agrave; toutes vos tenues, saison apr&egrave;s saison. Et encore, la rhodolite, rose vif avec les typiques veines extr&ecirc;mement f&eacute;minines et les tons apaisants de la magn&eacute;site turquoise. Enfin, m&eacute;tallique la pyrite, avec la typique irisation bronze.</p>"}],"aliases":[{"value":"B357594-BR","description":"CODICEMILOR","unique":false},{"value":"WSBZ00856","description":"CODICEWEB","unique":false},{"value":"WSBZ/PZ","description":"CODICEPRODOTTOCONTABILITA","unique":false},{"value":"BO","description":"CODICEESTENSIONE","unique":false},{"value":"8055320364099","description":"EAN","unique":false},{"value":"BZ-BRACELETBOX.BZ","description":"CODICEPRODOTTOPACKAGING","unique":false},{"value":"WSBZ00856.BO","description":"CODICECOMPLETO","unique":true}],"metadata":[{"string":{"key":"descrizione-tecnica-usata","classificationId":"t83zxj","value":"Descrizione tecnica usata","lang":"it"}},{"string":{"key":"descrizione-tecnica-usata","classificationId":"t83zxj","value":"Descrizione tecnica usata","lang":"en"}},{"string":{"key":"descrizione-lunga","classificationId":"t83zxj","value":"<p>Il <strong>bracciale con medaglia</strong> icona in Golden Rose con catena a rolo' e ciondolo a disco, racchiuso in una cornice placcata oro rosa 18 kt, riporta un monogramma della B di Bronzallure sul retro. Ottima vestibilit&agrave; per un gioiello che puo' essere al tempo stesso casual e elegante. E' disponibile nelle varianti madreperla bianca e rosa, onice, malachite, lapis e amazzonite. La nuova variante in corniola rossa, della famglia dei quarzi calcedoni conferisce note speziate a tutti i tuoi outfit, stagione dopo stagione. E ancora la rodolite, rosa acceso con le tipiche venature estremamente femminili e le tonalit&agrave; rasserenanti color turchese della magnesite. Infine, metallica la pirite, con le tipiche iridescenze color canna di fucile.</p> Il fascino senza tempo delle gemme più pure e genuine, selezionate nelle loro migliori forme e in tonalità uniche e raffinate, e quindi intagliate e lavorate con precisione in gioielli dal design autentico e contemporaneo grazie alla conoscenza diretta dei nostri migliori maestri artigiani. \nScopri la magia e le sfumature più ricercate disponibili in Natura, nei colori pastello e nelle tinte unite più accese e vivaci: dal classico blu lapis con i suoi accenni metallici e intramontabili, alla madreperla naturalmente iridescente e delicata (un must per le spose e un classico in ogni portagioie, ideale con la collezione di perle d'acqua dolce Maxima), dall’amazzonite nei toni acquatici del blu turchese rigato e denso, alla sensualità della corniola rossa e altro ancora, per la più ampia gamma di gioielli moderni in una vasta scelta di dischi, charm e anelli con sigillo, ma anche bracciali e orecchini.\nOgni gioiello Bronzallure è interamente disegnato e creato in Italia in un processo completamente proprietario e attento ai dettagli: le nostre collezioni fondono lo stato dell'arte del design milanese più aggiornato con l’abilità artigiana e un reperimento della materia prima rigido, sicuro e attento all’ambiente.\nAlba di Bronzallure si ispira al minimalismo milanese più elegante, fondendo un'intera gamma di forme rotonde e semicircolari con iconiche catene a maglia classica come la rolò, una presenza immancabile in gioielleria, resa contemporanea dall'uso della nostra inconfondibile e calda lega Golden Rosé. Tutti i nostri gioielli sono naturalmente privi di nichel e cadmio, grazie alla spessa placcatura di qualità in oro rosa 18kt, un elemento prezioso puro e femminile.\nÈ il complemento ideale per un'intera gamma di ciondoli e gioielli, come gli anelli con sigillo che sono in parte ispirati ai look bohemian-chic degli anni '70 e al tempo stesso tributo ai classici del gioiello e all'eleganza milanese: raffinati e senza tempo, alla mano ma incapaci di passare inosservati. Come chi li porta.","lang":"it"}},{"string":{"key":"descrizione-lunga","classificationId":"t83zxj","value":"<p>Made from the flawless this Rolo Bracelet with Gemstone is paired with our exclusive 18KT Golden Rose plating, the rose gold alloy. The iconic B monogram medal embellishes one side of this delicate design, recently restyled to include a nice openwork of Bronzallure MILANO signature letter and new wearable dimensions for the everyday fit. The round rolo is also extremely comfortable and adjustable with a wide choice of certified natural gemstones: from the organic iridescence of white and pink mother of pearl, to the magnetic hues of black onyx, to vivacious malachite, amazonite and lapis. The new Red Carnelian variation, from the family of chalcedony confers earthy vibes to your seasonless outfits. The dark pink red rhodolite are ultra feminine; extra new features and shades include the soothing turquoise tones of magnesite and the timeless gunmetal iridescence of pyrite, a new sophisticated ideal morning to night.</p> The timeless allure of pure and genuine gemstones, selected in their best shapes and refined shades, then finely cut and worked into authentic and contemporary designs thanks to the know-how of our master artisans in Italy in a fully controlled, detail-oriented process. Bronzallure blends a state of the art Milanese design direction to skilled craftsmen and a safe and attentive sourcing – discover the magic and most sought-after hues available in Nature, in pastel and solid colors, linear or with their own genuine pattern: from classic blue lapis with its lunar and edgy, timeless mettallic hints, to naturally iridescent and sweet mother of pearls (a must for brides and a classic in any jewelry box, ideal with our Maxima freshwater pearl collection), from striped and dense turquoise blue amazonite to sensual red carnelian and more, for the widest range of modern designs featuring a vast choice of discs, charm and cabochon-cut jewerly. Alba by Bronzallure is inspired to the most classy Milanese minimalism, blending a whole range of round and half-round shapes with iconic link chains such as the rolo, a milestone in jewelry and made contemporary by the use of our unmistakable and warm Golden Rose. All of our jewelry is genuinely nickel and cadmium free, thanks to a thick plating in the purest and most feminine 18KT rose gold. It comes s the ideal complement to a whole range of charms and jewelry, such as signet rings that is part inspired to the 70s looks and is part a tribute to jewelry classics and Milanese elegance: genuinely refined and timeless, deeply understated yet not to go unnoticed. Swipe through Alba pages and dig into a world of iconic essentials you’ll love to wear everyday, pick your favorite colors and sizes and combine them in infinite style options. The ideal gift from the stylish and fun friend to the most demanding jewelry expert.","lang":"en"}},{"string":{"key":"descrizione-lunga","classificationId":"t83zxj","value":"<p>Le bracelet avec m&eacute;daille ic&ocirc;ne en Goldenr Rose avec cha&icirc;ne rolo et un pendentif &agrave; disque, enferm&eacute; dans un cadre plaqu&eacute; or rose 18 carats, montre un monogramme B de Bronzallure sur le revers. Excellent ajustement pour un bijou qui peut &ecirc;tre &agrave; la fois d&eacute;contract&eacute; et &eacute;l&eacute;gant. Il est disponible en blanc et rose nacr&eacute;, onyx, malachite, lapis et amazonite. La nouvelle variante en cornaline rouge, de la famille des quartz de calc&eacute;doine donne des notes &eacute;pic&eacute;es &agrave; toutes vos tenues, saison apr&egrave;s saison. Et encore, la rhodolite, rose vif avec les typiques veines extr&ecirc;mement f&eacute;minines et les tons apaisants de la magn&eacute;site turquoise. Enfin, m&eacute;tallique la pyrite, avec la typique irisation bronze.</p> ","lang":"fr"}},{"string":{"key":"lunghezza-cm","classificationId":"t83zxj","value":"18,4"}},{"string":{"key":"lunghezza-cm-estensione","classificationId":"t83zxj","value":"2,54"}},{"string":{"key":"lunghezza-inch","classificationId":"t83zxj","value":"7,25"}},{"string":{"key":"lunghezza-inch-estensione","classificationId":"t83zxj","value":"1"}},{"string":{"key":"peso-category","classificationId":"t83zxj","value":"15,5"}},{"string":{"key":"selezione-per-hts","classificationId":"t83zxj","value":"BRONZE + GEMSTONE OVER/UGUALE $ 43 (gemstone, cz, perle, camei)"}},{"string":{"key":"codice-hts","classificationId":"t83zxj","value":"7116.20.1580"}},{"string":{"key":"dazio","classificationId":"t83zxj","value":"6,5"}},{"string":{"key":"bollo","classificationId":"t83zxj","value":"B ITALY BRONZALLURE"}},{"string":{"key":"unita-di-misura","classificationId":"t83zxj","value":"PZ."}},{"string":{"key":"pietra","classificationId":"t83zxj","value":"BLACK ONYX"}},{"string":{"key":"plateau","classificationId":"t83zxj","value":"C6_L10"}},{"string":{"key":"product-status","classificationId":"t83zxj","value":"NEW"}},{"string":{"key":"meta-descrizione","classificationId":"t83zxj","value":"Bracciale con ciondolo a disco in pietra naturale e catena rolò, placcato oro rosa 18 carati. Scopri tutte le varianti della collezione Alba by Bronzallure.","lang":"it"}},{"string":{"key":"meta-descrizione","classificationId":"t83zxj","value":"Made from the flawless this Rolo Bracelet with Gemstone is paired with our exclusive 18KT Golden Rose plating, the rose gold alloy. Rolo Bracelet with Gemstone","lang":"en"}},{"string":{"key":"meta-title","classificationId":"t83zxj","value":"Bracciale con Ciondolo a Disco e Catena Rolo'","lang":"it"}},{"string":{"key":"meta-title","classificationId":"t83zxj","value":"Rolo Bracelet with Gemstone","lang":"en"}},{"string":{"key":"descrizione-pietra","classificationId":"t83zxj","value":"Scegli questo bracciale pietre dure nelle varianti madreperla bianca e rosa, onice, malachite, lapis e amazzonite.","lang":"it"}},{"string":{"key":"descrizione-pietra","classificationId":"t83zxj","value":"Choose this gemstone bracelet in the white and pink mother of pearl, onyx, malachite, lapis and amazonite variants.","lang":"en"}},{"string":{"key":"bullet-point","classificationId":"t83zxj","value":"•\tGolden Rose Patented Alloy\n•\t18K Rose Gold Plating\n•\tFreshwater Pearls\n•\tDesigned & Made in Italy \n•\tNickel free, Cadmium Free, Hypoellergenic \n•\tComfort fit","lang":"en"}},{"string":{"key":"bullet-point","classificationId":"t83zxj","value":"•\tGolden Rosè(R): nuova lega nobile lucente e di color rosa già nel suo stato naturale, resistente ai graffi , realizzata con una formula brevettata che impedisce che cambi colore nel tempo.\n•\tPlaccatura in Oro Rosa 18kt\n•\tColore lucente nel tempo e maggiormente resistente ai graffi\n•\tManifattura e produzione 100% made in Italy\n•\tPietre naturali certificate selezionate a mano\n•\tTutti i gioielli Bronzallure sono ipoallergenici, cadmium e nichel free.","lang":"it"}},{"string":{"key":"descrizione-collezione","classificationId":"t83zxj","value":"Il fascino senza tempo delle gemme più pure e genuine, selezionate nelle loro migliori forme e in tonalità uniche e raffinate, e quindi intagliate e lavorate con precisione in gioielli dal design autentico e contemporaneo grazie alla conoscenza diretta dei nostri migliori maestri artigiani. \nScopri la magia e le sfumature più ricercate disponibili in Natura, nei colori pastello e nelle tinte unite più accese e vivaci: dal classico blu lapis con i suoi accenni metallici e intramontabili, alla madreperla naturalmente iridescente e delicata (un must per le spose e un classico in ogni portagioie, ideale con la collezione di perle d'acqua dolce Maxima), dall’amazzonite nei toni acquatici del blu turchese rigato e denso, alla sensualità della corniola rossa e altro ancora, per la più ampia gamma di gioielli moderni in una vasta scelta di dischi, charm e anelli con sigillo, ma anche bracciali e orecchini.\nOgni gioiello Bronzallure è interamente disegnato e creato in Italia in un processo completamente proprietario e attento ai dettagli: le nostre collezioni fondono lo stato dell'arte del design milanese più aggiornato con l’abilità artigiana e un reperimento della materia prima rigido, sicuro e attento all’ambiente.\nAlba di Bronzallure si ispira al minimalismo milanese più elegante, fondendo un'intera gamma di forme rotonde e semicircolari con iconiche catene a maglia classica come la rolò, una presenza immancabile in gioielleria, resa contemporanea dall'uso della nostra inconfondibile e calda lega Golden Rosé. Tutti i nostri gioielli sono naturalmente privi di nichel e cadmio, grazie alla spessa placcatura di qualità in oro rosa 18kt, un elemento prezioso puro e femminile.\nÈ il complemento ideale per un'intera gamma di ciondoli e gioielli, come gli anelli con sigillo che sono in parte ispirati ai look bohemian-chic degli anni '70 e al tempo stesso tributo ai classici del gioiello e all'eleganza milanese: raffinati e senza tempo, alla mano ma incapaci di passare inosservati. Come chi li porta.","lang":"it"}},{"string":{"key":"descrizione-collezione","classificationId":"t83zxj","value":"The timeless allure of pure and genuine gemstones, selected in their best shapes and refined shades, then finely cut and worked into authentic and contemporary designs thanks to the know-how of our master artisans in Italy in a fully controlled, detail-oriented process. Bronzallure blends a state of the art Milanese design direction to skilled craftsmen and a safe and attentive sourcing – discover the magic and most sought-after hues available in Nature, in pastel and solid colors, linear or with their own genuine pattern: from classic blue lapis with its lunar and edgy, timeless mettallic hints, to naturally iridescent and sweet mother of pearls (a must for brides and a classic in any jewelry box, ideal with our Maxima freshwater pearl collection), from striped and dense turquoise blue amazonite to sensual red carnelian and more, for the widest range of modern designs featuring a vast choice of discs, charm and cabochon-cut jewerly. Alba by Bronzallure is inspired to the most classy Milanese minimalism, blending a whole range of round and half-round shapes with iconic link chains such as the rolo, a milestone in jewelry and made contemporary by the use of our unmistakable and warm Golden Rose. All of our jewelry is genuinely nickel and cadmium free, thanks to a thick plating in the purest and most feminine 18KT rose gold. It comes s the ideal complement to a whole range of charms and jewelry, such as signet rings that is part inspired to the 70s looks and is part a tribute to jewelry classics and Milanese elegance: genuinely refined and timeless, deeply understated yet not to go unnoticed. Swipe through Alba pages and dig into a world of iconic essentials you’ll love to wear everyday, pick your favorite colors and sizes and combine them in infinite style options. The ideal gift from the stylish and fun friend to the most demanding jewelry expert.","lang":"en"}},{"string":{"key":"keywords","classificationId":"t83zxj","value":"Collection Alba, Italian Bracelets, Pendant","lang":"en"}},{"string":{"key":"keywords","classificationId":"t83zxj","value":"alba, bracciale, medaglia, wsbz00856, bronzallure, pendente, pietra, disco, ciondolo, catena rolò","lang":"it"}},{"string":{"key":"descrizione-placcatura","classificationId":"t83zxj","value":"Placcatura in Oro Rosa 18kt","lang":"it"}},{"string":{"key":"descrizione-placcatura","classificationId":"t83zxj","value":"18K Rose Gold Plating","lang":"en"}},{"string":{"key":"quando-utilizzarlo","classificationId":"t83zxj","value":"È il complemento ideale per un'intera gamma di ciondoli e gioielli, come gli anelli con sigillo che sono in parte ispirati ai look bohemian-chic degli anni '70 e al tempo stesso tributo ai classici del gioiello e all'eleganza milanese: raffinati e senza tempo, alla mano ma incapaci di passare inosservati. Come chi li porta.","lang":"it"}},{"string":{"key":"quando-utilizzarlo","classificationId":"t83zxj","value":" The ideal gift from the stylish and fun friend to the most demanding jewelry expert.","lang":"en"}},{"string":{"key":"testo-alternativo","classificationId":"t83zxj","value":"teto alternativo","lang":"it"}}],"tags":[{"id":"056bc105ef2e409ab0d9f3f277e25cc7","classificationId":"t83zxj","ancestors":["27246d5fdf6e451ebd13af4cbbfaf266"],"name":[{"lang":"en","value":"BRONZE"},{"lang":"it","value":"BRONZE"}]},{"id":"37aadb1015f8430b852a074a6abef7a2","classificationId":"t83zxj","ancestors":["236de0aaa0c64f3b9ff1741c118736e3"],"name":[{"lang":"en","value":"WOMAN"},{"lang":"it","value":"WOMAN"}]},{"id":"44fe902daa104dad840ee457c9d37ff7","classificationId":"t83zxj","ancestors":["41161aaf6201488fb41199003dc964ee"],"name":[{"lang":"en","value":"BRONZALLURE"},{"lang":"it","value":"BRONZALLURE"}]},{"id":"5514d3e24f524a5f9578c255ccf116f9","classificationId":"t83zxj","ancestors":["1d8a5a57b2344d89af8ef371b576e3e2"],"name":[{"lang":"en","value":"BRONZALLURE"},{"lang":"it","value":"BRONZALLURE"}]},{"id":"82aee2b907fc42e19ac481733b2ecf1d","classificationId":"t83zxj","ancestors":["2b10eb813cc34f92aa87bad58f371185"],"name":[{"lang":"en","value":"BRACELET"},{"lang":"it","value":"BRACELET"}]},{"id":"8e01afaf5d8a495a873558dac4be1be2","classificationId":"t83zxj","ancestors":["dc87cf3143ce449bbb6a557a47aeba5d"],"name":[{"lang":"en","value":"SPRING - SUMMER 2017"},{"lang":"it","value":"SPRING - SUMMER 2017"}]},{"id":"ac9b9de630cf4717b9372b6ca5f33a20","classificationId":"t83zxj","ancestors":["fcc55cc91b794f55a66cef073c533356","4bbb5cfa2a404958ac04d76b10a41b10"],"name":[{"lang":"it","value":"20,94CM"}]},{"id":"b898f4ea7ddd460eafb7ba6f88fd50d5","classificationId":"t83zxj","ancestors":["0e182bea4c1945d6b967aeac1e34bc72"],"name":[{"lang":"en","value":"ALBA"},{"lang":"it","value":"ALBA"}]},{"id":"ca6285671797458ab36dea444c3455b1","classificationId":"t83zxj","ancestors":["30dcb59a71ce4fab8eb1cfbb120ffb28"],"name":[{"lang":"en","value":"ROSE GOLD"},{"lang":"it","value":"ROSE GOLD"}]},{"id":"aa589aad607f419da769d18b0a58d6aa","classificationId":"t83zxj","ancestors":["7d736be6912545d088cc806e174a1978"],"name":[{"lang":"it","value":"Onice"},{"lang":"en","value":"Onice"}]}]}],"paging":{"estimatedCount":2}}
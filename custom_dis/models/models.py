# -*- coding: utf-8 -*-
# © 2019 SayDigital s.r.l.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import datetime, calendar
from odoo import api, exceptions, fields, models, _,SUPERUSER_ID
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo import tools
import logging

_logger = logging.getLogger(__name__)

class ProductDisMeta(models.Model):
    _name = "product.dis.meta"
    milorcode = fields.Char('Milor Code') #Riferimento univoco
    product_tmpl_id = fields.Char('product_tmpl_id') #Riferimento odoo
    code = fields.Char('Code') #Codice Dis
    image_path = fields.Char('Image path')
    dis_type = fields.Char('Tipo Dis')
    dis_creation_date = fields.Date('Data Creazione')
    dis_user = fields.Char('Dis User')
    dis_material = fields.Char('Dis Material')
    imported = fields.Boolean('Imported')
    message = fields.Char('Message')

    @api.model
    def validate_all_dis_meta(self):
        dis_products_meta = self.env['product.dis.meta']
        dis_metas = dis_products_meta.search([('imported','!=',True),('message','=',False)],order='id')

        i = 0
        #We make batch processing to avoid timeout
        limit = 80
        for dis in dis_metas:
            i = i + 1
            if i <= limit:
                dis.dis_validate()

    def dis_reset(self):
        for a in self:
            a.write({'imported':False,'message':False,})

    def dis_validate(self):
        #Actions to validate dis import
        #dev = open("C:\\temp\\dev.txt", "w")

        tproducts = self.env['product.template']
        products = self.env['product.product']
        dis_products = self.env['product.dis']
        dis_products_meta = self.env['product.dis.meta']

        dis_elaborati = []

        for a in self:
            if a.code.upper not in dis_elaborati:
                dis_elaborati.append(a.code.upper)
                creation = ''
                user = ''
                prefix = ''
                project = ''
                projects = []
                dis_metas = dis_products_meta.search([('code','=ilike',a.code),('imported','!=',True)],order='id')
                if dis_metas:
                    for d in dis_metas:
                        if d.dis_creation_date:
                            creation = d.dis_creation_date
                        if d.dis_user:
                            user = d.dis_user
                        if d.dis_type:
                            project = d.dis_type
                            
                            pno = d.dis_type[9:]
                            prefix = d.dis_type[:9]

                            pn = 0
                            try:
                                pn = int(pno)
                            except:
                                pn = 0
                            projects.append(pn)
                            
                            #dev.write('%s %s %s\n'%(str(prefix),str(pn),str(pno)))

                if projects:
                    project = str(prefix) + str(sorted(projects)[-1])

                for dis in dis_metas:
                    products_ids = tproducts.search([('milor_code','=',dis.milorcode),])
                    if products_ids:
                        for p in products_ids:
                            new_dis = {
                                'product_tmpl_id':p.id,
                                'name':dis.code,
                                'dis_type':project,
                                'dis_creation_date':creation,
                                'dis_user':user,
                                'dis_material':dis.dis_material,
                                }
                            #Check if DIS already exist with same attributes
                            exist = dis_products.search([('product_tmpl_id','=',p.id),('name','=',dis.code),('dis_type','=',project),('dis_creation_date','=',creation),('dis_user','=',user)])
                            if not exist:
                                dis_products.create(new_dis)
                            dis.write({'imported':True,'message':'OK',})
                            new_dis = {}
                            projects = []
                    else:
                            dis.write({'message':'Not found'})
        #dev.close()


# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re
from collections import OrderedDict

from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.tools import image_process
from odoo.tools.translate import _
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
from odoo.addons.web.controllers.main import Binary
from odoo.http import content_disposition
from odoo.osv.expression import OR

import logging

_logger = logging.getLogger(__name__)


class MyCustomerPortal(CustomerPortal):

    @http.route(['/my/purchase/<int:order_id>/charge'], type='http', auth="public", website=True)
    def notify_in_charge_order(self, order_id, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)

            order_sudo.in_charge = True
        except (AccessError, MissingError) as e:
            _logger.error("%s"%(str(e)),exc_info=True)
            return request.redirect('/my')
        return request.redirect('/my/purchase/%s' % order_id)
    
    @http.route(['/my/purchase/<int:order_id>/spedito'], type='http', auth="public", website=True)
    def notify_spedito_order(self, order_id, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
            order_sudo.write({
                      'in_charge':False,
                      'spedito_da_fornitore':True,
                      'spedito_in_galvanica':False
                      })
        except (AccessError, MissingError) as e:
            _logger.error("%s"%(str(e)),exc_info=True)
            return request.redirect('/my')
        return request.redirect('/my/purchase/%s' % order_id)

    @http.route(['/my/purchase/<int:order_id>/spedito_galv'], type='http', auth="public", website=True)
    def notify_spedito_in_galvanica(self, order_id, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
            order_sudo.write({
                      'in_charge':False,
                      'spedito_da_fornitore':False,
                      'spedito_in_galvanica':True
                      })
        except (AccessError, MissingError) as e:
            _logger.error("%s"%(str(e)),exc_info=True)
            return request.redirect('/my')
        return request.redirect('/my/purchase/%s' % order_id)

    def purchase_get_domain(self,search_in,search):
        domain = [('published_in_portal','=',True)]
        if search and search_in:
            search_domain = []
            
            if search_in in ('name'):
                search_domain = OR([search_domain, [('name', 'ilike', search)]])
                search_domain = OR([search_domain, [('milor_codes', 'ilike', search)]])
                search_domain = OR([search_domain, [('partner_ref', 'ilike', search)]])
            domain += search_domain
        return domain
    
    @http.route(['/my/purchase/<int:order_id>'], type='http', auth="public", website=True)
    def portal_my_purchase_order(self, order_id=None, report_type=None,  access_token=None, download=False, **kw):
        try:
            oid = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        custom_report_name = kw.get('report_name')
        if custom_report_name:
            report_id = request.env['ir.actions.report']._get_report_from_name(custom_report_name)
            if not isinstance(report_id, type(request.env['ir.actions.report'])):
                raise UserError(_("%s is not the reference of a report") % custom_report_name)

            # INFO: use_pn if you want to use pritnernode.
            use_pn = kw.get('use_pn')
            # INFO: fallback to txt downloading if something fail in printing by printernode or not using pn.
            fallback_to_txt = kw.get('fallback_to_txt') or not use_pn

            # INFO: extract from query params if we need to use PrintNode printers linked to the user partner.
            if use_pn:
                user = request.env.user
                if user.printnode_enabled or user.company_id.printnode_enabled:
                    report_id = request.env['ir.actions.report']._get_report_from_name(custom_report_name)
                    printer_id = user.get_report_printer(report_id.id)
                    _logger.info(f"Report ID: '{report_id}' / PrintNode printer: '{printer_id[0]}'")
                    if printer_id[0]:
                        printer_id[0].printnode_print(
                            report_id=report_id.sudo(),
                            objects=oid
                        )
                        return

            if fallback_to_txt:
                report_type = 'zpl'
                method_name = 'render_qweb_text'
                report = getattr(report_id, method_name)([oid.id], data={'report_type': report_type})[0]
                reporthttpheaders = [
                    ('Content-Type', 'x-application/zpl'),
                    ('Content-Length', len(report)),
                ]
                if download:
                    filename = "%s.zpl" % (re.sub('\W+', '-', oid._get_report_base_filename()))
                    reporthttpheaders.append(('Content-Disposition', content_disposition(filename)))
                return request.make_response(report, headers=reporthttpheaders)

        return super(MyCustomerPortal, self).portal_my_purchase_order(order_id=order_id, report_type=report_type, access_token=access_token, **kw)

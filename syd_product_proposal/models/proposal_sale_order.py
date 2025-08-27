# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.misc import get_lang
from odoo import api, fields, models, _
from werkzeug.urls import url_encode
from collections import defaultdict
from odoo.tools.safe_eval import safe_eval


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def create_proposal_from_products(self):
        wizard_id = self.env['syd_product_proposal.wizard_order'].create({
                                                   'product_ids':self.ids
                                                   })
        
        action = self.env['ir.actions.act_window'].for_xml_id('syd_product_proposal', 'action_order_creation_helper')
        action['res_id'] = wizard_id.id
        
        return action

class saleOrderLines(models.Model):
    _inherit = 'sale.order.line'
    
    customer_product_code = fields.Char('Customer Product Code')
    
class saleOrder(models.Model):
    _inherit = 'sale.order'
    
    from_proposal = fields.Boolean('SO from proposal?', default=False)

class ProposalSaleOrder(models.Model):
    _name = "proposal.sale.order"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Proposal Sales Order"
    _order = 'date_order desc, id desc'
    _check_company_auto = True
    
    
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}) 
        res = super(ProposalSaleOrder, self).copy(default)
        res.write({'date_deadline_from':False,'date_deadline_to':False})
        for ol in res.porder_line:
            ol.update({'description':False,
                       'customer_product_code':False})
        if res.type == 'mts':
            res._update_qty_proposed()
        return res

        date_deadline_from
    def _update_qty_proposed(self):
        for ol in self.porder_line:
            ol.update({'qty_proposed':ol.product_id.free_qty if bool(ol.product_id.free_qty < ol.qty_proposed) else ol.qty_proposed,
                       'qty_accepted':0.0
                       })

    @api.model
    def _default_note(self):
        return self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms') and self.env.company.invoice_terms or ''

    @api.model
    def _get_default_team(self):
        return self.env['crm.team']._get_default_team_id()

    @api.depends('porder_line.price_total', 'porder_line.price_total_accepted')
    def _amount_all(self):
        """
        Compute the total amounts of the PSO.
        """
        for order in self:
            price_total = 0.0
            price_total_accepted = 0.0
            for line in order.porder_line:
                price_total += line.price_total
                price_total_accepted += line.price_total_accepted
            order.update({
                'amount_total': price_total,
                'amount_total_accepted': price_total_accepted,
            })

    name = fields.Char(string='Proposal Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    default_name = fields.Char(string='Proposal Name', states={'draft': [('readonly', False)]})

    date_order = fields.Datetime(string='Order Date', required=True, readonly=True, index=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, copy=False, default=fields.Datetime.now, help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    user_id = fields.Many2one(
        'res.users', string='Salesperson', index=True, tracking=2, default=lambda self: self.env.user,
        domain=lambda self: [('groups_id', 'in', self.env.ref('sales_team.group_sale_salesman').id)])
    partner_id = fields.Many2one(
        'res.partner', string='Customer', readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        required=True, change_default=True, index=True, tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', check_company=True,  # Unrequired company
        required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="If you change the pricelist, only newly added lines will be affected.")
    
    porder_line = fields.One2many('proposal.sale.order.line', 'porder_id', string='Order Lines', states={'cancel': [('readonly', True)], 'confirmed': [('readonly', True)]}, copy=True, auto_join=True)
    amount_total = fields.Monetary(string='Total Proposed', store=True, readonly=True, compute='_amount_all', tracking=4)
    amount_total_accepted = fields.Monetary(string='Total Accepted', store=True, readonly=True, compute='_amount_all', tracking=4)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    team_id = fields.Many2one(
        'crm.team', 'Sales Team',
        change_default=True, default=_get_default_team, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    note = fields.Text('Terms and conditions', default=_default_note)
    currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id', string="Currency", readonly=True, required=True)
    accepted = fields.Boolean("Accepted", tracking=True,copy=False)
    type_second_image = fields.Selection([
        ('image', 'Image'),
        ('stl', 'STl')
        ], string="Type Second Image",default="image")
    type = fields.Selection([('mts','From Stock'),('mto','From Order')],string="Proposal Type",default="mts")
    filter_domain = fields.Char('Product Filter', help=" Filter on the object")
    model_name = fields.Char(default='product.product', string='Model Name', readonly=True, store=True)
    filter_id = fields.Many2one('ir.filters','Product Filter',domain="[('model_id','=','product.product'),'|',('user_id','=',user_id),('user_id','=',False)]")
    
    date_deadline_from = fields.Date('Date Deadline From')
    date_deadline_to = fields.Date('Date Deadline To')
    
    view_customer_product_code = fields.Boolean(compute='_get_view_customer_product_code', string='View Customer Product Code')

    def _get_view_customer_product_code(self):
        self.view_customer_product_code = self.env['ir.config_parameter'].sudo().get_param('syd_product_proposal.view_customer_product_code') or False

    
    @api.onchange('filter_id')
    def onchange_filter(self):
        if self.filter_id:
            self.filter_domain = self.filter_id.domain
            
    def populate_product(self):
        domain = (safe_eval(self.filter_domain,  {}) if self.filter_domain else [])
        products = self.env['product.product'].search(domain)
        pr = []
        for p in products:
                product_id = p.id
                values = {
                              'product_id':product_id,
                              'name':p.name,
                               'product_uom':p.uom_id.id
                              }
#
                pr.append([0,False,values])
        self.porder_line = pr
                
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        """
        if not self.partner_id:
            return
        partner_user = self.partner_id.user_id or self.partner_id.commercial_partner_id.user_id
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
        }
        user_id = partner_user.id
        if not self.env.context.get('not_self_saleperson'):
            user_id = user_id or self.env.uid
        if user_id and self.user_id.id != user_id:
            values['user_id'] = user_id

        if self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms') and self.env.company.invoice_terms:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.company.invoice_terms
        if not self.env.context.get('not_self_saleperson') or not self.team_id:
            values['team_id'] = self.env['crm.team']._get_default_team_id(domain=['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)], user_id=user_id)
        self.update(values)

    @api.onchange('user_id')
    def onchange_user_id(self):
        if self.user_id:
            self.team_id = self.env['crm.team']._get_default_team_id(user_id=self.user_id.id)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'proposal.sale.order', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('proposal.sale.order', sequence_date=seq_date) or _('New')

        # Makes sure 'pricelist_id' are defined
        if any(f not in vals for f in ['pricelist_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            vals['pricelist_id'] = vals.setdefault('pricelist_id', partner.property_product_pricelist and partner.property_product_pricelist.id)
        result = super(ProposalSaleOrder, self).create(vals)
        return result

    def preview_proposal_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

    def action_draft(self):
        self.ensure_one()
        orders = self.filtered(lambda s: s.state in ['cancel', 'sent'])
        return orders.write({'state': 'draft'})

    def action_cancel(self):
        self.ensure_one()
        return self.write({'state': 'cancel'})

    def action_confirm(self):
        self.ensure_one()
        SaleOrder = self.env['sale.order']
        order = {
            'partner_id': self.partner_id.id,
            'pricelist_id': self.pricelist_id and self.pricelist_id.id,
            'date_order': self.date_order,
            'origin': self.name,
            'user_id': self.user_id and self.user_id.id,
            'company_id': self.company_id and self.company_id.id,
            'team_id': self.team_id and self.team_id.id,
            'date_deadline_from':self.date_deadline_from,
            'date_deadline_to':self.date_deadline_to,
            'from_proposal':True,
            'note': self.note,
            'order_line': [
                (0, 0, {'name': ol.name,
                        'product_id': ol.product_id.id,
                        'product_uom_qty': ol.qty_accepted,
                        'customer_product_code': ol.customer_product_code,
                        'price_unit': ol.price_accepted}) for ol in self.porder_line.filtered(lambda self:self.qty_accepted>0)]
            }
        sale_order = SaleOrder.create(order)
        subject = _('Sale Order has been created') + ': <a href=# data-oe-model=sale.order data-oe-id=%d>%s</a>' % (sale_order.id, sale_order.name)
        message = _('Order Created from Proposal Order of ') + ': <a href=# data-oe-model=proposal.sale.order data-oe-id=%d>%s</a>' % (self.id, self.name)
        self.write({
            'state': 'confirmed',
            'date_order': fields.Datetime.now()
        })
        self.message_post(body=subject)
        sale_order.message_post(body=message)
        # Auto confirm the sale order
        sale_order.action_confirm()

    def action_proposal_send(self):
        ''' Opens a wizard to compose an email, with relevant mail template loaded by default '''
        self.ensure_one()
        template_id = self.env['ir.model.data'].xmlid_to_res_id('syd_product_proposal.email_template_proposal_sale', raise_if_not_found=False)
        lang = self.env.context.get('lang')
        template = self.env['mail.template'].browse(template_id)
        if template.lang:
            lang = template._render_template(template.lang, 'proposal.sale.order', self.ids[0])
        ctx = {
            'default_model': 'proposal.sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "mail.mail_notification_paynow",
            'force_email': True,
            'model_description': self.with_context(lang=lang).name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_so_as_sent'):
            self.filtered(lambda o: o.state == 'draft').with_context(tracking_disable=True).write({'state': 'sent'})
        return super(ProposalSaleOrder, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)

    def _compute_access_url(self):
        super(ProposalSaleOrder, self)._compute_access_url()
        for order in self:
            order.access_url = '/my/proposal_orders/%s' % (order.id)

    def _get_share_url(self, redirect=False, signup_partner=False, pid=None):
        """Override for sales order.

        If the PSO is in a state where an action is required from the partner,
        return the URL with a login token. Otherwise, return the URL with a
        generic access token (no login).
        """
        self.ensure_one()
        if self.state == 'sent':
            auth_param = url_encode(self.partner_id.signup_get_auth_param()[self.partner_id.id])
            return self.get_portal_url(query_string='&%s' % auth_param)
        return super(ProposalSaleOrder, self)._get_share_url(redirect, signup_partner, pid)

    def _get_portal_return_action(self):
        """ Return the action used to display orders when returning from customer portal. """
        self.ensure_one()
        return self.env.ref('syd_product_proposal.action_proposal_orders')

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'proposal %s' % self.name


class ProposalSaleOrderLine(models.Model):
    _name = 'proposal.sale.order.line'
    _description = 'Proposal Sales Order Line'
    _order = 'porder_id, sequence, id'
    _check_company_auto = True


#     @api.onchange('product_id')
#     def _onchange_porder_line(self):
#         if bool(self.product_id): #TODO
#             self.qty_proposed = self.product_id.qty_available or 1


    @api.depends('price_proposed', 'qty_proposed', 'qty_accepted', 'price_accepted')
    def _compute_amount(self):
        """
        Compute the amounts of the PSO line.
        """
        for line in self:
            price = line.price_proposed * line.qty_proposed
            price_accepted = (line.price_accepted if line.price_accepted else line.price_proposed ) * line.qty_accepted
            line.update({
                'price_total': price,
                'price_total_accepted': price_accepted,
            })

    name = fields.Text(string='Label', required=True)
    porder_id = fields.Many2one('proposal.sale.order', string='Order Reference', required=True, ondelete='cascade', index=True, copy=False)
    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one(
        'product.product', string='Product', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        change_default=True, ondelete='restrict', check_company=True)  # Unrequired company
    image_1920 = fields.Image("Image", related="product_id.image_1920",max_width=1920, max_height=1920)

    # resized fields stored (as attachment) for performance
    image_1024 = fields.Image("Image 1024", related="product_id.image_1024", max_width=1024, max_height=1024)
    image_512 = fields.Image("Image 512", related="product_id.image_512", max_width=512, max_height=512)
    image_256 = fields.Image("Image 256", related="product_id.image_256", max_width=256, max_height=256)
    image_128 = fields.Image("Image 128", related="product_id.image_128", max_width=128, max_height=128)
    
    metal_id = fields.Many2one('product.metal','Metallo', related="product_id.metal_id")
    metal_title = fields.Char("Title Metallo", related="product_id.metal_title")
    plating_id = fields.Many2one("product.plating",string="Colore Placcatura", related="product_id.plating_id")
    length_cm = fields.Char("Lunghezza (cm)", related="product_id.length_cm")

    qty_proposed = fields.Float(string='Quantity Proposed', digits='Product Unit of Measure', required=True, default=1.0)
    price_proposed = fields.Float('Price Proposed', required=True, digits='Product Price', default=0.0)
    qty_accepted = fields.Float(string='Quantity Accepted', digits='Product Unit of Measure', required=True, default=0.0)
    price_accepted = fields.Float('Price Accepted', required=True, digits='Product Price', default=0.0)
    price_total = fields.Monetary(compute='_compute_amount', string='Total Proposed', readonly=True, store=True)
    price_total_accepted = fields.Monetary(compute='_compute_amount', string='Total Accepted', readonly=True, store=True)
    currency_id = fields.Many2one(related='porder_id.currency_id', depends=['porder_id.currency_id'], store=True, string='Currency', readonly=True)
    company_id = fields.Many2one(related='porder_id.company_id', depends=['porder_id.company_id'], store=True, string='Company', index=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancelled'),
        ], related='porder_id.state', string='Order Status', readonly=True, copy=False, store=True, default='draft')
    description = fields.Text('Details')
    
    stl_attachment_id = fields.Many2one('ir.attachment',string="File STL")
    stl_id = fields.Integer(related="stl_attachment_id.id")
    stl_url = fields.Char('Stl Url',compute="_stl_url")
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True)
    scheduled_date = fields.Datetime(compute='_compute_qty_at_date_scheduled', default=fields.Datetime.now, store=False) 
    display_qty_widget = fields.Boolean(compute='_compute_qty_to_deliver')
    
    virtual_available_at_date = fields.Float('Forecast Quantity',related='product_id.virtual_available')
    free_qty_today  = fields.Float('Free To Use Quantity', related='product_id.free_qty')
    standard_price = fields.Float('Cost',related="product_id.standard_price")
    lst_price = fields.Float('Price',related="product_id.lst_price")
    
    customer_product_code = fields.Char('Customer Product Code') 
    
    def open_pricelist_rules(self):
        self.ensure_one()
        domain = ['|',
            '&', ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id), ('applied_on', '=', '1_product'),
            '&', ('product_id', '=', self.product_id.id), ('applied_on', '=', '0_product_variant')]
        return {
            'name': _('Price Rules'),
            'view_mode': 'tree,form',
            'views': [(self.env.ref('product.product_pricelist_item_tree_view_from_product').id, 'tree'), (False, 'form')],
            'res_model': 'product.pricelist.item',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain,
            'context': {
                'default_product_id': self.id,
                'default_applied_on': '0_product_variant',
            }
        }

    @api.onchange('product_id')
    def _onchange_productid_qty(self):
        if bool(self.product_id) and self.porder_id.type == 'mts':
            self.qty_proposed = self.product_id.free_qty or 0.0
    
    @api.model
    def create(self,values):
        if 'porder_id' in values:
            if self.env['proposal.sale.order'].browse(values['porder_id']).type=='mts':
                quantity = values.get('qty_proposed',0)
                if not quantity:
                    values['qty_proposed']=self.env['product.product'].browse(values['product_id']).free_qty
        return super(ProposalSaleOrderLine,self).create(values)  

    def _stl_url(self):
        for a in self:
            a.stl_url = "/web/content/%s"%a.stl_id
    @api.model
    def _default_warehouse_id(self):
        company = self.env.company.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids
    
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default=_default_warehouse_id, check_company=True)

    def _compute_qty_to_deliver(self):
        for proposal_order_line in self:
            proposal_order_line.display_qty_widget = True
    
    def _get_real_price_currency(self, product, rule_id, qty, uom, pricelist_id):
        """Retrieve the price before applying the pricelist
            :param obj product: object of current product record
            :parem float qty: total quentity of product
            :param tuple price_and_rule: tuple(price, suitable_rule) coming from pricelist computation
            :param obj uom: unit of measure of current order line
            :param integer pricelist_id: pricelist id of sales order"""
        PricelistItem = self.env['product.pricelist.item']
        field_name = 'lst_price'
        currency_id = None
        product_currency = product.currency_id
        if rule_id:
            pricelist_item = PricelistItem.browse(rule_id)
            if pricelist_item.pricelist_id.discount_policy == 'without_discount':
                while pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id and pricelist_item.base_pricelist_id.discount_policy == 'without_discount':
                    price, rule_id = pricelist_item.base_pricelist_id.with_context(uom=uom.id).get_product_price_rule(product, qty, self.porder_id.partner_id)
                    pricelist_item = PricelistItem.browse(rule_id)

            if pricelist_item.base == 'standard_price':
                field_name = 'standard_price'
                product_currency = product.cost_currency_id
            elif pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id:
                field_name = 'price'
                product = product.with_context(pricelist=pricelist_item.base_pricelist_id.id)
                product_currency = pricelist_item.base_pricelist_id.currency_id
            currency_id = pricelist_item.pricelist_id.currency_id

        if not currency_id:
            currency_id = product_currency
            cur_factor = 1.0
        else:
            if currency_id.id == product_currency.id:
                cur_factor = 1.0
            else:
                cur_factor = currency_id._get_conversion_rate(product_currency, currency_id, self.company_id or self.env.company, self.porder_id.date_order or fields.Date.today())

        product_uom = self.env.context.get('uom') or product.uom_id.id
        if uom and uom.id != product_uom:
            # the unit price is in a different uom
            uom_factor = uom._compute_price(1.0, product.uom_id)
        else:
            uom_factor = 1.0

        return product[field_name] * uom_factor * cur_factor, currency_id

    def _get_display_price(self, product):

        if self.porder_id.pricelist_id.discount_policy == 'with_discount':
            return product.with_context(pricelist=self.porder_id.pricelist_id.id).price
        product_context = dict(self.env.context, partner_id=self.porder_id.partner_id.id, date=self.porder_id.date_order, uom=self.product_id.uom_id.id)

        final_price, rule_id = self.porder_id.pricelist_id.with_context(product_context).get_product_price_rule(product or self.product_id, self.qty_proposed or 1.0, self.porder_id.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.qty_proposed, self.product_id.uom_id, self.porder_id.pricelist_id.id)
        if currency != self.porder_id.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, self.porder_id.pricelist_id.currency_id,
                self.porder_id.company_id or self.env.company, self.porder_id.date_order or fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)

    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return
        vals = {
            'name': self.product_id.name
        }

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.porder_id.partner_id.lang).code,
            partner=self.porder_id.partner_id,
            quantity=vals.get('qty_accepted') or self.qty_proposed,
            date=self.porder_id.date_order,
            pricelist=self.porder_id.pricelist_id.id,
            uom=self.product_id.uom_id.id,
        )

        if self.porder_id.pricelist_id and self.porder_id.partner_id:
            vals['price_proposed'] = self._get_display_price(product)
            
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            
        self.update(vals)

        title = False
        message = False
        result = {}
        warning = {}
        if product.sale_line_warn != 'no-message':
            title = _("Warning for %s") % product.name
            message = product.sale_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            if product.sale_line_warn == 'block':
                self.product_id = False

        return result

    @api.onchange('qty_proposed')
    def product_qty_change(self):
        if not self.product_id:
            self.price_proposed = 0.0
            return
        if self.porder_id.pricelist_id and self.porder_id.partner_id:
            product = self.product_id.with_context(
                lang=self.porder_id.partner_id.lang,
                partner=self.porder_id.partner_id,
                quantity=self.qty_proposed,
                date=self.porder_id.date_order,
                pricelist=self.porder_id.pricelist_id.id,
                uom=self.product_id.uom_id.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            self.price_proposed = self._get_display_price(product)

#     @api.onchange('qty_proposed', 'price_proposed')
#     def qty_and_price_proposed_change(self):
#         self.qty_accepted = self.qty_proposed
#         self.price_accepted = self.price_proposed
        
    @api.depends('scheduled_date')
    def _compute_qty_at_date_scheduled(self):
        for proposal_order_line in self:
            proposal_order_line.scheduled_date = fields.Datetime.now()
            
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    view_customer_product_code = fields.Boolean("Customer Product Code", default=False) 

    @api.model    
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            view_customer_product_code = self.env['ir.config_parameter'].sudo().get_param('view_customer_product_code')
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ir_values = self.env['ir.config_parameter']
        ir_values.sudo().set_param('view_customer_product_code', self.view_customer_product_code)
        
        visibility_group = self.env.ref('syd_product_proposal.group_proposal_product_code_visibility', raise_if_not_found=False)
        if visibility_group and self.view_customer_product_code and not self.env.user.has_group('syd_product_proposal.group_proposal_product_code_visibility'):
            visibility_group.sudo().write({'users': [(4, self.env.uid)]})
 
        elif self.env.user.has_group('syd_product_proposal.group_proposal_product_code_visibility') and not self.view_customer_product_code:
            visibility_group.write({'users': [(3, self.env.uid)]})
        return True

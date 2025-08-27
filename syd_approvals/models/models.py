# -*- coding: utf-8 -*-
# © 2019 SayDigital s.r.l.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import datetime, calendar
from dateutil.relativedelta import relativedelta
from odoo import api, exceptions, fields, models, _,SUPERUSER_ID
from odoo.exceptions import UserError, AccessError, ValidationError
from werkzeug import urls
import calendar
from odoo import tools
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_join
from odoo.tools.safe_eval import safe_eval


class ApprovalCategory(models.Model):
    _name = 'syd_approvals.category'
    _description = 'Approval Category'
    
    name=fields.Char('Name')
    model_id = fields.Many2one('ir.model',string="Model On")
    model_name = fields.Char(related='model_id.model', string='Model Name', readonly=True, store=True)
    rule_ids = fields.One2many('syd_approvals.rule','category_id',string="Rules")
    active=fields.Boolean('Active',default=True)
    field_child_id = fields.Many2one('ir.model.fields',string="Field Child",domain="[('model_id','=',model_id)]")
    model_child_name = fields.Char(related="field_child_id.relation", string='Model Child Name', readonly=True, store=True)
    

    
class ApprovalsRule(models.Model):
    _name = 'syd_approvals.rule'
    _description = 'Rule'
    
    name=fields.Char('Name')
    message=fields.Char('Message',default="This is blocked. You cannot change the state.")

    sequence = fields.Integer('Sequence')
    category_id = fields.Many2one('syd_approvals.category',string="Category")
    model_name = fields.Char(string="Model",related="category_id.model_name",store=True)
    user_id = fields.Many2one('res.users',string="Approver")
    filter_domain = fields.Char('Filter On', help=" Filter on the object")
    model_child_name = fields.Char(string="Model Child",related="category_id.model_child_name",store=True)
    filter_child_domain = fields.Char('Filter on Child',help="Filter on the object childs (in AND with the parent)")
    state=fields.Char('State',help="The state of the object that you want to block. If not set apply to each state")
    
class ApprovalObject(models.AbstractModel):
    _name = "syd_approvals.approval_mixin"
    _description = "Approval Mixin"
    
    approval_state = fields.Selection([('blocked','Blocked'),('done','Unlocked')],default="done",string="Approval State", tracking=True)
    approval_date = fields.Datetime('Unlocked Date')
    
    def get_approver_rule(self):
        for r in self:
            # esiste categoria per questo oggetto
            cat = self.env['syd_approvals.category'].search([('model_name','=',self._name)],limit=1)
            if cat:
                # per ogni regola di quella categoria
               for rule in cat.rule_ids:
                   domain = [('id', 'in', r.ids)] + (safe_eval(rule.filter_domain,  {}) if rule.filter_domain else [])
                   
                   if (self.search(domain)):
                       # se il filtro parent di quella regola si applica a questo oggetto
                       lines = getattr(r,cat.field_child_id.name)
                       for a in lines:
                           domain_child = [('id', 'in', a.ids)] + (safe_eval(rule.filter_child_domain,  {}) if rule.filter_child_domain else [])
                           if (self.env[rule.model_child_name].search(domain_child)):
                               # se il filtro figlio
                               return rule
                       if not len(lines):
                            return rule
            return False
    
    
    @api.model
    def create(self,vals):
        res = super(ApprovalObject,self).create(vals)
        for r in res:
            if r.sudo().get_approver_rule():
                r.write({'approval_state':'blocked'})
        return res
    
    def write(self,vals):
        for a in self:
            # se provo a cambiare lo stato o a sbloccare devo verificare se sono utente giusto
            if a.approval_state == 'blocked' and ('state' in vals or 'approval_state' in vals):
                rule_id = a.sudo().get_approver_rule()
                if (rule_id):
                    # se la regola ha uno stato impostato e non sto cambiando quello stato non andare avanti, altrimenti vai avanti
                    if (rule_id.state and vals['state'] and vals['state']== rule_id.state) or not rule_id.state or 'state' not in vals:
                        if (self.env.user.id != rule_id.sudo().user_id.id):
                            raise ValidationError(rule_id.sudo().message)
                        elif 'approval_state' not in vals :
                            vals['approval_state']='done'
                            vals['approval_date']= fields.Datetime.now()
                        elif 'approval_state' in vals and vals['approval_state']=='done' :   
                            vals['approval_date']= fields.Datetime.now()
        res = super(ApprovalObject,self).write(vals)
        for a in self:
            if a.approval_state == 'done' and not a.approval_date:
                rule_id = a.sudo().get_approver_rule()
                if (rule_id):
                    a.approval_state = 'blocked'
        return res
    
    @api.constrains('approval_state')
    def activity_update(self):
        to_clean, to_do = self.env[self._name], self.env[self._name]
        rule_id = self.sudo().get_approver_rule()
        if (rule_id):
            for obj in self:
                note = _('New %s to analyze') % ( obj._description)
                if obj.approval_state == 'done':
                    to_clean |= obj
                elif obj.approval_state == 'blocked':
                    obj.activity_schedule(
                        'syd_approvals.mail_to_approve',
                        note=note,
                        user_id=rule_id.sudo().user_id.id)
            if to_clean:
                to_clean.activity_feedback(['syd_approvals.mail_to_approve'])
                if obj.user_id:
                    body_template = self.env.ref('syd_approvals.message_object_unlocked')
                    body = body_template.render(
                        dict(object=obj, model_description=self._description,res_model=self._name,user_id=rule_id.sudo().user_id),
                        engine='ir.qweb',
                        minimal_qcontext=True
                    )
                    obj.message_notify(
                        partner_ids=obj.user_id.partner_id.ids,
                        body=body,
                        subject=_('%s: %s unlocked') % (self._description, obj.display_name),
                        record_name=obj.display_name,
                        model_description=self._description,
                        email_layout_xmlid='mail.mail_notification_light',
                    )
            
    def action_approval_unlock(self):
        for a in self:
            a.write({'approval_state':'done'})
        
    
class SaleOrder(models.Model):
    _name="sale.order"
    _inherit = ['sale.order','syd_approvals.approval_mixin']
    
    
    def action_quotation_send(self):
        for a in self:
            if a.approval_state == 'blocked':
                rule_id = a.sudo().get_approver_rule()
                if (rule_id) and (not rule_id.state or rule_id.state == 'sent'):
                    if (self.env.user.id != rule_id.sudo().user_id.id):
                        raise ValidationError(rule_id.sudo().message)
        return super(SaleOrder,self).action_quotation_send()
    
    
class PurchaseOrder(models.Model):
    _name="purchase.order"
    _inherit = ['purchase.order','syd_approvals.approval_mixin']

    
    
    def action_rfq_send(self):
        for a in self:
            if a.approval_state == 'blocked':
                rule_id = a.sudo().get_approver_rule()
                if (rule_id) and (not rule_id.state or rule_id.state == 'sent'):
                    if (self.env.user.id != rule_id.sudo().user_id.id):
                        raise ValidationError(rule_id.sudo().message)
        return super(PurchaseOrder,self).action_rfq_send()
    

    
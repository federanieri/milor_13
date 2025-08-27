# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class QualityTeam(models.Model):
    _name = "syd_quality.team"
    _description = "Quality Team"


    name = fields.Char('Name', required=True)
    
    quality_user_ids = fields.One2many('syd_quality.team_user','quality_team_id','Team Members')
    
    def _create_check(self,picking_id):
        for a in self:
            min_user = self.env['syd_quality.team_user']
            min_check = 0
            for u in a.quality_user_ids:
                if min_check == 0:
                    min_check = u.quality_check_todo_count
                    min_user = u
                else:
                    if min_check > u.quality_check_todo_count:
                        min_check = u.quality_check_todo_count
                        min_user = u
            self.env['syd_quality.check'].create(
                                                 {
                                                  'name':picking_id.name,
                                                  'origin':picking_id.origin,
                                                  'state':'todo' if picking_id.state == 'assigned' else 'waiting',
                                                  'team_id':a.id,
                                                  'picking_id':picking_id.id,
                                                  'team_user_id':min_user.id
                                                  }
                                                 )
    def _generate_batch(self):
        for a in self:
            for u in a.quality_user_ids:
                checks = self.search([('batch_id','=',False),('team_user_id','=',u.id)])
                batch_values={
                                  'user_id':u.user_id.id,
                             }
                picking_ids = []
                for c in checks:
                    picking_ids += [c.picking_id.id]
                batch_values['picking_ids']=picking_ids
                bv = self.env["stock.picking"].create(batch_values)

    @api.model
    def generate_batch(self):
        teams = self.search([(1,'=',1)])
        teams._generate_batch()
        
class StockLocation(models.Model):
    _inherit = 'stock.location'
    
    quality_team_id = fields.Many2one('syd_quality.team','Quality Team')
    
class QualityTeamUser(models.Model):
    _name = "syd_quality.team_user"
    _description = "Quality Team"
    
    quality_team_id = fields.Many2one('syd_quality.team','Team',required=True)
    user_id = fields.Many2one('res.users','User',required=True)
    sequence = fields.Integer('Sequence')
    quality_check_ids = fields.One2many('syd_quality.check','team_user_id')
    quality_check_todo_count = fields.Integer('To Do',compute="_count_quality_check")
    
    def _count_quality_check(self):
        for a in self:
            check_ids = self.env['syd_quality.check'].search([('state','in',('waiting','todo'))])
            a.quality_check_todo_count = len(check_ids)
    
class QualityCheck(models.Model):
    _name = "syd_quality.check"
    _description = "Quality Check"
    _inherit = ['mail.thread','mail.activity.mixin']
    
    

    def _get_default_team_id(self):
        company_id = self.company_id.id or self.env.context.get('default_company_id', self.env.company.id)
        domain = ['|', ('company_id', '=', company_id), ('company_id', '=', False)]
        return self.team_id._get_quality_team(domain)

    def _read_group_states(self, values, domain, order):
        selection = self.env['syd_quality.check'].fields_get(allfields=['state'])['state']['selection']
        return [s[0] for s in selection]

    name = fields.Char(
        'Reference', copy=False, default=lambda self: _('New'),
        required=True)
    sequence = fields.Integer('Sequence')
    state = fields.Selection([('waiting','Waiting'),('todo','To Do'),('done','Done')],string="State",readonly=True,group_expand='_read_group_states')
    team_id = fields.Many2one(
        'syd_quality.team', 'Team', check_company=True,
        default=_get_default_team_id, required=True)
    team_user_id = fields.Many2one('syd_quality.team_user','Team User',domain="[('quality_team_id','=',team_id)]")
    user_id = fields.Many2one('res.users', 'Responsible',related="team_user_id.user_id")
    picking_id = fields.Many2one('stock.picking',required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company)
    batch_id = fields.Many2one(
        'stock.picking.batch', string='Batch Transfer',related="picking_id.batch_id")
    origin = fields.Char('Origin')
    has_scrap= fields.Boolean('Has Scrap',compute="_scrap")
    
    def _scrap(self):
        for a in self:
            scraps = self.env['stock.scrap'].search([('picking_id', '=', a.picking_id.id)]).ids
            a.write({
                     'has_scrap':bool(scraps)
                     })
            
    def action_see_move_scrap(self):
        self.ensure_one()
        action = self.env.ref('stock.action_stock_scrap').read()[0]
        scraps = self.env['stock.scrap'].search([('picking_id', '=', self.picking_id.id)])
        action['domain'] = [('id', 'in', scraps.ids)]
        action['context'] = dict(self._context, create=False)
        return action      
      
class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    check_ids = fields.One2many('syd_quality.check','picking_id')
    
    
    @api.constrains('state')
    def _change_quality_state(self):
        for a in self:
            for b in a.check_ids:
                if a.state in ('draft','confirmed','assigned'):
                    b.state = 'todo' 
                elif a.state == 'done' :
                    b.state = 'done' 
                else :
                    b.state = 'waiting'
                
    @api.constrains('location_id')
    def _assign_quality(self):
        for a in self:
            for b in a.check_ids:
                    b.unlink()
            if a.location_id.quality_team_id:
                a.location_id.quality_team_id._create_check(a)
                

# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-9-18 15:05
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import pytz
import logging

_logger = logging.getLogger(__name__)

ROUTSTATE = [('draft', u'草稿'), ('normal', u'正常'), ('override', u'失效')]


# 工艺
class AASMESRouting(models.Model):
    _name = 'aas.mes.routing'
    _description = 'AAS MES Routing'

    name = fields.Char(string=u'名称', required=True, copy=False)
    active = fields.Boolean(string=u'有效', default=True, copy=False)
    version = fields.Char(string=u'版本', copy=False)
    note = fields.Text(string=u'描述')

    workticket = fields.Boolean(string=u'是否生成工票', default=True, copy=False)
    state = fields.Selection(selection=ROUTSTATE, string=u'状态', default='draft', copy=False)
    create_time = fields.Datetime(string=u'创建时间', default=fields.Datetime.now, copy=False)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    standard_hours = fields.Float(string=u'标准工时(秒)', compute="_compute_standard_hours", store=True)
    origin_id = fields.Many2one(comodel_name='aas.mes.routing', string=u'源工艺', ondelete='restrict')
    owner_id = fields.Many2one(comodel_name='res.users', string=u'负责人', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)
    routing_lines = fields.One2many(comodel_name='aas.mes.routing.line', inverse_name='routing_id', string=u'工艺工序')

    @api.model
    def create(self, vals):
        chinadate = fields.Datetime.to_china_today()
        vals['version'] = chinadate.replace('-', '')
        return super(AASMESRouting, self).create(vals)

    @api.one
    def action_confirm(self):
        self.write({'state': 'normal'})

    @api.multi
    def action_change_routing(self):
        self.ensure_one()
        wizard = self.env['aas.mes.routing.wizard'].create({
            'routing_id': self.id, 'name': self.name, 'note': self.note,
            'mesline_id': False if not self.mesline_id else self.mesline_id.id,
            'wizard_lines': [(0, 0, {
                'name': rline.name, 'sequence': rline.sequence, 'note': rline.note,
                'workstation_id': rline.workstation_id.id, 'mesline_id': rline.mesline_id.id
            }) for rline in self.routing_lines]
        })
        view_form = self.env.ref('aas_mes.view_form_aas_mes_routing_wizard')
        return {
            'name': u"变更工艺",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.routing.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }


    @api.depends('routing_lines.standard_hours')
    def _compute_standard_hours(self):
        for record in self:
            record.standard_hours = sum([rline.standard_hours for rline in record.routing_lines])


# 工艺工序
class AASMESRoutingLine(models.Model):
    _name = 'aas.mes.routing.line'
    _description = 'AAS MES Routing Line'
    _order = 'routing_id desc,sequence'

    routing_id = fields.Many2one(comodel_name='aas.mes.routing', string=u'工艺', required=True, ondelete='cascade')
    name = fields.Char(string=u'名称', required=True, copy=False)
    sequence = fields.Integer(string=u'序号')
    note = fields.Text(string=u'描述')
    standard_hours = fields.Float(string=u'标准工时(秒)', default=0.0)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('uniq_sequence', 'unique (routing_id, sequence)', u'同一工艺的工序序号不可以重复！')
    ]

    @api.model
    def create(self, vals):
        if vals.get('routing_id', False) and not vals.get('mesline_id', False):
            routing = self.env['aas.mes.routing'].browse(vals.get('routing_id'))
            if routing.mesline_id:
                vals['mesline_id'] = routing.mesline_id.id
        return super(AASMESRoutingLine, self).create(vals)






#############################################向导#############################################



class AASMESRoutingWizard(models.TransientModel):
    _name = 'aas.mes.routing.wizard'
    _description = 'AAS MES Routing Wizard'

    routing_id = fields.Many2one(comodel_name='aas.mes.routing', string=u'工艺', required=True, ondelete='cascade')
    name = fields.Char(string=u'名称')
    note = fields.Text(string=u'描述')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade')
    wizard_lines = fields.One2many(comodel_name='aas.mes.routing.line.wizard', inverse_name='wizard_id', string=u'工艺工序')

    @api.multi
    def action_done(self):
        self.ensure_one()
        if not self.wizard_lines or len(self.wizard_lines) <= 0:
            raise UserError(u'请先添加工艺工序！')
        routing_lines = []
        for wline in self.wizard_lines:
            rlinevals = {
                'name': wline.name, 'sequence': wline.sequence, 'note': wline.note,
                'workstation_id': wline.workstation_id.id
            }
            if wline.badmode_lines and len(wline.badmode_lines) > 0:
                rlinevals['badmode_lines'] = [(0, 0, {'badmode_id': bline.badmode_id.id}) for bline in wline.badmode_lines]
            routing_lines.append((0, 0, rlinevals))
        routing = self.env['aas.mes.routing'].create({
            'name': self.name, 'note': self.note, 'origin_id': self.routing_id.id,
            'routing_lines': routing_lines, 'state': 'normal',
            'mesline_id': False if not self.mesline_id else self.mesline_id.id
        })
        self.routing_id.write({'active': False, 'state': 'override'})
        view_form = self.env.ref('aas_mes.view_form_aas_mes_routing')
        return {
            'name': u"生产工艺",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.routing',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'self',
            'res_id': routing.id,
            'context': self.env.context
        }


class AASMESRoutingLineWizard(models.TransientModel):
    _name = 'aas.mes.routing.line.wizard'
    _description = 'AAS MES Routing Line Wizard'
    _order = 'sequence,id'

    wizard_id = fields.Many2one(comodel_name='aas.mes.routing.wizard', string=u'工艺', ondelete='cascade')
    name = fields.Char(string=u'名称')
    sequence = fields.Integer(string=u'序号')
    note = fields.Text(string=u'描述')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='cascade')
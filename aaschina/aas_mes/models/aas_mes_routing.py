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
    state = fields.Selection(selection=ROUTSTATE, string=u'状态', default='draft', copy=False)
    create_time = fields.Datetime(string=u'创建时间', default=fields.Datetime.now, copy=False)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    origin_id = fields.Many2one(comodel_name='aas.mes.routing', string=u'源工艺', ondelete='restrict')
    owner_id = fields.Many2one(comodel_name='res.users', string=u'负责人', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)
    routing_lines = fields.One2many(comodel_name='aas.mes.routing.line', inverse_name='routing_id', string=u'工艺工序')

    @api.model
    def action_checking_version(self):
        tz_name = self.env.user.tz or self.env.context.get('tz') or 'Asia/Shanghai'
        utctime = fields.Datetime.from_string(fields.Datetime.now())
        utctime = pytz.timezone('UTC').localize(utctime, is_dst=False)
        currenttime = utctime.astimezone(pytz.timezone(tz_name))
        return currenttime.strftime('%Y%m%d')

    @api.model
    def create(self, vals):
        vals['version'] = self.action_checking_version()
        return super(AASMESRouting, self).create(vals)

    @api.one
    def action_confirm(self):
        self.write({'state': 'normal'})

    @api.multi
    def action_change_routing(self):
        self.ensure_one()
        wizard_lines = []
        for rline in self.routing_lines:
            rlinevals = {
                'name': rline.name, 'sequence': rline.sequence, 'note': rline.note,
                'workstation_id': rline.workstation_id.id, 'mesline_id': rline.mesline_id.id
            }
            rlinevals['badmode_lines'] = [(0, 0, {'badmode_id': bline.badmode_id.id}) for bline in rline.badmode_lines]
            wizard_lines.append(rlinevals)
        wizard = self.env['aas.mes.routing.wizard'].create({
            'routing_id': self.id, 'name': self.name, 'note': self.note,
            'mesline_id': False if not self.mesline_id else self.mesline_id.id,
            'wizard_lines': [(0, 0, wline) for wline in wizard_lines]
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


# 工艺工序
class AASMESRoutingLine(models.Model):
    _name = 'aas.mes.routing.line'
    _description = 'AAS MES Routing Line'
    _order = 'routing_id desc,sequence'

    routing_id = fields.Many2one(comodel_name='aas.mes.routing', string=u'工艺', required=True, ondelete='cascade')
    name = fields.Char(string=u'名称', required=True, copy=False)
    sequence = fields.Integer(string=u'序号')
    note = fields.Text(string=u'描述')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)
    badmode_lines = fields.One2many(comodel_name='aas.mes.routing.badmode', inverse_name='workcenter_id', string=u'不良模式')

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


    @api.multi
    def action_update_badmode(self):
        self.ensure_one()
        wizard = self.env['aas.mes.workcenter.badmode.wizard'].create({
            'workcenter_id': self.id,
            'badmode_lines': [(0, 0, {'badmode_id': bline.badmode_id.id}) for bline in self.badmode_lines]
        })
        view_form = self.env.ref('aas_mes.view_form_aas_mes_workcenter_badmode_wizard')
        return {
            'name': u"更新不良模式",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.workcenter.badmode.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }



# 工序不良模式
class AASMESRoutingBadmode(models.Model):
    _name = 'aas.mes.routing.badmode'
    _description = 'AAS MES Routing Bad Mode'
    _rec_name = 'badmode_name'

    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='cascade')
    badmode_id = fields.Many2one(comodel_name='aas.mes.badmode', string=u'不良模式', ondelete='restrict')
    badmode_name = fields.Char(string=u'不良名称', copy=False)

    _sql_constraints = [
        ('uniq_badmode', 'unique (workcenter_id, badmode_id)', u'请不要重复添加同一个不良模式！')
    ]

    @api.model
    def create(self, vals):
        if vals.get('badmode_id', False):
            badmode = self.env['aas.mes.badmode'].browse(vals.get('badmode_id'))
            vals['badmode_name'] = badmode.name
        return super(AASMESRoutingBadmode, self).create(vals)


    @api.multi
    def write(self, vals):
        if vals.get('badmode_id', False):
            badmode = self.env['aas.mes.badmode'].browse(vals.get('badmode_id'))
            vals['badmode_name'] = badmode.name
        return super(AASMESRoutingBadmode, self).write(vals)

    @api.model
    def action_loading_badmodelist(self, workcenter_id):
        """
        获取指定工序的不良模式列表
        :param workcenter_id:
        :return:
        """
        values = {'success': True, 'message': '', 'badmodelist': []}
        badmodelist = self.env['aas.mes.routing.badmode'].search([('workcenter_id', '=', workcenter_id)])
        if not badmodelist or len(badmodelist) <= 0:
            values.update({'success': False, 'message': u'当前工序还未设置不良模式！'})
            return values
        values['badmodelist'] = [{'badmode_id': badmode.badmode_id.id, 'badmode_name': badmode.badmode_name} for badmode in badmodelist]
        return values






#############################################向导#############################################



class AASMESRoutingWizard(models.TransientModel):
    _name = 'aas.mes.routing.wizard'
    _description = 'AAS MES Routing Wizard'

    routing_id = fields.Many2one(comodel_name='aas.mes.routing', string=u'工艺', required=True, ondelete='cascade')
    name = fields.Char(string=u'名称')
    note = fields.Text(string=u'描述')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
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
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    badmode_lines = fields.One2many(comodel_name='aas.mes.routing.line.badmode.wizard', inverse_name='rline_id', string=u'不良模式')


class AASMESRoutingLineBadmodeWizard(models.TransientModel):
    _name = 'aas.mes.routing.line.badmode.wizard'
    _description = 'AAS MES Routing Line Badmode Wizard'

    rline_id = fields.Many2one(comodel_name='aas.mes.routing.line.wizard', string=u'工序', ondelete='cascade')
    badmode_id = fields.Many2one(comodel_name='aas.mes.badmode', string=u'不良模式', ondelete='restrict')


class AASMESWorkcenterBadmodeWizard(models.TransientModel):
    _name = 'aas.mes.workcenter.badmode.wizard'
    _description = 'AAS MES Workcenter Badmode Wizard'

    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='cascade')
    badmode_lines = fields.One2many(comodel_name='aas.mes.workcenter.badmode.line.wizard', inverse_name='wizard_id', string=u'不良模式清单')

    @api.one
    def action_done(self):
        if self.workcenter_id.badmode_lines and len(self.workcenter_id.badmode_lines) > 0:
            self.workcenter_id.badmode_lines.unlink()
        if self.badmode_lines and len(self.badmode_lines) > 0:
            self.workcenter_id.write({'badmode_lines': [(0, 0, {'badmode_id': templine.badmode_id.id}) for templine in self.badmode_lines]})


class AASMESWorkcenterBadmodeLineWizard(models.TransientModel):
    _name = 'aas.mes.workcenter.badmode.line.wizard'
    _description = 'AAS MES Workcenter Badmode Line Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.mes.workcenter.badmode.wizard', string='Wizard', ondelete='cascade')
    badmode_id = fields.Many2one(comodel_name='aas.mes.badmode', string=u'不良模式', ondelete='restrict')
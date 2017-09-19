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
        vals['state'] = 'normal'
        return super(AASMESRouting, self).create(vals)

    @api.multi
    def action_change_routing(self):
        self.ensure_one()


# 工艺工序
class AASMESRoutingLine(models.Model):
    _name = 'aas.mes.routing.line'
    _description = 'AAS MES Routing Line'
    _order = 'sequence,id'

    routing_id = fields.Many2one(comodel_name='aas.mes.routing', string=u'工艺', required=True, ondelete='cascade')
    name = fields.Char(string=u'名称', required=True, copy=False)
    sequence = fields.Integer(string=u'序号')
    note = fields.Text(string=u'描述')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)


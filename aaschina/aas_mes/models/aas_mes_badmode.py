# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-9-24 07:59
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


# 不良模式
class AASMESBadmode(models.Model):
    _name = 'aas.mes.badmode'
    _description = 'AAS MES Bad Mode'

    name = fields.Char(string=u'名称', required=True, copy=False)
    code = fields.Char(string=u'编码', copy=False)
    note = fields.Text(string=u'描述')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    workstation_name = fields.Char(string=u'工位名称', compute="_compute_workstation_name", store=True)

    _sql_constraints = [
        ('uniq_name', 'unique (workstation_id, name)', u'同一工位的不良模式名称不能重复！'),
        ('uniq_code', 'unique (code)', u'不良模式的编码不可以重复！')
    ]

    @api.depends('workstation_id')
    def _compute_workstation_name(self):
        for record in self:
            record.workstation_name = False if not record.workstation_id else record.workstation_id.name


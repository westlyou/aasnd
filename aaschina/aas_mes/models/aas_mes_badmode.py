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
    note = fields.Text(string=u'描述')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    mesline_name = fields.Char(string=u'产线名称', compute="_compute_mesline_name", store=True)

    _sql_constraints = [
        ('uniq_name', 'unique (mesline_id, name)', u'同一产线的不良模式名称不能重复！！')
    ]

    @api.depends('mesline_id')
    def _compute_mesline_name(self):
        for record in self:
            if record.mesline_id:
                record.mesline_name = record.mesline_id.name
            else:
                record.mesline_name = False


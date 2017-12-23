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
    universal = fields.Boolean(string=u'通用的', default=True, copy=False)

    _sql_constraints = [
        ('uniq_code', 'unique (code)', u'不良模式的编码不可以重复！')
    ]


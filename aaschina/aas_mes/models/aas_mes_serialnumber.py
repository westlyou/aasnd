# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-10-12 10:31
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

class AASMESSerialnumber(models.Model):
    _name = 'aas.mes.serialnumber'
    _description = 'AAS MES Serialnumber'

    name = fields.Char(string=u'名称', required=True, copy=False)
    regular_code = fields.Char(string=u'规则编码', copy=False)
    sequence = fields.Integer(string=u'规则序号', copy=False)
    used = fields.Boolean(string=u'已使用', default=False, copy=False)
    create_time = fields.Datetime(string=u'创建时间', default=fields.Datetime.now, copy=False)
    user_id = fields.Many2one(comodel_name='res.users', string=u'创建人', ondelete='restrict', default=lambda self: self.env.user)
    internal_product_code = fields.Char(string=u'产品编码', copy=False, help=u'在公司内部的产品编码')
    customer_product_code = fields.Char(string=u'客户编码', copy=False, help=u'在客户方的产品编码')

    _sql_constraints = [
        ('uniq_name', 'unique (name)', u'序列号的名称不可以重复！')
    ]

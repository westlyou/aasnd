# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-10-18 16:25
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

# 生产操作
class AASMESOperation(models.Model):
    _name = 'aas.mes.operation'
    _description = 'AAS MES Operation'
    _rec_name = 'serialnumber_id'

    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', required=True, ondelete='restrict')

    embed_piece = fields.Boolean(string=u'置入连接片', default=False, copy=False)
    embed_piece_pass = fields.Boolean(string=u'置入连接片通过', default=False, copy=False)
    function_test = fields.Boolean(string=u'功能测试', default=False, copy=False)
    function_test_pass = fields.Boolean(string=u'功能测试通过', default=False, copy=False)
    final_quality_check = fields.Boolean(string='FQC', default=False, copy=False)
    fqccheck_pass = fields.Boolean(string=u'FQC操作通过', default=False, copy=False)
    gp12_check = fields.Boolean(string='GP12', default=False, copy=False)
    gp12_check_pass = fields.Boolean(string=u'GP12操作通过', default=False, copy=False)

    commit_badness = fields.Boolean(string=u'上报不良', default=False, copy=False)
    commit_badness_count = fields.Integer(string=u'上报不良次数', default=0, copy=False)
    rework_done = fields.Boolean(string=u'不良维修', default=False, copy=False)
    rework_done_count = fields.Integer(string=u'不良维修次数', default=0, copy=False)
    ipqc_check = fields.Boolean(string='IPQC', default=False, copy=False)
    ipqc_check_count = fields.Integer(string=u'IPQC测试次数', default=0, copy=False)


# 置入连接片记录
class AASMESOperationEmbedpiece(models.Model):
    _name = 'aas.mes.operation.embedpiece'
    _description = 'AAS MES Operation Embed Piece'

    operation_id = fields.Many2one(comodel_name='aas.mes.operation', string=u'操作记录', ondelete='cascade')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'操作员工', ondelete='restrict')
    operate_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'操作用户', ondelete='restrict', default=lambda self: self.env.user)
    operation_pass = fields.Boolean(string=u'操作通过', default=True, copy=False)
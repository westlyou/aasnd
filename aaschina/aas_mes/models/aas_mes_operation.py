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

    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', required=True, ondelete='restrict', index=True)

    embed_piece = fields.Boolean(string=u'置入连接片', default=False, copy=False)
    embed_piece_count = fields.Boolean(string=u'置入连接片次数', default=0, copy=False)
    function_test = fields.Boolean(string=u'功能测试', default=False, copy=False)
    function_test_count = fields.Integer(string=u'功能测试次数', default=0, copy=False)
    final_quality_check = fields.Boolean(string='FQC', default=False, copy=False)
    fqccheck_count = fields.Boolean(string=u'FQC操作次数', default=0, copy=False)
    gp12_check = fields.Boolean(string='GP12', default=False, copy=False)
    gp12_check_count = fields.Integer(string=u'GP12操作次数', default=0, copy=False)

    commit_badness = fields.Boolean(string=u'上报不良', default=False, copy=False)
    commit_badness_count = fields.Integer(string=u'上报不良次数', default=0, copy=False)
    dorework = fields.Boolean(string=u'不良维修', default=False, copy=False)
    dorework_count = fields.Integer(string=u'不良维修次数', default=0, copy=False)
    ipqc_check = fields.Boolean(string='IPQC', default=False, copy=False)
    ipqc_check_count = fields.Integer(string=u'IPQC测试次数', default=0, copy=False)


# 置入连接片记录
class AASMESOperationEmbedpiece(models.Model):
    _name = 'aas.mes.operation.embedpiece'
    _description = 'AAS MES Operation Embed Piece'
    _rec_name = 'serialnumber_id'

    operation_id = fields.Many2one(comodel_name='aas.mes.operation', string=u'操作记录', ondelete='cascade')
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'操作员工', ondelete='restrict')
    operate_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'操作用户', ondelete='restrict', default=lambda self: self.env.user)
    operation_pass = fields.Boolean(string=u'操作通过', default=True, copy=False)

    @api.model
    def create(self, vals):
        record = super(AASMESOperationEmbedpiece, self).create(vals)
        record.operation_id.write({'embed_piece_count': record.operation_id.embed_piece_count + 1})
        return record


# 功能测试记录
class AASMESOperationFunctiontest(models.Model):
    _name = 'aas.mes.operation.functiontest'
    _description = 'AAS MES Operation Function Test'
    _rec_name = 'serialnumber_id'

    operation_id = fields.Many2one(comodel_name='aas.mes.operation', string=u'操作记录', ondelete='cascade')
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'操作员工', ondelete='restrict')
    operate_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'操作用户', ondelete='restrict', default=lambda self: self.env.user)
    operation_pass = fields.Boolean(string=u'操作通过', default=True, copy=False)

    @api.model
    def create(self, vals):
        record = super(AASMESOperationFunctiontest, self).create(vals)
        record.operation_id.write({'function_test_count': record.operation_id.function_test_count + 1})
        return record

    @api.model
    def action_done_functiontest(self, serialnumber, workstation_code, operation_pass, employee_code=None):
        result = {'success': True, 'message': ''}
        tserialnumber = self.env['aas.mes.serialnumber'].search([('name', '=', serialnumber)], limit=1)
        if not tserialnumber:
            result.update({'success': False, 'message': u'序列号%s未搜索到,请仔细检查！'% serialnumber})
            return result
        functiontestvals = {'serialnumber_id': tserialnumber.id, 'operation_pass': operation_pass}
        workstation = self.env['aas.mes.workstation'].search([('code', '=', workstation_code)], limit=1)
        if not workstation:
            result.update({'success': False, 'message': u'工位异常，请仔细检查是否已经被删除！'})
            return result
        functiontestvals['workstation_id'] = workstation.id
        if not employee_code and (not workstation.employee_lines or len(workstation.employee_lines) <= 0):
            result.update({'success': False, 'message': u'当前工位没有员工在岗，请先员工上岗再进行操作！'})
            return result
        if employee_code:
            temployee = self.env['aas.hr.employee'].search([('code', '=', employee_code)], limit=1)
            if not temployee:
                result.update({'success': False, 'message': u'员工异常未搜索到当前员工！'})
                return result
            functiontestvals['employee_id'] = temployee.id
        elif workstation.employee_lines and len(workstation.employee_lines) > 0:
            functiontestvals['employee_id'] = workstation.employee_lines[0].id
        operation = self.env['aas.mes.operation'].search([('serialnumber_id', '=', tserialnumber.id)], limit=1)
        if not operation:
           operation = self.env['aas.mes.operation'].create({'serialnumber_id': tserialnumber.id})
        functiontestvals['operation_id'] = operation.id
        self.env['aas.mes.operation.functiontest'].create(functiontestvals)
        return result



# FQC测试记录
class AASMESOperationFinalqualitycheck(models.Model):
    _name = 'aas.mes.operation.finalqualitycheck'
    _description = 'AAS MES Operation Final Quality Check'
    _rec_name = 'serialnumber_id'

    operation_id = fields.Many2one(comodel_name='aas.mes.operation', string=u'操作记录', ondelete='cascade')
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'操作员工', ondelete='restrict')
    operate_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'操作用户', ondelete='restrict', default=lambda self: self.env.user)
    operation_pass = fields.Boolean(string=u'操作通过', default=True, copy=False)

    @api.model
    def create(self, vals):
        record = super(AASMESOperationFinalqualitycheck, self).create(vals)
        record.operation_id.write({'fqccheck_count': record.operation_id.fqccheck_count + 1})
        return record


# GP12操作记录
class AASMESOperationGP12check(models.Model):
    _name = 'aas.mes.operation.gp12check'
    _description = 'AAS MES Operation GP12Check'
    _rec_name = 'serialnumber_id'

    operation_id = fields.Many2one(comodel_name='aas.mes.operation', string=u'操作记录', ondelete='cascade')
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'操作员工', ondelete='restrict')
    operate_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'操作用户', ondelete='restrict', default=lambda self: self.env.user)
    operation_pass = fields.Boolean(string=u'操作通过', default=True, copy=False)

    @api.model
    def create(self, vals):
        record = super(AASMESOperationGP12check, self).create(vals)
        record.operation_id.write({'gp12_check_count': record.operation_id.gp12_check_count + 1})
        return record
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
    serialnumber_name = fields.Char(string=u'序列名称', copy=False)
    barcode_create = fields.Boolean(string=u'生成条码', default=False, copy=False)
    barcode_record_id = fields.Many2one(comodel_name='aas.mes.operation.record', string=u'生成条码记录')
    embed_piece = fields.Boolean(string=u'置入连接片', default=False, copy=False)
    embed_record_id = fields.Many2one(comodel_name='aas.mes.operation.record', string=u'置入连接片记录')
    function_test = fields.Boolean(string=u'隔离板测试', default=False, copy=False)
    functiontest_record_id = fields.Many2one(comodel_name='aas.mes.operation.record', string=u'隔离板测试记录')
    final_quality_check = fields.Boolean(string='最终检查', default=False, copy=False)
    fqccheck_record_id = fields.Many2one(comodel_name='aas.mes.operation.record', string=u'最终检查记录')
    gp12_check = fields.Boolean(string='GP12', default=False, copy=False)
    gp12_record_id = fields.Many2one(comodel_name='aas.mes.operation.record', string=u'GP12确认记录')

    commit_badness = fields.Boolean(string=u'上报不良', default=False, copy=False)
    commit_badness_count = fields.Integer(string=u'上报不良次数', default=0, copy=False)
    dorework = fields.Boolean(string=u'不良维修', default=False, copy=False)
    dorework_count = fields.Integer(string=u'不良维修次数', default=0, copy=False)
    ipqc_check = fields.Boolean(string='IPQC', default=False, copy=False)
    ipqc_check_count = fields.Integer(string=u'IPQC测试次数', default=0, copy=False)


    @api.model
    def create(self, vals):
        if vals.get('serialnumber_id', False) and (not vals.get('serialnumber_name', False)):
            serialnumber = self.env['aas.mes.serialnumber'].browse(vals.get('serialnumber_id'))
            vals['serialnumber_name'] = serialnumber.name
        return super(AASMESOperation, self).create(vals)



OPERATELIST = [('newbarcode', u'生成条码'), ('embedpiece', u'置入连接片'), ('functiontest', u'隔离板测试'),
               ('fqc', u'最终检查'), ('gp12', u'GP12检测'), ('ipqc', u'IPQC确认')]
OPERATEDICT = {'newbarcode': u'生成条码', 'embedpiece': u'置入连接片', 'functiontest': u'隔离板测试',
               'fqc': u'最终检查', 'gp12': u'GP12检测', 'ipqc': u'IPQC确认'}

# 生产操作记录
class AASMESOperationRecord(models.Model):
    _name = 'aas.mes.operation.record'
    _description = 'AAS MES Operation Record'

    operation_id = fields.Many2one(comodel_name='aas.mes.operation', string=u'操作记录', ondelete='cascade')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'操作员工', ondelete='restrict')
    operate_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'操作用户', ondelete='restrict', default=lambda self: self.env.user)
    operation_pass = fields.Boolean(string=u'操作通过', default=True, copy=False)
    operate_result = fields.Char(string=u'操作结果', copy=False)
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'操作设备', ondelete='restrict')
    operate_type = fields.Selection(selection=OPERATELIST, string=u'操作类型', copy=False)
    operate_name = fields.Char(string=u'操作名称', copy=False)

    @api.model
    def create(self, vals):
        if vals.get('operate_type', False):
            vals['operate_name'] = OPERATEDICT.get(vals.get('operate_type'), False)
        record = super(AASMESOperationRecord, self).create(vals)
        record.action_after_create()
        return record

    @api.one
    def action_after_create(self):
        serialnumber = self.operation_id.serialnumber_id
        operationvals = {}
        if self.operate_type == 'newbarcode':
            operationvals.update({'barcode_create': True, 'barcode_record_id': self.id})
        elif self.operate_type == 'embedpiece':
            operationvals.update({'embed_piece': True, 'embed_record_id': self.id})
        elif self.operate_type == 'functiontest':
            operationvals.update({'function_test': True, 'functiontest_record_id': self.id})
            if serialnumber.state == 'draft':
                serialnumber.write({'state': 'normal'})
        elif self.operate_type == 'fqc':
            operationvals.update({'final_quality_check': True, 'fqccheckt_record_id': self.id})
        elif self.operate_type == 'gp12':
            operationvals.update({'gp12_check': True, 'gp12_record_id': self.id})
        if operationvals and len(operationvals) > 0:
            self.operation_id.write(operationvals)




    @api.model
    def action_functiontest(self, equipment_code, serialnumber, operation_pass=False, operate_result=False):
        """
        添加功能测试记录
        :param equipment_code:
        :param serialnumber:
        :param operation_pass:
        :param operate_result:
        :return:
        """
        result = {'success': True, 'message': ''}
        equipment = self.env['aas.equipment.equipment'].search([('code', '=', equipment_code)], limit=1)
        if not equipment:
            result.update({'success': False, 'message': u'设备不存在或已经被删除，请仔细检查！'})
            return result
        if not equipment.mesline_id or not equipment.workstation_id:
            result.update({'success': False, 'message': u'设备还未设置产线或工位！'})
            return result
        mesline, workstation = equipment.mesline_id, equipment.workstation_id
        employeelist = self.env['aas.mes.workstation.employee'].search([('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)])
        if not employeelist or len(employeelist) <= 0:
            result.update({'success': False, 'message': u'当前工位上还没有员工上岗，请先扫描员工卡上岗再继续其他操作！'})
            return result
        temployee = employeelist[0].employee_id
        toperation = self.env['aas.mes.operation'].search([('serialnumber_name', '=', serialnumber)], limit=1)
        functiontestvals = {
            'operation_id': toperation.id, 'operate_type': 'functiontest',
            'employee_id': temployee.id, 'equipment_id': equipment.id,
            'operation_pass': operation_pass, 'operate_result': operate_result
        }
        functiontest = self.env['aas.mes.operation.record'].create(functiontestvals)
        toperation.write({'function_test': True, 'functiontest_record_id': functiontest.id})
        return result








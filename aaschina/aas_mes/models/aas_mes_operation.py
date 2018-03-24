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

REWORKSTATEDICT = {'commit': u'不良上报', 'repair': u'返工维修', 'ipqc': u'IPQC确认', 'done': u'完成'}

# 生产操作
class AASMESOperation(models.Model):
    _name = 'aas.mes.operation'
    _description = 'AAS MES Operation'
    _rec_name = 'serialnumber_id'
    _order = 'id desc'

    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', required=True, ondelete='restrict', index=True)
    serialnumber_name = fields.Char(string=u'序列名称', copy=False, index=True)

    barcode_create = fields.Boolean(string=u'生成条码', default=False, copy=False)
    barcode_record_id = fields.Many2one(comodel_name='aas.mes.operation.record', string=u'生成条码记录')

    embed_piece = fields.Boolean(string=u'置入连接片', default=False, copy=False)
    embed_record_id = fields.Many2one(comodel_name='aas.mes.operation.record', string=u'置入连接片记录')

    function_test = fields.Boolean(string=u'功能测试', default=False, copy=False)
    functiontest_record_id = fields.Many2one(comodel_name='aas.mes.operation.record', string=u'功能测试记录')

    final_quality_check = fields.Boolean(string=u'最终检查', default=False, copy=False)
    fqccheck_record_id = fields.Many2one(comodel_name='aas.mes.operation.record', string=u'最终检查记录')
    fqccheck_date = fields.Char(string=u'FQC日期', copy=False, index=True)

    gp12_check = fields.Boolean(string='GP12', default=False, copy=False)
    gp12_record_id = fields.Many2one(comodel_name='aas.mes.operation.record', string=u'GP12确认记录')
    gp12_date = fields.Char(string=u'GP12检测日期', copy=False, index=True)
    gp12_time = fields.Datetime(string=u'GP12检测时间', copy=False)

    commit_badness = fields.Boolean(string=u'上报不良', default=False, copy=False)
    commit_badness_count = fields.Integer(string=u'上报不良次数', default=0, copy=False)

    dorework = fields.Boolean(string=u'不良维修', default=False, copy=False)
    dorework_count = fields.Integer(string=u'不良维修次数', default=0, copy=False)

    ipqc_check = fields.Boolean(string='IPQC', default=False, copy=False)
    ipqc_check_count = fields.Integer(string=u'IPQC测试次数', default=0, copy=False)

    operation_date = fields.Char(string=u'生成日期', copy=False)
    labeled = fields.Boolean(string=u'已包装', default=False, copy=False)
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', index=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', index=True)
    internal_product_code = fields.Char(string=u'产品编码', copy=False, help=u'内部产品编码')
    customer_product_code = fields.Char(string=u'客户编码', copy=False, help=u'在客户方的产品编码')
    record_lines = fields.One2many(comodel_name='aas.mes.operation.record', inverse_name='operation_id', string=u'记录清单')


    @api.model
    def create(self, vals):
        record = super(AASMESOperation, self).create(vals)
        serialnumber = record.serialnumber_id
        record.write({'serialnumber_name': serialnumber.name})
        if serialnumber.state == 'draft':
            serialnumber.write({'state': 'normal'})
        return record


    @api.one
    def action_finalcheck(self, mesline, workstation):
        tempemployeedomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        tempemloyeelist = self.env['aas.mes.workstation.employee'].search(tempemployeedomain)
        scanemployeelist, scanemployeestr, checkemployeelist, checkemployeestr = [], False, [], False
        if tempemloyeelist and len(tempemloyeelist) > 0:
            for temployee in tempemloyeelist:
                employee = temployee.employee_id
                if temployee.action_type == 'scan':
                    scanemployeelist.append(employee.name+'['+employee.code+']')
                elif temployee.action_type == 'check':
                    checkemployeelist.append(employee.name+'['+employee.code+']')
            scanemployeestr, checkemployeestr = ','.join(scanemployeelist), ','.join(checkemployeelist)
        employeeid, equipmentid = False, False
        equipmentdomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        equipments = self.env['aas.mes.workstation.equipment'].search(equipmentdomain)
        if equipments and len(equipments) > 0:
            equipmentid = equipments[0].equipment_id.id
        self.env['aas.mes.operation.record'].create({
            'operation_id': self.id, 'equipment_id': equipmentid, 'employee_id': employeeid,
            'scanning_employee': scanemployeestr, 'checking_employee': checkemployeestr,
            'operator_id': self.env.user.id, 'operation_pass': True, 'operate_result': 'PASS', 'operate_type': 'fqc'
        })
        # 添加产出记录
        tserialnumber = self.serialnumber_id
        outputdomain = [('serialnumber_id', '=', tserialnumber.id)]
        outputdomain += [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        tempout = self.env['aas.mes.production.output'].search(outputdomain, limit=1)
        if tempout:
            tempvalues = {'qualified': True, 'pass_onetime': False}
            if not tempout.employee_id:
                tempvalues.update({'employee_id': employeeid, 'employee_name': checkemployeestr})
            if not tempout.equipment_id:
                tempvalues['equipment_id'] = equipmentid
            tempout.write(tempvalues)
        else:
            self.env['aas.mes.production.output'].create({
                'product_id': tserialnumber.product_id.id, 'output_qty': 1.0,
                'output_date': fields.Datetime.to_china_today(), 'mesline_id': mesline.id,
                'schedule_id': False if not mesline.schedule_id else mesline.schedule_id.id,
                'workstation_id': workstation.id, 'equipment_id': equipmentid,
                'employee_id': employeeid, 'employee_name': checkemployeestr, 'serialnumber_id': tserialnumber.id
            })


    @api.one
    def action_gp12check(self, mesline, workstation):
        tempemployeedomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        tempemloyeelist = self.env['aas.mes.workstation.employee'].search(tempemployeedomain)
        scanemployeelist, scanemployeestr, checkemployeelist, checkemployeestr = [], False, [], False
        if tempemloyeelist and len(tempemloyeelist) > 0:
            for temployee in tempemloyeelist:
                employee = temployee.employee_id
                if temployee.action_type == 'scan':
                    scanemployeelist.append(employee.name+'['+employee.code+']')
                elif temployee.action_type == 'check':
                    checkemployeelist.append(employee.name+'['+employee.code+']')
            scanemployeestr, checkemployeestr = ','.join(scanemployeelist), ','.join(checkemployeelist)
        employeeid, equipmentid = False, False
        equipmentdomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        equipments = self.env['aas.mes.workstation.equipment'].search(equipmentdomain)
        if equipments and len(equipments) > 0:
            equipmentid = equipments[0].equipment_id.id
        gp12record = self.env['aas.mes.operation.record'].create({
            'operation_id': self.id, 'operate_result': 'PASS', 'operate_type': 'gp12', 'equipment_id': equipmentid,
            'employee_id': employeeid, 'scanning_employee': scanemployeestr, 'checking_employee': checkemployeestr
        })
        current_time = fields.Datetime.now()
        china_date = fields.Datetime.to_china_string(current_time)[0:10]
        self.write({
            'gp12_check': True, 'gp12_record_id': gp12record.id, 'gp12_date': china_date, 'gp12_time': current_time
        })
        # 添加产出记录
        tserialnumber = self.serialnumber_id
        outputdomain = [('serialnumber_id', '=', tserialnumber.id)]
        outputdomain += [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        tempout = self.env['aas.mes.production.output'].search(outputdomain, limit=1)
        if tempout:
            tempvalues = {'qualified': True, 'pass_onetime': False}
            if not tempout.employee_id:
                tempvalues.update({'employee_id': employeeid, 'employee_name': checkemployeestr})
            if not tempout.equipment_id:
                tempvalues['equipment_id'] = equipmentid
            tempout.write(tempvalues)
        else:
            self.env['aas.mes.production.output'].create({
                'product_id': tserialnumber.product_id.id, 'output_qty': 1.0,
                'output_date': fields.Datetime.to_china_today(), 'mesline_id': mesline.id,
                'schedule_id': False if not mesline.schedule_id else mesline.schedule_id.id,
                'workstation_id': workstation.id, 'equipment_id': equipmentid,
                'employee_id': employeeid, 'employee_name': checkemployeestr, 'serialnumber_id': tserialnumber.id
            })


    @api.model
    def action_loading_unpacking(self, checkdate=False):
        """获取GP12已检测并且还未打包标签的序列号
        :return:
        """
        values = {
            'success': True, 'message': '', 'serialnumberlist': [],
            'productid': 0, 'productcode': '', 'serialnumber': '', 'serialcount': '0'
        }
        if not checkdate:
            checkdate = fields.Datetime.to_china_today()
        tempdomain = [('gp12_check', '=', True), ('labeled', '=', False), ('gp12_date', '=', checkdate)]
        operationlist = self.env['aas.mes.operation'].search(tempdomain, order='gp12_time desc')
        if operationlist and len(operationlist) > 0:
            firstoperation = operationlist[0]
            values['productid'] = firstoperation.product_id.id
            customer_code = firstoperation.customer_product_code
            if customer_code:
                values['productcode'] = customer_code.replace('-', '')
            values.update({'serialnumber': firstoperation.serialnumber_name, 'serialcount': len(operationlist)})
            for toperation in operationlist:
                if not toperation.gp12_time:
                    checktime = fields.Datetime.to_china_string(fields.Datetime.now())
                else:
                    checktime = fields.Datetime.to_china_string(toperation.gp12_time)
                values['serialnumberlist'].append({
                    'serialnumber_id': toperation.serialnumber_id.id,
                    'serialnumber_content': ','.join([toperation.serialnumber_name, 'OK', checktime])
                })
        return values

    @api.model
    def action_loading_serialcount(self, meslineid):
        """加载当日终检扫描数量
        :param meslineid:
        :return:
        """
        values = {'success': True, 'message': '', 'serialcount': 0}
        mesline = self.env['aas.mes.line'].browse(meslineid)
        if not mesline:
            return values
        workorder = mesline.workorder_id
        if not workorder:
            return values
        productid, currentdate = workorder.product_id.id, fields.Datetime.to_china_string(fields.Datetime.now())[0:10]
        tdomain = [('product_id', '=', productid), ('mesline_id', '=', mesline.id), ('fqccheck_date', '=', currentdate)]
        values['serialcount'] = self.env['aas.mes.operation'].search_count(tdomain)
        return values


    @api.model
    def action_loading_operation_rework_list(self, operationid):
        """获取序列号的操作记录和返工清单
        :param operationid:
        :return:
        """
        values = {'success': True, 'message': '', 'recordlist': [], 'reworklist': []}
        toperation = self.env['aas.mes.operation'].browse(operationid)
        recordlist, reworklist = [], []
        if toperation.barcode_create:
            createrecord = toperation.barcode_record_id
            temployee, tequipment = createrecord.employee_id, createrecord.equipment_id
            recordlist.append({
                'result': True, 'sequence': 1, 'operation_name': u'生成条码',
                'employee_name': '' if not temployee else temployee.name,
                'equipment_code': '' if not tequipment else tequipment.code,
                'operation_time': fields.Datetime.to_china_string(createrecord.operate_time), 'scan_employee': ''
            })
        else:
            recordlist.append({
                'result': False, 'sequence': 1, 'operation_name': u'生成条码',
                'employee_name': '', 'equipment_code': '', 'operation_time': '', 'scan_employee': ''
            })
            if not values.get('message', False):
                values['message'] = u'请仔细检查，生成条码操作还未完成！'
        if toperation.function_test:
            ftestrecord = toperation.functiontest_record_id
            temployee, tequipment = ftestrecord.employee_id, ftestrecord.equipment_id
            recordlist.append({
                'result': True, 'sequence': 2, 'operation_name': u'功能测试',
                'employee_name': '' if not temployee else temployee.name,
                'equipment_code': '' if not tequipment else tequipment.code,
                'operation_time': fields.Datetime.to_china_string(ftestrecord.operate_time), 'scan_employee': ''
            })
        else:
            recordlist.append({
                'result': False, 'sequence': 2, 'operation_name': u'功能测试',
                'employee_name': '', 'equipment_code': '', 'operation_time': '', 'scan_employee': ''
            })
            if not values.get('message', False):
                values['message'] = u'请仔细检查，功能测试操作还未完成！'
        if toperation.final_quality_check:
            checkrecord = toperation.fqccheck_record_id
            scanemployee = '' if not checkrecord.scanning_employee else checkrecord.scanning_employee
            checkemployee = '' if not checkrecord.checking_employee else checkrecord.checking_employee

            temployee, tequipment = checkrecord.employee_id, checkrecord.equipment_id
            recordlist.append({
                'result': True, 'sequence': 3, 'operation_name': u'最终检查',
                'scan_employee': scanemployee, 'employee_name': checkemployee,
                'equipment_code': '' if not tequipment else tequipment.code,
                'operation_time': fields.Datetime.to_china_string(checkrecord.operate_time)
            })
        else:
            recordlist.append({
                'result': False, 'sequence': 3, 'operation_name': u'最终检查',
                'employee_name': '', 'equipment_code': '', 'operation_time': '', 'scan_employee': ''
            })
        values['recordlist'] = recordlist
        serialnumber = toperation.serialnumber_id
        if serialnumber.rework_lines and len(serialnumber.rework_lines) > 0:
            values['reworklist'] = [{
                'badmode_date': rework.badmode_date, 'state': REWORKSTATEDICT[rework.state],
                'badmode_name': rework.badmode_id.name+'['+rework.badmode_id.code+']',
                'commiter': '' if not rework.commiter_id else rework.commiter_id.name,
                'commit_time': fields.Datetime.to_china_string(rework.commit_time),
                'repairer': '' if not rework.repairer_id else rework.repairer_id.name,
                'repair_time': fields.Datetime.to_china_string(rework.repair_time),
                'ipqcchecker': '' if not rework.ipqcchecker_id else rework.ipqcchecker_id.name,
                'ipqccheck_time': fields.Datetime.to_china_string(rework.ipqccheck_time)
            } for rework in serialnumber.rework_lines]
        return values


        




OPERATELIST = [('newbarcode', u'生成条码'), ('embedpiece', u'置入连接片'), ('functiontest', u'功能测试'),
               ('fqc', u'最终检查'), ('gp12', u'GP12检测'), ('ipqc', u'IPQC确认')]
OPERATEDICT = {'newbarcode': u'生成条码', 'embedpiece': u'置入连接片', 'functiontest': u'功能测试',
               'fqc': u'最终检查', 'gp12': u'GP12检测', 'ipqc': u'IPQC确认'}

# 生产操作记录
class AASMESOperationRecord(models.Model):
    _name = 'aas.mes.operation.record'
    _description = 'AAS MES Operation Record'
    _rec_name = 'serialnumber_id'
    _order = 'id desc'

    operation_id = fields.Many2one(comodel_name='aas.mes.operation', string=u'操作记录', ondelete='cascade')
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', index=True)
    serialnumber = fields.Char(string=u'序列号', copy=False)
    scanning_employee = fields.Char(string=u'扫描员工', copy=False, index=True)
    checking_employee = fields.Char(string=u'检查员工', copy=False, index=True)
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'操作员工', ondelete='restrict')
    operate_date = fields.Char(string=u'操作日期', copy=False)
    operate_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'操作用户', default=lambda self: self.env.user)
    operation_pass = fields.Boolean(string=u'操作通过', default=True, copy=False)
    operate_result = fields.Char(string=u'操作结果', copy=False)
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'操作设备', ondelete='restrict')
    operate_type = fields.Selection(selection=OPERATELIST, string=u'操作类型', copy=False)
    operate_name = fields.Char(string=u'操作名称', copy=False)

    @api.model
    def create(self, vals):
        if vals.get('operate_type', False):
            vals['operate_name'] = OPERATEDICT.get(vals.get('operate_type'), False)
        vals['operate_date'] = fields.Datetime.to_china_today()
        record = super(AASMESOperationRecord, self).create(vals)
        record.action_after_create()
        return record

    @api.one
    def action_after_create(self):
        operationvals = {}
        serialnumber = self.operation_id.serialnumber_id
        if serialnumber:
            self.write({'serialnumber': serialnumber.name, 'serialnumber_id': serialnumber.id})
        if self.operate_type == 'newbarcode':
            operationvals.update({'barcode_create': True, 'barcode_record_id': self.id})
        elif self.operate_type == 'embedpiece':
            operationvals.update({'embed_piece': True, 'embed_record_id': self.id})
        elif self.operate_type == 'functiontest':
            operationvals.update({'function_test': True, 'functiontest_record_id': self.id})
            if serialnumber.state == 'draft':
                serialnumber.write({'state': 'normal'})
        elif self.operate_type == 'fqc':
            if not serialnumber.stocked:
                operationvals['fqccheck_date'] = fields.Datetime.to_china_today()
            operationvals.update({'final_quality_check': True, 'fqccheck_record_id': self.id})
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
        _logger.info(u'序列号%s提交功能测试记录，开始时间：%s', serialnumber, fields.Datetime.now())
        equipment = self.env['aas.equipment.equipment'].search([('code', '=', equipment_code)], limit=1)
        if not equipment:
            result.update({'success': False, 'message': u'设备不存在或已经被删除，请仔细检查！'})
            return result
        if not equipment.mesline_id or not equipment.workstation_id:
            result.update({'success': False, 'message': u'设备还未设置产线或工位！'})
            return result
        employeeid, employeename, operationid = False, False, False
        mesline, workstation = equipment.mesline_id, equipment.workstation_id
        employeedomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        temployee = self.env['aas.mes.workstation.employee'].search(employeedomain, limit=1)
        if temployee:
            employeeid, employeename = temployee.employee_id.id, temployee.employee_id.name
        toperation = self.env['aas.mes.operation'].search([('serialnumber_name', '=', serialnumber)], limit=1)
        if toperation:
            operationid = toperation.id
        functiontestvals = {
            'employee_id': employeeid, 'operation_id': operationid, 'equipment_id': equipment.id,
            'operate_type': 'functiontest', 'serialnumber': serialnumber,
            'operation_pass': operation_pass, 'operate_result': operate_result
        }
        self.env['aas.mes.operation.record'].create(functiontestvals)
        if not operation_pass:
            toperation.write({'function_test': False, 'functiontest_record_id': False})
        _logger.info(u'序列号%s更新产出优率记录，开始时间：%s', serialnumber, fields.Datetime.now())
        # 添加或更新产出信息
        tserialnumber = toperation.serialnumber_id
        if not tserialnumber:
            return result
        tempdomain = [('serialnumber_id', '=', tserialnumber.id)]
        tempdomain += [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        tempoutput = self.env['aas.mes.production.output'].search(tempdomain, order='output_time desc', limit=1)
        if tempoutput:
            tempvalues = {'pass_onetime': False, 'qualified': operation_pass}
            if not tempoutput.employee_id:
                tempvalues.update({'employee_id': employeeid, 'employee_name': employeename})
            if not tempoutput.equipment_id:
                tempvalues['equipment_id'] = equipment.id
            tempoutput.write(tempvalues)
        else:
            self.env['aas.mes.production.output'].create({
                'product_id': tserialnumber.product_id.id, 'output_qty': 1.0,
                'output_date': fields.Datetime.to_china_today(), 'mesline_id': mesline.id,
                'schedule_id': False if not mesline.schedule_id else mesline.schedule_id.id,
                'workstation_id': workstation.id, 'equipment_id': equipment.id,
                'pass_onetime': operation_pass, 'qualified': operation_pass,
                'employee_id': employeeid, 'employee_name': employeename, 'serialnumber_id': tserialnumber.id
            })
        _logger.info(u'序列号%s提交功能测试记录，结束时间：%s', serialnumber, fields.Datetime.now())
        return result








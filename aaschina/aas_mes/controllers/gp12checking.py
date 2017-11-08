# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-10-19 13:27
"""

import logging
import werkzeug

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)


class AASMESGP12CheckingController(http.Controller):

    @http.route('/aasmes/gp12/checking', type='http', auth="user")
    def aasmes_gp12_checking(self):
        values = {'success': True, 'message': '', 'employeelist': []}
        loginuser = request.env.user
        values['checker'] = loginuser.name
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', loginuser.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return request.render('aas_mes.aas_gp12_checking', values)
        if lineuser.mesrole != 'gp12checker':
            values.update({'success': False, 'message': u'当前登录账号还未授权GP12'})
            return request.render('aas_mes.aas_gp12_checking', values)
        if not lineuser.workstation_id:
            values.update({'success': False, 'message': u'当前登录账号还未绑定GP12工位'})
            return request.render('aas_mes.aas_gp12_checking', values)
        if lineuser.workstation_id.employee_lines and len(lineuser.workstation_id.employee_lines) > 0:
            employeelist = []
            for employee in lineuser.workstation_id.employee_lines:
                employeelist.append({
                    'employee_id': employee.id,
                    'employee_name': employee.name, 'employee_code': employee.code
                })
        return request.render('aas_mes.aas_gp12_checking', values)


    @http.route('/aasmes/gp12/scanemployee', type='json', auth="user")
    def aasmes_gp12_scanemployee(self, barcode):
        values = {'success': True, 'message': '', 'employee_id': '0', 'employee_name': '', 'action': 'working'}
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', request.env.user.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return values
        if lineuser.mesrole != 'gp12checker':
            values.update({'success': False, 'message': u'当前登录账号还未授权GP12'})
            return values
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定GP12工位'})
            return values
        employee = request.env['aas.hr.employee'].search([('barcode', '=', barcode)], limit=1)
        if not employee:
            values.update({'success': False, 'message': u'员工卡扫描异常，请检查系统中是否存在该员工！'})
            return values
        values.update({'employee_id': employee.id, 'employee_name': employee.name})
        attendancedomain = [('employee_id', '=', employee.id), ('attend_done', '=', False)]
        mesattendance = request.env['aas.mes.work.attendance'].search(attendancedomain, limit=1)
        if mesattendance:
            mesattendance.action_done()
            values.update({'action': 'leave', 'message': u'亲，您已离岗了哦！'})
        else:
            attendancevals = {'employee_id': employee.id, 'mesline_id': mesline.id, 'workstation_id': workstation.id}
            equipmentdomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
            tequipment = request.env['aas.mes.workstation.equipment'].search(equipmentdomain, limit=1)
            if tequipment:
                attendancevals['equipment_id'] = tequipment.equipment_id.id
            try:
                request.env['aas.mes.work.attendance'].create(attendancevals)
            except ValidationError, ve:
                values.update({'success': False, 'message': ve.name})
                return values
            values['message'] = u'亲，您已上岗！努力工作吧，加油！'
        return values


    @http.route('/aasmes/gp12/scanserialnumber', type='json', auth="user")
    def aasmes_gp12_scan_serialnumber(self, barcode, employeeid, productcode=None):
        values = {'success': True, 'message': '', 'result': 'OK', 'functiontestlist': [], 'reworklist': []}
        tempoperation = self.env['aas.mes.operation'].search([('serialnumber_name', '=', barcode)], limit=1)
        if not tempoperation:
            values.update({
                'result': 'NG',
                'success': False, 'message': u'序列号异常，请检查您扫描的标签是否是一个正确的序列号！'
            })
            return values
        serialnumber = tempoperation.serialnumber_id
        values['productcode'] = serialnumber.customer_product_code.replace('-', '')
        if productcode and productcode!=values['productcode']:
            values.update({'success': False, 'message': u'序列号异常，请确认可能与其他序列号不是同类别的产品混入！！'})
            return values
        # 功能测试记录
        operatedomain = [('operation_id', '=', tempoperation.id), ('operate_type', '=', 'functiontest')]
        functiontestlist = request.env['aas.mes.operation.record'].search(operatedomain)
        if functiontestlist and len(functiontestlist) > 0:
            count = 1
            for record in functiontestlist:
                values['functiontestlist'].append({
                    'operate_no': count, 'operator_name': record.employee_id.name,
                    'operate_result': record.operate_result, 'operate_equipment': record.equipment_id.name,
                    'operate_time': fields.Datetime.to_timezone_string(record.operate_time, 'Asia/Shanghai')
                })
                count += 1
        # 返工记录
        serialnumber_name = serialnumber.name
        operation_time = fields.Datetime.to_timezone_string(fields.Datetime.now(), 'Asia/Shanghai')
        # 返工件
        if tempoperation.serialnumber_id.reworked:
            if not tempoperation.dorework:
                values['operate_result'] = ','.join([serialnumber_name, 'NG', operation_time])
                values.update({'message': u'序列号异常，正在等待维修！！', 'result': 'NG'})
                return values
            if not tempoperation.ipqc_check:
                values['operate_result'] = ','.join([serialnumber_name, 'NG', operation_time])
                values.update({'message': u'序列号异常，正在等待IPQC确认！！', 'result': 'NG'})
                return values
        if tempoperation.gp12_check:
            values['operate_result'] = ','.join([serialnumber_name, 'NG', operation_time])
            values.update({'message': u'GP12已操作，请不要重复操作！', 'result': 'NG'})
            return values
        if not tempoperation.function_test:
            values['operate_result'] = ','.join([serialnumber_name, 'NG', operation_time])
            values.update({'message': u'序列号异常，隔离板测试还没有操作！', 'result': 'NG'})
            return values
        if not tempoperation.final_quality_check:
            values['operate_result'] = ','.join([serialnumber_name, 'NG', operation_time])
            values.update({'message': u'序列号异常，最终检查还没有操作！！', 'result': 'NG'})
            return values
        gp12record = request.env['aas.mes.operation.record'].create({
            'operation_id': tempoperation.id, 'employee_id': employeeid, 'operate_result': 'OK',
            'operate_type': 'gp12'
        })
        tempoperation.write({'gp12_check': True, 'gp12_record_id': gp12record.id})
        values['operate_result'] = ','.join([serialnumber_name, 'OK', operation_time])
        return values





# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-11-4 12:57
"""

import logging
import werkzeug

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

class AASMESFinalCheckingController(http.Controller):

    @http.route('/aasmes/finalchecking', type='http', auth="user")
    def aasmes_finalchecking(self):
        values = {'success': True, 'message': '', 'employeelist': [], 'equipmentlist': [], 'workorder_id': '0'}
        loginuser = request.env.user
        values['checker'] = loginuser.name
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', loginuser.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return request.render('aas_mes.aas_finalchecking', values)
        values['mesline_name'] = lineuser.mesline_id.name
        if lineuser.mesrole != 'fqcchecker':
            values.update({'success': False, 'message': u'当前登录账号还未授权终检'})
            return request.render('aas_mes.aas_finalchecking', values)
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定终检工位！'})
            return request.render('aas_mes.aas_finalchecking', values)
        if not mesline.workorder_id:
            values.update({'success': False, 'message': u'当前产线还未指定生产工单，请联系领班分配生产工单！'})
            return request.render('aas_mes.aas_finalchecking', values)
        values.update({'workorder_id': mesline.workorder_id.id, 'workorder_name': mesline.workorder_id.name})
        values['workstation_name'] = workstation.name
        if workstation.employee_lines and len(workstation.employee_lines) > 0:
            values['employeelist'] = [{
                'employee_id': wemployee.employee_id.id,
                'employee_name': wemployee.employee_id.name,
                'employee_code': wemployee.employee_id.code
            } for wemployee in workstation.employee_lines]
        if workstation.equipment_lines and len(workstation.equipment_lines) > 0:
            values['equipmentlist'] = [wequipment.equipment_id.code for wequipment in workstation.equipment_lines]
        return request.render('aas_mes.aas_finalchecking', values)



    @http.route('/aasmes/finalchecking/scanemployee', type='json', auth="user")
    def aasmes_finalchecking_scanemployee(self, barcode):
        values = {
            'success': True, 'message': '', 'action': 'working',
            'employee_id': '0', 'employee_name': '', 'employee_code': ''
        }
        employee = request.env['aas.hr.employee'].search([('barcode', '=', barcode)], limit=1)
        if not employee:
            values.update({'success': False, 'message': u'员工卡扫描异常，请检查系统中是否存在该员工！'})
            return values
        values.update({'employee_id': employee.id, 'employee_name': employee.name, 'employee_code': employee.code})
        attendancedomain = [('employee_id', '=', employee.id), ('attend_done', '=', False)]
        mesattendance = request.env['aas.mes.work.attendance'].search(attendancedomain, limit=1)
        if mesattendance:
            mesattendance.action_done()
            values['action'] = 'leave'
            values.update({'success': True, 'message': u'亲，您已离岗了哦！'})
        else:
            lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', request.env.user.id)], limit=1)
            if not lineuser:
                values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
                return values
            if lineuser.mesrole != 'fqcchecker':
                values.update({'success': False, 'message': u'当前登录账号还未授权终检！'})
                return values
            workstation = lineuser.workstation_id
            if not workstation:
                values.update({'success': False, 'message': u'当前登录账号还未绑定终检工位'})
                return values
            attendancevals = {
                'employee_id': employee.id,
                'mesline_id': lineuser.mesline_id.id, 'workstation_id': lineuser.workstation_id.id
            }
            if workstation.equipment_lines and len(workstation.equipment_lines) > 0:
                attendancevals['equipment_id'] = workstation.equipment_lines[0].id
            request.env['aas.mes.work.attendance'].create(attendancevals)
            values['message'] = u'亲，您已上岗！努力工作吧，加油！'
        return values


    @http.route('/aasmes/finalchecking/scanserialnumber', type='json', auth="user")
    def aasmes_finalchecking_scanserialnumber(self, barcode):
        values = {'success': True, 'message': '', 'serialnumber': barcode}
        tempoperation = request.env['aas.mes.operation'].search([('serialnumber_name', '=', barcode)], limit=1)
        if not tempoperation:
            values.update({'success': False, 'message': u'请仔细检查您扫描的是否是序列号条码！'})
            return values
        serialnumber = tempoperation.serialnumber_id
        values.update({
            'rework': serialnumber.reworked, 'internal_code': serialnumber.internal_product_code,
            'customer_code': serialnumber.customer_product_code, 'operationid': tempoperation.id
        })
        recordlist, couldcheck = [], True
        if tempoperation.barcode_create:
            createrecord = tempoperation.barcode_record_id
            recordlist.append({
                'result': True, 'sequence': 1, 'operation_name': u'生成条码',
                'employee_name': '' if not createrecord.employee_id else createrecord.employee_id.name,
                'equipment_code': '' if not createrecord.equipment_id else createrecord.equipment_id.code,
                'operation_time': fields.Datetime.to_timezone_string(createrecord.operate_time, 'Asia/Shanghai')
            })
        else:
            recordlist.append({
                'result': False, 'sequence': 1, 'operation_name': u'生成条码',
                'employee_name': '', 'equipment_code': '', 'operation_time': ''
            })
            if not values.get('message', False):
                values['message'] = u'请仔细检查，生成条码操作还未完成！'
            couldcheck = False
        if tempoperation.function_test:
            ftestrecord = tempoperation.functiontest_record_id
            recordlist.append({
                'result': True, 'sequence': 2, 'operation_name': u'功能测试',
                'employee_name': '' if not ftestrecord.employee_id else ftestrecord.employee_id.name,
                'equipment_code': '' if not ftestrecord.equipment_id else ftestrecord.equipment_id.code,
                'operation_time': fields.Datetime.to_timezone_string(ftestrecord.operate_time, 'Asia/Shanghai')
            })
        else:
            recordlist.append({
                'result': False, 'sequence': 2, 'operation_name': u'功能测试',
                'employee_name': '', 'equipment_code': '', 'operation_time': ''
            })
            if not values.get('message', False):
                values['message'] = u'请仔细检查，功能测试操作还未完成！'
            couldcheck = False
        values['checkval'] = 'forbidden'
        if tempoperation.final_quality_check:
            checkrecord = tempoperation.fqccheck_record_id
            recordlist.append({
                'result': True, 'sequence': 3, 'operation_name': u'最终检查',
                'employee_name': '' if not checkrecord.employee_id else checkrecord.employee_id.name,
                'equipment_code': '' if not checkrecord.equipment_id else checkrecord.equipment_id.code,
                'operation_time': fields.Datetime.to_timezone_string(checkrecord.operate_time, 'Asia/Shanghai')
            })
            values['checkval'] = 'done'
        else:
            recordlist.append({
                'result': False, 'sequence': 3, 'operation_name': u'最终检查',
                'employee_name': '', 'equipment_code': '', 'operation_time': ''
            })
            if couldcheck:
                values['checkval'] = 'waiting'
        values['recordlist'] = recordlist
        return values



    @http.route('/aasmes/finalchecking/actionconfirm', type='json', auth="user")
    def aasmes_finalchecking_actionconfirm(self, workorderid, operationid):
        values = {'success': True, 'message': ''}
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', request.env.user.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return values
        values['mesline_name'] = lineuser.mesline_id.name
        if lineuser.mesrole != 'fqcchecker':
            values.update({'success': False, 'message': u'当前登录账号还未授权终检'})
            return values
        workstation = lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定终检工位！'})
            return values
        workorder = lineuser.mesline_id.workorder_id
        if not workorder or workorder.id != workorderid:
            values.update({'success': False, 'message': u'当前产线信息变化，请先刷新页面再继续操作！'})
            return values
        tempoperation = request.env['aas.mes.operation'].browse(operationid)
        tempemployee, tempequipment = False, False
        if workstation.employee_lines and len(workstation.employee_lines) > 0:
            tempemployee = workstation.employee_lines[0].employee_id.id
        if workstation.equipment_lines and len(workstation.equipment_lines) > 0:
            tempequipment = workstation.equipment_lines[0].equipment_id.id
        operationrecord = request.env['aas.mes.operation.record'].create({
            'operation_id': operationid, 'employee_id': tempemployee, 'equipment_id': tempequipment,
            'operator_id': request.env.user.id, 'operation_pass': True, 'operate_result': 'Pass', 'operate_type': 'fqc'
        })
        tempoperation.write({'fqccheck_record_id': operationrecord.id})
        outputresult = workorder.action_output(workorder.id, workorder.product_id.id, 1, serialnumber=tempoperation.serialnumber_name)
        if not outputresult['success']:
            values.update({'success': False, 'message': outputresult['message']})
            return values
        tempvals = workorder.action_consume(workorder.id, workorder.product_id.id)
        if tempvals['message']:
            values['message'] = tempvals['message']
        return values

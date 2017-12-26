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
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

REWORKSTATEDICT = {'commit': u'不良上报', 'repair': u'返工维修', 'ipqc': u'IPQC确认', 'done': u'完成'}

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
        if lineuser.mesrole != 'fqcchecker':
            values.update({'success': False, 'message': u'当前登录账号还未授权终检'})
            return request.render('aas_mes.aas_finalchecking', values)
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定终检工位！'})
            return request.render('aas_mes.aas_finalchecking', values)
        values.update({'mesline_name': mesline.name, 'workstation_name': workstation.name})
        if not mesline.workorder_id:
            values.update({'workorder_id': '0', 'workorder_name': ''})
        values['workstation_name'] = workstation.name
        wkdomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        employees = request.env['aas.mes.workstation.employee'].search(wkdomain)
        if employees and len(employees) > 0:
            values['employeelist'] = [{
                'employee_id': wemployee.employee_id.id,
                'employee_name': wemployee.employee_id.name, 'employee_code': wemployee.employee_id.code
            } for wemployee in employees]
        equipments = request.env['aas.mes.workstation.equipment'].search(wkdomain)
        if equipments and len(equipments) > 0:
            values['equipmentlist'] = [{
                'equipment_id': wequipment.equipment_id.id,
                'equipment_name': wequipment.equipment_id.name, 'equipment_code': wequipment.equipment_id.code
            } for wequipment in equipments]
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
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', request.env.user.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return values
        if lineuser.mesrole != 'fqcchecker':
            values.update({'success': False, 'message': u'当前登录账号还未授权终检！'})
            return values
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定终检工位'})
            return values
        values.update({'employee_id': employee.id, 'employee_name': employee.name, 'employee_code': employee.code})
        avalues = request.env['aas.mes.work.attendance'].action_scanning(employee, mesline, workstation)
        values.update(avalues)
        return values


    @http.route('/aasmes/finalchecking/scanserialnumber', type='json', auth="user")
    def aasmes_finalchecking_scanserialnumber(self, barcode):
        values = {'success': True, 'message': '', 'serialnumber': barcode, 'recordlist': [], 'reworklist': []}
        tempoperation = request.env['aas.mes.operation'].search([('serialnumber_name', '=', barcode)], limit=1)
        if not tempoperation:
            values.update({'success': False, 'message': u'请仔细检查您扫描的是否是序列号条码！'})
            return values
        values['badmode_name'] = ''
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
        if serialnumber.rework_lines and len(serialnumber.rework_lines) > 0:
            values['reworklist'] = [{
                'badmode_name': rework.badmode_id.name+'['+rework.badmode_id.code+']', 'badmode_date': rework.badmode_date,
                'commiter': '' if not rework.commiter_id else rework.commiter_id.name,
                'commit_time': '' if not rework.commit_time else fields.Datetime.to_timezone_string(rework.commit_time, 'Asia/Shanghai'),
                'repairer': '' if not rework.repairer_id else rework.repairer_id.name,
                'repair_time': '' if not rework.repair_time else fields.Datetime.to_timezone_string(rework.repair_time, 'Asia/Shanghai'),
                'ipqcchecker': '' if not rework.ipqcchecker_id else rework.ipqcchecker_id.name,
                'ipqccheck_time': '' if not rework.ipqccheck_time else fields.Datetime.to_timezone_string(rework.ipqccheck_time, 'Asia/Shanghai'),
                'state': REWORKSTATEDICT[rework.state]
            } for rework in serialnumber.rework_lines]
            currentrework = serialnumber.rework_lines[0]
            values['badmode_name'] = currentrework.badmode_id.name
        return values

    @http.route('/aasmes/finalchecking/reworkconfirm', type='json', auth="user")
    def aasmes_finalchecking_reworkconfirm(self, operationid):
        values = {'success': True, 'message': ''}
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', request.env.user.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return values
        values['mesline_name'] = lineuser.mesline_id.name
        if lineuser.mesrole != 'fqcchecker':
            values.update({'success': False, 'message': u'当前登录账号还未授权终检'})
            return values
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定终检工位！'})
            return values
        tempoperation = request.env['aas.mes.operation'].browse(operationid)
        tempoperation.action_finalcheck(mesline, workstation)
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
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定终检工位！'})
            return values
        workorder = lineuser.mesline_id.workorder_id
        if not workorder or workorder.id != workorderid:
            values.update({'success': False, 'message': u'当前产线信息变化，请先刷新页面再继续操作！'})
            return values
        tempoperation = request.env['aas.mes.operation'].browse(operationid)
        tvalues = request.env['aas.mes.workorder'].action_flowingline_output(workorder, mesline, workstation,
                                                                             tempoperation.serialnumber_name)
        if not tvalues.get('success', False):
            return tvalues
        return values



    @http.route('/aasmes/finalchecking/actionconsume', type='json', auth="user")
    def aasmes_finalchecking_actionconsume(self):
        values = {'success': True, 'message': ''}
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', request.env.user.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return values
        values['mesline_name'] = lineuser.mesline_id.name
        if lineuser.mesrole != 'fqcchecker':
            values.update({'success': False, 'message': u'当前登录账号还未授权终检'})
            return values
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定终检工位！'})
            return values
        workorder = mesline.workorder_id
        if not workorder:
            values.update({'success': False, 'message': u'当前产线还未指定生产工单，请联系领班设置生产工单！'})
            return values
        cresult = workorder.action_consume(workorder.id, workorder.product_id.id)
        if not cresult['success']:
            values.update(cresult)
            return values
        # 根据结单方式判断什么时候自动结单
        closeorder = request.env['ir.values'].sudo().get_default('aas.mes.settings', 'closeorder_method')
        if closeorder == 'equal':
            if float_compare(workorder.output_qty, workorder.input_qty, precision_rounding=0.000001) >= 0.0:
                workorder.action_done()
        else:
            # total
            total_qty = workorder.output_qty + workorder.scrap_qty
            if float_compare(total_qty, workorder.input_qty, precision_rounding=0.000001) >= 0.0:
                workorder.action_done()
        values['message'] = u'结单成功！'
        return values

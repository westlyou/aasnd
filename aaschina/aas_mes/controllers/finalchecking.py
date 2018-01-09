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
        values.update({
            'checker': loginuser.name, 'equipment_id': '0', 'equipment_code': '',
            'workorder_id': '0', 'workorder_name': '', 'customer_code': '', 'product_code': ''
        })
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
        workorder = mesline.workorder_id
        if workorder:
            temproduct = workorder.product_id
            values.update({
                'workorder_id': workorder.id, 'workorder_name': workorder.name, 'product_code': temproduct.default_code,
                'customer_code': '' if not temproduct.customer_product_code else temproduct.customer_product_code
            })
        wkdomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        employees = request.env['aas.mes.workstation.employee'].search(wkdomain)
        if employees and len(employees) > 0:
            values['employeelist'] = [{
                'employee_id': wemployee.employee_id.id,
                'employee_name': wemployee.employee_id.name, 'employee_code': wemployee.employee_id.code
            } for wemployee in employees]
        equipments = request.env['aas.mes.workstation.equipment'].search(wkdomain)
        if equipments and len(equipments) > 0:
            tempequipment = equipments[0].equipment_id
            values.update({'equipment_id': tempequipment.id, 'equipment_code': tempequipment.code})
        return request.render('aas_mes.aas_finalchecking', values)


    @http.route('/aasmes/finalchecking/serialcount', type='json', auth="user")
    def aasmes_finalchecking_serialcount(self):
        values = {'success': True, 'message': '', 'serialcount': '0'}
        loginuser = request.env.user
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', loginuser.id)], limit=1)
        if not lineuser:
            return values
        mesline = lineuser.mesline_id
        if not mesline:
            return values
        workorder = mesline.workorder_id
        if not workorder:
            return values
        tempvalues = request.env['aas.mes.operation'].action_loading_serialcount(mesline.id)
        values['serialcount'] = tempvalues['serialcount']
        return values



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
        values = {
            'success': True, 'message': '', 'serialnumber': barcode, 'done': False,
            'recordlist': [], 'reworklist': [], 'rework': False, 'serialcount': 0,
            'operationid': '0', 'internal_code': '', 'customer_code': '', 'badmode_name': ''
        }
        loginuser = request.env.user
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', loginuser.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录员工还未绑定产线工位'})
            return values
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not mesline or not workstation:
            values.update({'success': False, 'message': u'当前登录员工还未绑定产线工位'})
            return values
        workorder = mesline.workorder_id
        tempoperation = request.env['aas.mes.operation'].search([('serialnumber_name', '=', barcode)], limit=1)
        if not tempoperation:
            values.update({'success': False, 'message': u'请仔细检查是否是有效条码'})
            return values
        tempvalues = request.env['aas.mes.operation'].action_loading_operation_rework_list(tempoperation.id)
        values.update({'recordlist': tempvalues['recordlist'], 'reworklist': tempvalues['reworklist']})
        serialnumber = tempoperation.serialnumber_id
        values.update({
            'rework': serialnumber.reworked, 'internal_code': serialnumber.internal_product_code,
            'customer_code': serialnumber.customer_product_code, 'operationid': tempoperation.id
        })
        if not tempoperation.function_test:
            values.update({'success': False, 'message': u'功能测试未完成或未通过'})
            return values
        if tempoperation.final_quality_check:
            tempvalues = request.env['aas.mes.operation'].action_loading_serialcount(mesline.id)
            values['serialcount'] = tempvalues['serialcount']
            values.update({'message': u'已扫描，请不要重复操作', 'done': True})
            return values
        if serialnumber.reworked:
            if serialnumber.rework_lines and len(serialnumber.rework_lines) > 0:
                currentrework = serialnumber.rework_lines[0]
                values['badmode_name'] = currentrework.badmode_id.name
            values['message'] = u'%s重工，请仔细检查确认'% values['badmode_name']
            return values
        tvalues = request.env['aas.mes.workorder'].action_flowingline_output(workorder, barcode)
        if not tvalues.get('success', False):
            values.update(tvalues)
            return values
        tempoperation.action_finalcheck(mesline, workstation)
        orvalues = request.env['aas.mes.operation'].action_loading_operation_rework_list(tempoperation.id)
        values.update({'recordlist': orvalues['recordlist'], 'reworklist': orvalues['reworklist']})
        scvalues = request.env['aas.mes.operation'].action_loading_serialcount(mesline.id)
        values['serialcount'] = scvalues['serialcount']
        return values

    @http.route('/aasmes/finalchecking/loadrecordlist', type='json', auth="user")
    def aasmes_finalchecking_loadrecordlist(self, operationid):
        return request.env['aas.mes.operation'].action_loading_operation_rework_list(operationid)



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
        if not tempoperation.final_quality_check:
            tempoperation.action_finalcheck(mesline, workstation)
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

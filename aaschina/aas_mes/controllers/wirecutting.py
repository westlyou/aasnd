# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-11-3 11:00
"""

import logging
import werkzeug

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

ORDERSTATESDICT = {'draft': u'草稿', 'confirm': u'确认', 'producing': u'生产', 'pause': u'暂停', 'done': u'完成'}

class AASMESWireCuttingController(http.Controller):

    @http.route('/aasmes/wirecutting', type='http', auth="user")
    def aasmes_wirecutting(self):
        values = {'success': True, 'message': '', 'employeelist': []}
        loginuser = request.env.user
        values['checker'] = loginuser.name
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', loginuser.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return request.render('aas_mes.aas_wirecutting', values)
        values['mesline_name'] = lineuser.mesline_id.name
        if lineuser.mesrole != 'wirecutter':
            values.update({'success': False, 'message': u'当前登录账号还未授权切线'})
            return request.render('aas_mes.aas_wirecutting', values)
        workstation = lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定切线工位！'})
            return request.render('aas_mes.aas_wirecutting', values)
        values['workstation_name'] = workstation.name
        if workstation.employee_lines and len(workstation.employee_lines) > 0:
            values['employeelist'] = [{
                'employee_id': wemployee.employee_id.id,
                'employee_name': wemployee.employee_id.name,
                'employee_code': wemployee.employee_id.code
            } for wemployee in workstation.employee_lines]
        return request.render('aas_mes.aas_wirecutting', values)


    @http.route('/aasmes/wirecutting/scanemployee', type='json', auth="user")
    def aasmes_wirecutting_scanemployee(self, barcode):
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
            if lineuser.mesrole != 'wirecutter':
                values.update({'success': False, 'message': u'当前登录账号还未授权下线！'})
                return values
            workstation = lineuser.workstation_id
            if not workstation:
                values.update({'success': False, 'message': u'当前登录账号还未绑定下线工位'})
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


    @http.route('/aasmes/wirecutting/scanwireorder', type='json', auth="user")
    def aasmes_wirecutting_scanwireorder(self, barcode):
        values = {'success': True, 'message': ''}
        wireorder = request.env['aas.mes.wireorder'].search([('name', '=', barcode)], limit=1)
        if not wireorder:
            values.update({'success': False, 'message': u'请仔细检查确认扫描工单是否在系统中存在！'})
            return values
        if wireorder.state not in ['wait', 'producing']:
            values.update({'success': False, 'message': u'请仔细检查线材工单状态异常可能还未投产或已经完成！'})
            return values
        if not wireorder.workorder_lines or len(wireorder.workorder_lines) <= 0:
            values.update({'success': False, 'message': u'请仔细检查线材工单没有下线工单需要操作！'})
            return values
        values.update({
            'wireorder_id': wireorder.id, 'wireorder_name': wireorder.name,
            'product_code': wireorder.product_id.default_code, 'product_qty': wireorder.product_qty
        })
        workorderlist = [{
            'id': workorder.id, 'order_name': workorder.name, 'product_code': workorder.product_code,
            'product_uom': workorder.product_id.uom_id.name, 'product_qty': workorder.product_qty,
            'output_qty': workorder.output_qty, 'state_name': ORDERSTATESDICT[workorder.state]
        } for workorder in wireorder.workorder_lines]
        values['workorderlist'] = workorderlist
        return values


    @http.route('/aasmes/wirecutting/scancontainer', type='json', auth="user")
    def aasmes_wirecutting_scancontainer(self, barcode):
        values = {'success': True, 'message': ''}
        container = request.env['aas.container'].search([('barcode', '=', barcode)], limit=1)
        if not container:
            values.update({'success': False, 'message': u'请仔细检查确认扫描的容器是否在系统中存在！'})
            return values
        values.update({'container_id': container.id, 'container_name': container.name})
        return values


    @http.route('/aasmes/wirecutting/output', type='json', auth="user")
    def aasmes_wirecutting_output(self, workorder_id, output_qty, container_id):
        values = {'success': True, 'message': ''}
        loginuser = request.env.user
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', loginuser.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return values
        values['mesline_name'] = lineuser.mesline_id.name
        if lineuser.mesrole != 'wirecutter':
            values.update({'success': False, 'message': u'当前登录账号还未授权切线'})
            return request.render('aas_mes.aas_wirecutting', values)
        workstation = lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定切线工位！'})
            return values
        workorder = request.env['aas.mes.workorder'].browse(workorder_id)
        product = workorder.product_id
        try:
            workorder.action_output(workorder_id, product.id, output_qty, container_id)
        except UserError,ue:
            values.update({'success': False, 'message':ue.name})
            return values
        consumeresult = workorder.action_consume(workorder_id, product.id)
        if not consumeresult.get('success', False):
            values.update(consumeresult)
            return values
        values.update({'output_qty': workorder.output_qty, 'state_name': ORDERSTATESDICT[workorder.state]})
        return values

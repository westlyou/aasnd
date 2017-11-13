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
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

ORDERSTATESDICT = {'draft': u'草稿', 'confirm': u'确认', 'producing': u'生产', 'pause': u'暂停', 'done': u'完成'}

class AASMESWireCuttingController(http.Controller):

    @http.route('/aasmes/wirecutting', type='http', auth="user")
    def aasmes_wirecutting(self):
        values = {'success': True, 'message': '', 'materiallist': [], 'employee_id': '0', 'employee_name': ''}
        loginuser = request.env.user
        values['checker'] = loginuser.name
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', loginuser.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return request.render('aas_mes.aas_wirecutting', values)
        if lineuser.mesrole != 'wirecutter':
            values.update({'success': False, 'message': u'当前登录账号还未授权切线'})
            return request.render('aas_mes.aas_wirecutting', values)
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定切线工位！'})
            return request.render('aas_mes.aas_wirecutting', values)
        values.update({'mesline_name': mesline.name, 'workstation_name': workstation.name})
        employeelist = request.env['aas.mes.workstation.employee'].search([('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)])
        if employeelist and len(employeelist) > 0:
            temployee = employeelist[0].employee_id
            values.update({'employee_id': temployee.id, 'employee_name': temployee.name+'['+temployee.code+']'})
        feedmateriallist = request.env['aas.mes.feedmaterial'].search([('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)])
        if feedmateriallist and len(feedmateriallist) > 0:
            values['materiallist'] = [{
                'material_name': feedmaterial.material_id.default_code+'['+feedmaterial.material_lot.name+']',
                'material_qty': feedmaterial.material_qty
            } for feedmaterial in feedmateriallist]
        return request.render('aas_mes.aas_wirecutting', values)


    @http.route('/aasmes/wirecutting/scanemployee', type='json', auth="user")
    def aasmes_wirecutting_scanemployee(self, barcode, equipment_id):
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
        if lineuser.mesrole != 'wirecutter':
            values.update({'success': False, 'message': u'当前登录账号还未授权下线！'})
            return values
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定下线工位'})
            return values
        values.update({'employee_id': employee.id, 'employee_name': employee.name+'['+employee.code+']'})
        attendancedomain = [('employee_id', '=', employee.id), ('attend_done', '=', False)]
        mesattendance = request.env['aas.mes.work.attendance'].search(attendancedomain, limit=1)
        if mesattendance:
            mesattendance.action_done()
            values['action'] = 'leave'
            values.update({'success': True, 'message': u'亲，您已离岗了哦！'})
        else:
            attendancevals = {'employee_id': employee.id, 'mesline_id': mesline.id, 'workstation_id': workstation.id}
            if equipment_id:
                attendancevals['equipment_id'] = equipment_id
            request.env['aas.mes.work.attendance'].create(attendancevals)
            values['message'] = u'亲，您已上岗！努力工作吧，加油！'
        return values

    @http.route('/aasmes/wirecutting/scanequipment', type='json', auth="user")
    def aasmes_wirecutting_scanequipment(self, barcode):
        values = {
            'success': True, 'message': '', 'equipment_id': '0', 'equipment_code': ''
        }
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', request.env.user.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return values
        if lineuser.mesrole != 'wirecutter':
            values.update({'success': False, 'message': u'当前登录账号还未授权下线！'})
            return values
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定下线工位'})
            return values
        equipment = request.env['aas.equipment.equipment'].search([('barcode', '=', barcode)], limit=1)
        if not equipment:
            values.update({'success': False, 'message': u'系统并未搜索到此设备，请仔细检查！'})
            return values
        values.update({'equipment_id': equipment.id, 'equipment_code': equipment.code})
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
            'product_uom': workorder.product_id.uom_id.name, 'product_qty': workorder.input_qty,
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


    @http.route('/aasmes/wirecutting/scanmaterial', type='json', auth="user")
    def aasmes_wirecutting_scanmaterial(self, barcode):
        values = {'success': True, 'message': ''}
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', request.env.user.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return values
        if lineuser.mesrole != 'wirecutter':
            values.update({'success': False, 'message': u'当前登录账号还未授权切线'})
            return values
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定切线工位！'})
            return values
        label = request.env['aas.product.label'].search([('barcode', '=', barcode)], limit=1)
        if not label:
            values.update({'success': False, 'message': u'请仔细检查确认扫描的标签是否在系统中存在！'})
            return values
        if not mesline.location_production_id or (not mesline.location_material_list or len(mesline.location_material_list)<= 0):
            values.update({'success': False, 'message': u'产线%s的成品原料库位还未设置，请联系相关人员设置！'% mesline.name})
            return values
        locationids = [mlocation.location_id.id for mlocation in mesline.location_material_list]
        locationids.append(mesline.location_production_id.id)
        locationlist = request.env['stock.location'].search([('id', 'child_of', locationids)])
        if label.location_id.id not in locationlist.ids:
            values.update({'success': False, 'message': u'当前标签不在产线%s的线边库，请不要扫描此标签！'% mesline.name})
            return values
        feeddomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        feeddomain.extend([('material_id', '=', label.product_id.id), ('material_lot', '=', label.product_lot.id)])
        feedmaterial = request.env['aas.mes.feedmaterial'].search(feeddomain, limit=1)
        if feedmaterial:
            values.update({'success': False, 'message': u'此物料的相同批次已经上料，请不要重复操作！'})
            return values
        else:
            feedmaterial = request.env['aas.mes.feedmaterial'].create({
                'mesline_id': mesline.id, 'workstation_id': workstation.id,
                'material_id': label.product_id.id, 'material_lot': label.product_lot.id
            })
        values.update({
            'material_name': label.product_code+'['+label.product_lotname+']', 'material_qty': feedmaterial.material_qty
        })
        return values


    @http.route('/aasmes/wirecutting/output', type='json', auth="user")
    def aasmes_wirecutting_output(self, workorder_id, output_qty, container_id, employee_id, equipment_id):
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
        if float_compare(workorder.output_qty+output_qty, workorder.input_qty, precision_rounding=0.000001) > 0.0:
            values.update({'success': False, 'message': u'总产出数量不可以大于计划生产数量，请仔细检查！'})
            return values
        outputresult = request.env['aas.mes.wireorder'].action_wirecutting_output(workorder.id, output_qty,
                                                                   container_id,  workstation.id, employee_id, equipment_id)
        if not outputresult['success']:
            values.update(outputresult)
            return values
        return values



    @http.route('/aasmes/wirecutting/actionrefresh', type='json', auth="user")
    def aasmes_wirecutting_refresh(self, wireorder_id):
        values = {'success': True, 'message': '', 'workorderlist': [], 'materiallist': []}
        loginuser = request.env.user
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', loginuser.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return values
        mesline = lineuser.mesline_id
        values['mesline_name'] = mesline.name
        if lineuser.mesrole != 'wirecutter':
            values.update({'success': False, 'message': u'当前登录账号还未授权切线'})
            return request.render('aas_mes.aas_wirecutting', values)
        workstation = lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定切线工位！'})
            return values
        values['workstation_name'] = workstation.name
        wireorder = request.env['aas.mes.wireorder'].browse(wireorder_id)
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
            'product_uom': workorder.product_id.uom_id.name, 'product_qty': workorder.input_qty,
            'output_qty': workorder.output_qty, 'state_name': ORDERSTATESDICT[workorder.state]
        } for workorder in wireorder.workorder_lines]
        values['workorderlist'] = workorderlist
        feedmateriallist = request.env['aas.mes.feedmaterial'].search([('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)])
        if feedmateriallist and len(feedmateriallist) > 0:
            values['materiallist'] = [{
                'material_name': feedmaterial.material_id.default_code+'['+feedmaterial.material_lot.name+']',
                'material_qty': feedmaterial.material_qty
            } for feedmaterial in feedmateriallist]
        return values

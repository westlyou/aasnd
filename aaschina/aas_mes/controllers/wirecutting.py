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
        employeedomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        employeelist = request.env['aas.mes.workstation.employee'].search(employeedomain)
        if employeelist and len(employeelist) > 0:
            temployee = employeelist[0].employee_id
            values.update({'employee_id': temployee.id, 'employee_name': temployee.name+'['+temployee.code+']'})
        feedmateriallist = request.env['aas.mes.feedmaterial'].search([('mesline_id', '=', mesline.id)])
        if feedmateriallist and len(feedmateriallist) > 0:
            materialdict = {}
            for feedmaterial in feedmateriallist:
                mkey = 'M'+str(feedmaterial.material_id.id)
                if mkey not in materialdict:
                    materialdict[mkey] = {
                        'material_name': feedmaterial.material_id.default_code,
                        'material_qty': feedmaterial.material_qty
                    }
                else:
                    materialdict[mkey]['material_qty'] += feedmaterial.material_qty
            values['materiallist'] = materialdict.values()
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
        equipment = False if not equipment_id else request.env['aas.equipment.equipment'].browse(equipment_id)
        avalues = request.env['aas.mes.work.attendance'].action_scanning(employee, mesline, workstation, equipment)
        values.update(avalues)
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
            'output_qty': workorder.output_qty, 'state_name': ORDERSTATESDICT[workorder.state], 'scrap_qty': workorder.scrap_qty
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
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', request.env.user.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return values
        if lineuser.mesrole != 'wirecutter':
            values.update({'success': False, 'message': u'当前登录账号还未授权切线'})
            return values
        mesline = lineuser.mesline_id
        if not mesline.location_production_id or (not mesline.location_material_list or len(mesline.location_material_list) <= 0):
            values.update({'success': False, 'message': u'当前产线还未设置成品和原料线边库，请联系相关人员设置'})
            return values
        workstation = lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'下线工位还未设置！'})
            return values
        if not container.isempty:
            values.update({'success': False, 'message': u'容器已被占用，暂不可以使用！'})
            return values
        container.action_domove(mesline.location_production_id.id, movenote=u'线材产出容器自动调拨')
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
        feeddomain = [('mesline_id', '=', mesline.id)]
        feeddomain += [('material_id', '=', label.product_id.id), ('material_lot', '=', label.product_lot.id)]
        feedmaterial = request.env['aas.mes.feedmaterial'].search(feeddomain, limit=1)
        if feedmaterial:
            feedmaterial.action_refresh_stock()
            values.update({'success': False, 'message': u'此物料的相同批次已经上料，请不要重复操作！'})
            return values
        else:
            request.env['aas.mes.feedmaterial'].create({
                'mesline_id': mesline.id, 'material_id': label.product_id.id, 'material_lot': label.product_lot.id
            })
        tempdomain = [('mesline_id', '=', mesline.id), ('material_id', '=', label.product_id.id)]
        feedmateriallist = request.env['aas.mes.feedmaterial'].search(tempdomain)
        values.update({
            'material_name': label.product_code,
            'material_qty': sum([feedmaterial.material_qty for feedmaterial in feedmateriallist])
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
            return values
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


    @http.route('/aasmes/wirecutting/scrap', type='json', auth="user")
    def aasmes_wirecutting_scrap(self, workorder_id, scrap_qty, employee_id, equipment_id):
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
        scrapresult = request.env['aas.mes.wireorder'].action_wirecutting_scrap(workorder_id, scrap_qty, workstation.id, employee_id, equipment_id)
        if not scrapresult['success']:
            values.update(scrapresult)
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
            'output_qty': workorder.output_qty, 'state_name': ORDERSTATESDICT[workorder.state], 'scrap_qty': workorder.scrap_qty
        } for workorder in wireorder.workorder_lines]
        values['workorderlist'] = workorderlist
        feedmateriallist = request.env['aas.mes.feedmaterial'].search([('mesline_id', '=', mesline.id)])
        if feedmateriallist and len(feedmateriallist) > 0:
            materialdict = {}
            for feedmaterial in feedmateriallist:
                mkey = 'M'+str(feedmaterial.material_id.id)
                if mkey in materialdict:
                    materialdict[mkey]['material_qty'] += feedmaterial.material_qty
                else:
                    materialdict[mkey] = {
                        'material_name': feedmaterial.material_id.default_code,
                        'material_qty': feedmaterial.material_qty
                    }
            values['materiallist'] = materialdict.values()
        return values


    @http.route('/aasmes/wirecutting/validate/producttest', type='json', auth="user")
    def aasmes_wirecutting_validate_producttest(self, workorderid, testtype):
        values = {'success': True, 'message': '', 'producttest_id': '0'}
        loginuser = request.env.user
        userdomain = [('lineuser_id', '=', loginuser.id), ('mesrole', '=', 'wirecutter')]
        lineuser = request.env['aas.mes.lineusers'].search(userdomain, limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return values
        workstation = lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定切线工位！'})
            return values
        workorder = request.env['aas.mes.workorder'].browse(workorderid)
        tdomain = [('product_id', '=', workorder.wireorder_id.product_id.id), ('workstation_id', '=', workstation.id)]
        producttest = request.env['aas.mes.producttest'].search(tdomain, limit=1)
        if not producttest:
            product_code = workorder.wireorder_id.product_code
            values.update({'success': False, 'message': u'%s还未设置检测参数，请联系相关人员设置！'% product_code})
            return values
        paramvals = request.env['aas.mes.producttest'].action_loading_parameters(producttest, testtype)
        if not paramvals.get('success', False):
            values.update(paramvals)
            return values
        return values


    @http.route('/aasmes/wirecutting/producttest/<string:testtype>/<string:testid>', type='http', auth="user")
    def aasmes_wirecutting_producttest(self, testtype, testid):
        values = {
            'success': True, 'message': '', 'producttest_id': '0', 'parameters': [],
            'product_id': '0', 'product_code': '', 'wire_id': '0', 'wire_code': '',
            'equipment_id': '0', 'equipment_code': '', 'employee_id': '0', 'employee_name': '',
            'workstation_id': '0', 'workstation_name': '', 'mesline_id': '0', 'mesline_name': '',
            'wireorder_id': '0', 'wireorder_name': '', 'workorder_id': '0', 'testtype': testtype
        }
        loginuser = request.env.user
        values['checker'] = loginuser.name
        if testtype not in ['firstone', 'lastone', 'random']:
            values.update({'success': False, 'message': u'检测分类值异常，请确认是否是从有效的途径打开此页面！'})
            return request.render('aas_mes.aas_wirecutting_producttest', values)
        userdomain = [('lineuser_id', '=', loginuser.id), ('mesrole', '=', 'wirecutter')]
        lineuser = request.env['aas.mes.lineusers'].search(userdomain, limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return request.render('aas_mes.aas_wirecutting_producttest', values)
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定工位，无法继续其他操作！'})
            return request.render('aas_mes.aas_wirecutting_producttest', values)
        testids = testid.split('-')
        workorderid, equipmentid, employeeid = int(testids[0]), int(testids[1]), int(testids[2])
        workorder = request.env['aas.mes.workorder'].browse(workorderid)
        if not workorder or not workorder.wireorder_id:
            values.update({'success': False, 'message': u'请仔细检查确认，当前工单是否是有效的线材工单！'})
            return request.render('aas_mes.aas_wirecutting_producttest', values)
        equipment = request.env['aas.equipment.equipment'].browse(equipmentid)
        if not equipment:
            values.update({'success': False, 'message': u'请仔细检查确认，当前设备是否是一个有效的下线设备！'})
            return request.render('aas_mes.aas_wirecutting_producttest', values)
        employee = request.env['aas.hr.employee'].browse(employeeid)
        if not employee:
            values.update({'success': False, 'message': u'请仔细检查确认，当前员工信息无效！'})
            return request.render('aas_mes.aas_wirecutting_producttest', values)
        wireorder = workorder.wireorder_id
        values.update({
            'product_id': wireorder.product_id.id, 'product_code': wireorder.product_code,
            'wire_id': workorder.product_id.id, 'wire_code': workorder.product_id.default_code,
            'equipment_id': equipment.id, 'equipment_code': equipment.code,
            'employee_id': employee.id, 'employee_name': employee.name,
            'workstation_id': workstation.id, 'workstation_name': workstation.name,
            'mesline_id': mesline.id, 'mesline_name': mesline.name,
            'wireorder_id': wireorder.id, 'wireorder_name': wireorder.name, 'workorder_id': workorder.id
        })
        testdomain = [('product_id', '=', wireorder.product_id.id), ('workstation_id', '=', workstation.id)]
        producttest = request.env['aas.mes.producttest'].search(testdomain, limit=1)
        if not producttest:
            values.update({'success': False, 'message': u'请仔细检查确认，当前还未设置检测信息！'})
            return request.render('aas_mes.aas_wirecutting_producttest', values)
        values['producttest_id'] = producttest.id
        paramvals = request.env['aas.mes.producttest'].action_loading_parameters(producttest, testtype)
        values.update(paramvals)
        return request.render('aas_mes.aas_wirecutting_producttest', values)


    @http.route('/aasmes/wirecutting/producttest/docommit', type='json', auth="user")
    def aasmes_wirecutting_producttest_docommit(self, testtype, workorderid, producttestid, equipmentid, employeeid, parameters):
        values = {'success': True, 'message': '', 'orderid': '0'}
        loginuser = request.env.user
        userdomain = [('lineuser_id', '=', loginuser.id), ('mesrole', '=', 'wirecutter')]
        lineuser = request.env['aas.mes.lineusers'].search(userdomain, limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return values
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定切线工位！'})
            return values
        workorder = request.env['aas.mes.workorder'].browse(workorderid)
        if not workorder.wireorder_id:
            values.update({'success': False, 'message': u'工单异常，当前工单可能不是一个有效的线材工单！'})
            return values
        if not parameters or len(parameters) <= 0:
            values.update({'success': False, 'message': u'工单异常，检测参数异常，未获取到检测参数信息！'})
            return values
        productid = workorder.product_id.id
        vdtvals = request.env['aas.mes.workorder'].action_validate_consume(workorderid, productid, 1.0)
        if not vdtvals.get('success', False):
            values.update(vdtvals)
            return values
        badmodedict = {'random': 'T0053', 'firstone': 'T0054', 'lastone': 'T0055'}
        badmode = request.env['aas.mes.badmode'].search([('code', '=', badmodedict[testtype])], limit=1)
        if badmode:
            badlines = [{'badmode_id': badmode.id, 'badmode_qty': 1.0}]
            optvals = request.env['aas.mes.workorder'].action_output(workorderid, productid, 1.0, badmode_lines=badlines)
            if not optvals.get('success', False):
                values.update(optvals)
                return values
            request.env['aas.mes.workorder'].action_consume(workorderid, productid)
        wireorder = workorder.wireorder_id
        testorder = request.env['aas.mes.producttest.order'].create({
            'producttest_id': producttestid, 'product_id': wireorder.product_id.id,
            'workstation_id': workstation.id, 'mesline_id': mesline.id, 'equipment_id': equipmentid,
            'test_type': testtype, 'employee_id': employeeid, 'workorder_id': workorder.id,
            'wireorder_id': wireorder.id, 'state': 'confirm',
            'schedule_id': False if not mesline.schedule_id else mesline.schedule_id.id,
            'order_lines': [(0, 0, tparam) for tparam in parameters]
        })
        testorder.write({'qualified': all([orderline.qualified for orderline in testorder.order_lines])})
        values['orderid'] = testorder.id
        return values


    @http.route('/aasmes/wirecutting/producttest/orderdetail/<int:orderid>', type='http', auth="user")
    def aasmes_wirecutting_orderdetail(self, orderid):
        values = {'success': True, 'message': '', 'checker': request.env.user.name}
        testdict = {'firstone': u'首件检测', 'lastone': u'末件检测', 'random': u'抽样检测'}
        testorder = request.env['aas.mes.producttest.order'].browse(orderid)
        values.update({
            'order_name': testorder.name, 'testtype_name': testdict[testorder.test_type],
            'mesline_name': testorder.mesline_id.name, 'workstation_name': testorder.workstation_id.name,
            'equipment_code': testorder.equipment_id.code, 'employee_name': testorder.employee_id.name,
            'qualified': testorder.qualified, 'workorder_name': testorder.workorder_id.name,
            'wireorder_name': testorder.wireorder_id.name, 'product_code': testorder.wireorder_id.product_code,
            'wire_code': testorder.workorder_id.product_id.default_code,
            'paramlines': [{
                'pname': temparam.parameter_id.parameter_name,
                'pvalue': temparam.parameter_value, 'qualified': temparam.qualified
            } for temparam in testorder.order_lines]
        })
        return request.render('aas_mes.aas_wirecutting_producttest_orderdetail', values)

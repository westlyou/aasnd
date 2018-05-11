# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-3-4 19:12
"""

import logging
import werkzeug

from odoo import http
from odoo.http import request
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

class AASMESProducttestController(http.Controller):

    @http.route('/aasmes/producttest/loadworkstations', type='json', auth="user")
    def aasmes_producttest_loadworkstations(self, q=None, page=1, limit=30, meslineid=None):
        values = {'items': [], 'total_count': 0}
        workstationids = []
        if meslineid:
            mesline = request.env['aas.mes.line'].browse(meslineid)
            if mesline.workstation_lines and len(mesline.workstation_lines) > 0:
                workstationids = [wtnline.workstation_id.id for wtnline in mesline.workstation_lines]
        search_domain = []
        if workstationids and len(workstationids) > 0:
            search_domain.append(('id', 'in', workstationids))
        if q:
            search_domain.append(('name', 'ilike', q))
        workstationlist = request.env['aas.mes.workstation'].search(search_domain, offset=(page-1)*limit)
        if workstationlist and len(workstationlist) > 0:
            values['items'] = [{'id': workstation.id, 'text': workstation.name} for workstation in workstationlist]
        values['total_count'] = request.env['aas.mes.workstation'].search_count(search_domain)
        return values

    @http.route('/aasmes/producttest/scanemployee', type='json', auth="user")
    def aasmes_producttest_scanemployee(self, barcode):
        values = {'success': True, 'message': '', 'employee_id': '0', 'employee_name': ''}
        employee = request.env['aas.hr.employee'].search([('barcode', '=', barcode.upper())], limit=1)
        if not employee:
            values.update({'success': False, 'message': u'请仔细检查是否扫描的是有效员工！'})
            return values
        values.update({'employee_id': employee.id, 'employee_name': employee.name})
        return values

    @http.route('/aasmes/producttest/scanequipment', type='json', auth="user")
    def aasmes_producttest_scanequipment(self, barcode):
        values = {'success': True, 'message': '', 'equipment_id': '0', 'equipment_name': ''}
        equipment = request.env['aas.equipment.equipment'].search([('barcode', '=', barcode.upper())], limit=1)
        if not equipment:
            values.update({'success': False, 'message': u'请仔细检查是否扫描的是有效设置！'})
            return values
        values.update({'equipment_id': equipment.id, 'equipment_code': equipment.code})
        return values


    @http.route('/aasmes/producttest/dotest/<string:testtype>', type='http', auth="user")
    def aasmes_producttest_dotest(self, testtype):
        values = {
            'success': True, 'message': '', 'testtype': testtype,
            'workorder_id': '0', 'workorder_name': '', 'product_id': '0',
            'product_code': '', 'mesline_id': '0', 'mesline_name': ''
        }
        loginuser = request.env.user
        values['checker'] = loginuser.name
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', loginuser.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线，无法继续其他操作！'})
            return request.render('aas_mes.aas_producttest_dotest', values)
        mesline = lineuser.mesline_id
        if not mesline:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线，无法继续其他操作！'})
            return request.render('aas_mes.aas_producttest_dotest', values)
        workorder = mesline.workorder_id
        if not workorder:
            values.update({'success': False, 'message': u'当前产线还未指定即将生产的工单，无法继续其他操作！'})
            return request.render('aas_mes.aas_producttest_dotest', values)
        if testtype not in ['firstone', 'lastone', 'random']:
            values.update({'success': False, 'message': u'检测类型异常，无法继续其他操作！'})
            return request.render('aas_mes.aas_producttest_dotest', values)
        values.update({
            'workorder_id': workorder.id, 'workorder_name': workorder.name,
            'product_id': workorder.product_id.id, 'product_code': workorder.product_id.default_code,
            'mesline_id': mesline.id, 'mesline_name': mesline.name
        })
        return request.render('aas_mes.aas_producttest_dotest', values)


    @http.route('/aasmes/producttest/loadparameters', type='json', auth="user")
    def aasmes_producttest_loadparameters(self, testtype, workstationid, productid):
        values = {'success': True, 'message': '', 'parameters': []}
        testdomain = [('product_id', '=', productid), ('workstation_id', '=', workstationid)]
        producttest = request.env['aas.mes.producttest'].search(testdomain, limit=1)
        if not producttest:
            values.update({'success': False, 'message': u'检测异常，请确认是指设置了相关检测侧参数信息！'})
            return values
        tempvals = request.env['aas.mes.producttest'].action_loading_parameters(producttest, testtype)
        values.update(tempvals)
        return values


    @http.route('/aasmes/producttest/docommittest', type='json', auth="user")
    def aasmes_producttest_docommittest(self, testtype, workorderid, workstationid, employeeid, parameters, equipmentid=False):
        values = {'success': True, 'message': '', 'orderid': '0'}
        workorder = request.env['aas.mes.workorder'].browse(workorderid)
        if not parameters or len(parameters) <= 0:
            values.update({'success': False, 'message': u'工单异常，检测参数异常，未获取到检测参数信息！'})
            return values
        if not employeeid:
            values.update({'success': False, 'message': u'您还未设置操作员工，请先设置操作员工再提交操作！'})
            return values
        if not workstationid:
            values.update({'success': False, 'message': u'请仔细检查，您可能还未设置工位！'})
            return values
        productid, mesline = workorder.product_id.id, workorder.mesline_id
        # 获取员工在当前产线工位的班次信息
        tempvals = request.env['aas.mes.work.attendance.line'].get_schedule(mesline, workstationid, employeeid)
        tschedule = tempvals.get('schedule', False)
        # 获取质检清单
        testdomain = [('product_id', '=', productid), ('workstation_id', '=', workstationid)]
        producttest = request.env['aas.mes.producttest'].search(testdomain, limit=1)
        testorder = request.env['aas.mes.producttest.order'].create({
            'producttest_id': producttest.id, 'product_id': productid,
            'workstation_id': workstationid, 'mesline_id': mesline.id, 'equipment_id': equipmentid,
            'test_type': testtype, 'employee_id': employeeid, 'workorder_id': workorderid,
            'state': 'done', 'order_lines': [(0, 0, tparam) for tparam in parameters],
            'schedule_id': False if not tschedule else tschedule.id
        })
        testorder.write({'qualified': all([orderline.qualified for orderline in testorder.order_lines])})
        values['orderid'] = testorder.id
        # 如果NG则添加锁定记录
        testorder.action_lock_testequipment()
        return values

    @http.route('/aasmes/producttest/orderdetail/<int:orderid>', type='http', auth="user")
    def aasmes_producttest_orderdetail(self, orderid):
        values = {'success': True, 'message': '', 'checker': request.env.user.name}
        testdict = {'firstone': u'首件检测', 'lastone': u'末件检测', 'random': u'抽样检测'}
        testorder = request.env['aas.mes.producttest.order'].browse(orderid)
        values.update({
            'order_name': testorder.name, 'testtype_name': testdict[testorder.test_type],
            'mesline_name': testorder.mesline_id.name, 'workstation_name': testorder.workstation_id.name,
            'equipment_code': '' if not testorder.equipment_id else testorder.equipment_id.code,
            'employee_name': testorder.employee_id.name,
            'qualified': testorder.qualified, 'workorder_name': testorder.workorder_id.name,
            'product_code': testorder.product_id.default_code,
            'paramlines': [{
                'pname': temparam.parameter_id.parameter_name,
                'pvalue': temparam.parameter_value, 'qualified': temparam.qualified
            } for temparam in testorder.order_lines]
        })
        return request.render('aas_mes.aas_producttest_orderdetail', values)

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

REWORKSTATEDICT = {'commit': u'不良上报', 'repair': u'返工维修', 'ipqc': u'IPQC确认', 'done': u'完成'}


class AASMESGP12CheckingController(http.Controller):

    @http.route('/aasmes/gp12/checking', type='http', auth="user")
    def aasmes_gp12_checking(self):
        values = {
            'success': True, 'message': '', 'serialnumberlist': [],
            'checkerlist': [], 'scanner_id': '0', 'scanner_name': '', 'serialcount': '0'
        }
        loginuser = request.env.user
        values['checker'] = loginuser.name
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', loginuser.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return request.render('aas_mes.aas_gp12_checking', values)
        if lineuser.mesrole != 'gp12checker':
            values.update({'success': False, 'message': u'当前登录账号还未授权GP12'})
            return request.render('aas_mes.aas_gp12_checking', values)
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定GP12工位'})
            return request.render('aas_mes.aas_gp12_checking', values)
        values.update({'mesline_name': mesline.name, 'workstation_name': workstation.name})
        employeedomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        scannerdomain = employeedomain + [('action_type', '=', 'scan')]
        scanner = request.env['aas.mes.workstation.employee'].search(scannerdomain, limit=1)
        if scanner:
            values.update({'scanner_id': scanner.employee_id.id, 'scanner_name': scanner.employee_id.name})
        checkerdomain = employeedomain + [('action_type', '=', 'check')]
        checkerlist = request.env['aas.mes.workstation.employee'].search(checkerdomain)
        if checkerlist and len(checkerlist) > 0:
            values['checkerlist'] = [{
                'employee_id': tchecker.employee_id.id,
                'employee_name': tchecker.employee_id.name, 'employee_code': tchecker.employee_id.code
            } for tchecker in checkerlist]
        return request.render('aas_mes.aas_gp12_checking', values)


    @http.route('/aasmes/gp12/loadunpacklist', type='json', auth="user")
    def aasmes_gp12_loadunpacklist(self):
        values = request.env['aas.mes.operation'].action_loading_unpacking()
        return values


    @http.route('/aasmes/gp12/scanemployee', type='json', auth="user")
    def aasmes_gp12_scanemployee(self, barcode):
        values = {
            'success': True, 'message': '', 'action': 'working',
            'employee_id': '0', 'employee_name': '', 'employee_code': '', 'needrole': False
        }
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
        values.update({
            'employee_id': employee.id, 'employee_name': employee.name, 'employee_code': employee.code
        })
        values.update(request.env['aas.mes.work.attendance'].action_scanning(employee, mesline, workstation))
        tdomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id), ('action_type', '=', 'scan')]
        if request.env['aas.mes.workstation.employee'].search_count(tdomain) <= 0:
            values['needrole'] = True
        return values

    @http.route('/aasmes/gp12/changemployeerole', type='json', auth="user")
    def aasmes_gp12_changemployeerole(self, employeeid, action_type='check'):
        values = {'success': True, 'message': ''}
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', request.env.user.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return values
        if lineuser.mesrole != 'gp12checker':
            values.update({'success': False, 'message': u'当前登录账号还未授权GP12检测！'})
            return values
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定终检工位'})
            return values
        tdomain = [('employee_id', '=', employeeid)]
        tdomain += [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        wemployee = request.env['aas.mes.workstation.employee'].search(tdomain, limit=1)
        if wemployee:
            wemployee.write({'action_type': action_type})
        return values


    @http.route('/aasmes/gp12/scanserialnumber', type='json', auth="user")
    def aasmes_gp12_scan_serialnumber(self, barcode, productcode=None):
        values = {
            'success': True, 'message': '', 'result': 'OK',  'functiontestlist': [], 'reworklist': [], 'done': False
        }
        userdomain = [('lineuser_id', '=', request.env.user.id), ('mesrole', '=', 'gp12checker')]
        lineuser = request.env['aas.mes.lineusers'].search(userdomain, limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return values
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定GP12工位'})
            return values
        tempoperation = request.env['aas.mes.operation'].search([('serialnumber_name', '=', barcode)], limit=1)
        if not tempoperation:
            values.update({'result': 'NG', 'success': False, 'message': u'请检查您扫描的是否是一个有效的序列号'})
            return values
        serialnumber = tempoperation.serialnumber_id
        if tempoperation.gp12_check:
            values.update({'message': u'已扫描 请不要重复操作', 'done': True})
        values['serialnumber_id'] = serialnumber.id
        values['productcode'] = serialnumber.customer_product_code.replace('-', '')
        if productcode and productcode != values['productcode']:
            values.update({'success': False, 'message': u'序列号异常，请确认可能混入其他型号'})
            return values
        # 功能测试记录
        operatedomain = [('operation_id', '=', tempoperation.id), ('operate_type', '=', 'functiontest')]
        functiontestlist = request.env['aas.mes.operation.record'].search(operatedomain)
        if functiontestlist and len(functiontestlist) > 0:
            values['functiontestlist'] = [{
                'operate_result': record.operate_result,
                'operator_name': '' if not record.employee_id else record.employee_id.name,
                'operate_equipment': '' if not record.equipment_id else record.equipment_id.code,
                'operate_time': fields.Datetime.to_timezone_string(record.operate_time, 'Asia/Shanghai')
            } for record in functiontestlist]
        # 返工记录
        reworklist = request.env['aas.mes.rework'].search([('serialnumber_id', '=', serialnumber.id)])
        if reworklist and len(reworklist) > 0:
            values['reworklist'] = [{
                'serialnumber': serialnumber.name, 'badmode_date': rework.badmode_date,
                'product_code': rework.customerpn, 'workcenter_name': rework.workstation_id.name,
                'badmode_name': rework.badmode_id.name, 'commiter_name': rework.commiter_id.name,
                'state_name': REWORKSTATEDICT[rework.state],
                'repair_result': '' if not rework.repair_note else rework.repair_note,
                'repairer_name': '' if not rework.repairer_id else rework.repairer_id.name,
                'ipqc_name': '' if not rework.ipqcchecker_id else rework.ipqcchecker_id.name,
                'repair_time': '' if not rework.repair_time else fields.Datetime.to_timezone_string(rework.repair_time, 'Asia/Shanghai')
            } for rework in reworklist]
        serialnumber_name = serialnumber.name
        operation_time = fields.Datetime.to_china_string(fields.Datetime.now())
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
        if not tempoperation.function_test:
            values['operate_result'] = ','.join([serialnumber_name, 'NG', operation_time])
            values.update({'message': u'序列号异常，隔离板测试还没有操作！', 'result': 'NG'})
            return values
        if not tempoperation.final_quality_check:
            values['operate_result'] = ','.join([serialnumber_name, 'NG', operation_time])
            values.update({'message': u'序列号异常，最终检查还没有操作！！', 'result': 'NG'})
            return values
        if not tempoperation.gp12_check:
            tempoperation.action_gp12check(mesline, workstation)
        values['operate_result'] = ','.join([serialnumber_name, 'OK', operation_time])
        return values



    @http.route('/aasmes/gp12/rework', type='http', auth="user")
    def aasmes_gp12_rework(self):
        values = {'success': True, 'message': '', 'employeelist': []}
        loginuser = request.env.user
        values['checker'] = loginuser.name
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', loginuser.id)], limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return request.render('aas_mes.aas_gp12_rework', values)
        if lineuser.mesrole != 'gp12checker':
            values.update({'success': False, 'message': u'当前登录账号还未授权GP12'})
            return request.render('aas_mes.aas_gp12_rework', values)
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定GP12工位'})
            return request.render('aas_mes.aas_gp12_rework', values)
        values.update({
            'mesline_id':mesline.id, 'mesline_name': mesline.name,
            'workstation_id': workstation.id, 'workstation_name': workstation.name
        })
        return request.render('aas_mes.aas_gp12_rework', values)


    @http.route('/aasmes/gp12/rework/scanserialnumber', type='json', auth="user")
    def aasmes_gp12_rework_scan_serialnumber(self, barcode):
        values = {'success': True, 'message': '', 'reworklist': []}
        serialnumber = request.env['aas.mes.serialnumber'].search([('name', '=', barcode)])
        if not serialnumber:
            values.update({'success': False, 'message': u'扫描序列号异常，请仔细检查当前扫描的条码是否是序列号条码！'})
            return values
        rework = request.env['aas.mes.rework'].search([('serialnumber_id', '=', serialnumber.id)], order='id desc', limit=1)
        if rework and not rework.repairer_id:
            values.update({'success': False, 'message': u'不良已上报还未维修，请不要重复上报！'})
            return values
        values['product_code'] = serialnumber.customer_product_code
        # 返工记录
        reworklist = request.env['aas.mes.rework'].search([('serialnumber_id', '=', serialnumber.id)])
        if reworklist and len(reworklist) > 0:
            values['reworklist'] = [{
                'serialnumber': serialnumber.name, 'badmode_date': rework.badmode_date,
                'product_code': rework.customerpn, 'workcenter_name': rework.workstation_id.name,
                'badmode_name': rework.badmode_id.name, 'commiter_name': rework.commiter_id.name,
                'state_name': REWORKSTATEDICT[rework.state]
            } for rework in reworklist]
        values.update({'serialnumber_id': serialnumber.id, 'serialnumber_name': serialnumber.name})
        return values


    @http.route('/aasmes/gp12/rework/actioncommit', type='json', auth="user")
    def aasmes_gp12_rework_actioncommit(self, employee_id, badmode_id, serialnumberlist):
        values = {'success': True, 'message': ''}
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
        if serialnumberlist and len(serialnumberlist) > 0:
            for serialnumberid in serialnumberlist:
                request.env['aas.mes.rework'].action_commit(serialnumberid, workstation.id, badmode_id, employee_id)
        return values

    @http.route('/aasmes/gp12/dolabel', type='json', auth="user")
    def aasmes_gp12_dolabel(self, serialnumberids, printer_id):
        values = {'success': True, 'message': ''}
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
        if not mesline.location_production_id:
            values.update({'success': False, 'message': u'当前产线还未设置成品库位！'})
            return values
        serialnumberlist = request.env['aas.mes.serialnumber'].browse(serialnumberids)
        if not serialnumberlist or len(serialnumberlist) <= 0:
            values.update({'success': False, 'message': u'序列号获取异常，请仔细检查！'})
            return values
        tserialnumber = serialnumberlist[0]
        lot_name = mesline.workdate.replace('-', '')
        product_lot = request.env['stock.production.lot'].action_checkout_lot(tserialnumber.product_id.id, lot_name)
        product_id, product_qty = tserialnumber.product_id.id, len(serialnumberlist)
        location_id, customer_code = mesline.location_production_id.id, tserialnumber.customer_product_code
        tlabel = request.env['aas.mes.production.label'].action_gp12_dolabel(product_id, product_lot.id,
                                                                      product_qty, location_id, customer_code)
        serialnumberlist.action_label(tlabel.id)
        srclocation = request.env.ref('stock.location_production')
        tlabel.action_stock(srclocation.id)
        values['label_name'] = tlabel.name
        printvals = request.env['aas.product.label'].action_print_label(printer_id, [tlabel.id])
        values.update(printvals)
        return values


    @http.route('/aasmes/gp12/delivery', type='http', auth="user")
    def aasmes_gp12_delivery(self):
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
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定GP12工位'})
            return request.render('aas_mes.aas_gp12_checking', values)
        values.update({'mesline_name': mesline.name, 'workstation_name': workstation.name})
        return request.render('aas_mes.aas_gp12_delivery', values)


    @http.route('/aasmes/gp12/delivery/scanlabel', type='json', auth="user")
    def aasmes_gp12_delivery_scanlabel(self, barcode):
        values = {'success': True, 'message': ''}
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
        if not mesline.location_production_id or (not mesline.location_material_list or len(mesline.location_material_list) <= 0):
            values.update({'success': False, 'message': u'当前产线还未设置成品和原料库位！'})
            return values
        label = request.env['aas.product.label'].search([('barcode', '=', barcode)], limit=1)
        if not label:
            values.update({'success': False, 'message': u'未搜索到相应标签，请检查是否扫描了无效标签！'})
            return values
        locationids = [mlocation.location_id.id for mlocation in mesline.location_material_list]
        locationids.append(mesline.location_production_id.id)
        locationlist = request.env['stock.location'].search([('id', 'child_of', locationids)])
        if label.location_id.id not in locationlist.ids:
            values.update({'success': False, 'message': u'当前标签不在GP12的线边库中，不可以扫描其他库位的标签！'})
            return values
        labelvals = {
            'id': label.id, 'name': label.name, 'product_lot': label.product_lot.name, 'product_qty': label.product_qty,
            'customerpn': label.product_id.customer_product_code, 'internalpn': label.product_id.default_code
        }
        values['label'] = labelvals
        return values


    @http.route('/aasmes/gp12/delivery/actiondone', type='json', auth="user")
    def aasmes_gp12_delivery_actiondone(self, labelids):
        values = {'success': True, 'message': ''}
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
        if not mesline.location_production_id or (not mesline.location_material_list or len(mesline.location_material_list) <= 0):
            values.update({'success': False, 'message': u'当前产线还未设置成品和原料库位！'})
            return values
        labellist = request.env['aas.product.label'].browse(labelids)
        receiptdict, labellines = {}, []
        for label in labellist:
            labellines.append((0, 0, {
                'label_id': label.id, 'product_id': label.product_id.id, 'product_uom': label.product_uom.id,
                'product_lot': label.product_lot.id, 'label_location': label.location_id.id, 'product_qty': label.product_qty
            }))
            pkey = 'P'+str(label.product_id.id)
            if pkey not in receiptdict:
                receiptdict[pkey] = {'product_id': label.product_id.id, 'product_qty': label.product_qty, 'label_related': True}
            else:
                receiptdict[pkey]['product_qty'] += label.product_qty
        try:
            receipt = request.env['aas.stock.receipt'].create({
                'receipt_type': 'manufacture', 'label_lines': labellines,
                'receipt_lines': [(0, 0, linevals) for linevals in receiptdict.values()]
            })
            for receiptline in receipt.receipt_lines:
                receiptlabels = request.env['aas.stock.receipt.label'].search([('receipt_id', '=', receipt.id), ('product_id', '=', receiptline.product_id.id)])
                receiptlabels.write({'line_id': receiptline.id})
            receipt.action_confirm()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        except ValidationError, ve:
            values.update({'success': False, 'message': ve.name})
            return values
        return values



    @http.route('/aasmes/gp12/loadreworksandrecords', type='json', auth="user")
    def aasmes_gp12_loadreworksandrecords(self, serialnumberid):
        values = {'success': True, 'message': '', 'functiontestlist': [], 'reworklist': []}
        serialnumber = request.env['aas.mes.serialnumber'].browse(serialnumberid)
        tempoperation = serialnumber.operation_id
        if not tempoperation:
            tempoperation = request.env['aas.mes.operation'].search([('serialnumber_id', '=', serialnumber.id)], limit=1)
        values['serialnumber'] = serialnumber.name
        # 功能测试记录
        operatedomain = [('operation_id', '=', tempoperation.id), ('operate_type', '=', 'functiontest')]
        functiontestlist = request.env['aas.mes.operation.record'].search(operatedomain)
        if functiontestlist and len(functiontestlist) > 0:
            values['functiontestlist'] = [{
                'operate_result': record.operate_result,
                'operator_name': '' if not record.employee_id else record.employee_id.name,
                'operate_equipment': '' if not record.equipment_id else record.equipment_id.code,
                'operate_time': fields.Datetime.to_timezone_string(record.operate_time, 'Asia/Shanghai')
            } for record in functiontestlist]
        # 返工记录
        reworklist = request.env['aas.mes.rework'].search([('serialnumber_id', '=', serialnumber.id)])
        if reworklist and len(reworklist) > 0:
            values['reworklist'] = [{
                'serialnumber': serialnumber.name, 'badmode_date': rework.badmode_date,
                'product_code': rework.customerpn, 'workcenter_name': rework.workstation_id.name,
                'badmode_name': rework.badmode_id.name, 'commiter_name': rework.commiter_id.name,
                'state_name': REWORKSTATEDICT[rework.state],
                'repair_result': '' if not rework.repair_note else rework.repair_note,
                'repairer_name': '' if not rework.repairer_id else rework.repairer_id.name,
                'ipqc_name': '' if not rework.ipqcchecker_id else rework.ipqcchecker_id.name,
                'repair_time': '' if not rework.repair_time else fields.Datetime.to_china_string(rework.repair_time)
            } for rework in reworklist]
        return values







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
    def aasmes_gp12_loadunpacklist(self, checkdate=False):
        values = request.env['aas.mes.operation'].action_loading_unpacking(checkdate=checkdate)
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
        employee = request.env['aas.hr.employee'].search([('barcode', '=', barcode.upper())], limit=1)
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
    def aasmes_gp12_scan_serialnumber(self, barcode, productid=None):
        values = {
            'success': True, 'message': '', 'result': 'OK',  'functiontestlist': [],
            'reworklist': [], 'done': False, 'productid': 0, 'productcode': ''
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
        employeedomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        scandomain = employeedomain + [('action_type', '=', 'scan')]
        if request.env['aas.mes.workstation.employee'].search_count(scandomain) <= 0:
            values.update({'success': False, 'message': u'当前岗位没有扫描员工，请先让扫描员工上岗再继续操作！'})
            return values
        checkdomain = employeedomain + [('action_type', '=', 'check')]
        if request.env['aas.mes.workstation.employee'].search_count(checkdomain) <= 0:
            values.update({'success': False, 'message': u'当前岗位没有检测员工，请先让检测员工上岗再继续操作！'})
            return values
        tempoperation = request.env['aas.mes.operation'].search([('serialnumber_name', '=', barcode)], limit=1)
        if not tempoperation:
            values.update({'result': 'NG', 'success': False, 'message': u'请检查您扫描的是否是一个有效的序列号'})
            return values
        serialnumber = tempoperation.serialnumber_id
        values.update({
            'serialnumber_id': serialnumber.id,
            'productid': serialnumber.product_id.id,
            'productcode': serialnumber.customer_product_code.replace('-', '')
        })
        if productid and productid != values['productid']:
            values.update({'success': False, 'message': u'序列号异常，请确认可能混入其他型号'})
            return values
        serialnumber_name = serialnumber.name
        operation_time = fields.Datetime.to_china_string(fields.Datetime.now())
        if tempoperation.gp12_check:
            values.update({'message': u'已扫描 请不要重复操作', 'done': True})
        # 返工件
        if serialnumber.reworked and serialnumber.reworksource == 'produce':
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
        values = {
            'success': True, 'message': '', 'reworklist': [],
            'scanner_id': '0', 'scanner_name': '', 'workstation_id': '0', 'workstation_name': ''
        }
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
        employeedomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        scannerdomain = employeedomain + [('action_type', '=', 'scan')]
        scanner = request.env['aas.mes.workstation.employee'].search(scannerdomain, limit=1)
        if not scanner:
            values.update({'success': False, 'message': u'当前工位没有扫描员工在岗！'})
            return request.render('aas_mes.aas_gp12_rework', values)
        values.update({'scanner_id': scanner.employee_id.id, 'scanner_name': scanner.employee_id.name})
        badmode_date = fields.Datetime.to_china_today()
        reworkdomain = [('workstation_id', '=', workstation.id), ('badmode_date', '=', badmode_date)]
        reworklist = request.env['aas.mes.rework'].search(reworkdomain)
        if reworklist and len(reworklist) > 0:
            tindex = 1
            for rework in reworklist:
                values['reworklist'].append({
                    'lineno': tindex, 'state_name': REWORKSTATEDICT[rework.state],
                    'serialnumber': rework.serialnumber_id.name, 'badmode_date': rework.badmode_date,
                    'product_code': rework.customerpn, 'workcenter_name': rework.workstation_id.name,
                    'badmode_name': rework.badmode_id.name, 'commiter_name': rework.commiter_id.name
                })
                tindex += 1
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
        values.update({
            'product_code': serialnumber.customer_product_code,
            'serialnumber_id': serialnumber.id, 'serialnumber_name': serialnumber.name
        })
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
                request.env['aas.mes.rework'].action_commit(serialnumberid, workstation.id, badmode_id,
                                                            employee_id, mesline_id=mesline.id)
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
        labelvals = serialnumberlist.action_gp12packing(mesline)
        labelid, labelname = labelvals['label_id'], labelvals['label_name']
        values['label_name'] = labelname
        printvals = request.env['aas.product.label'].action_print_label(printer_id, [labelid])
        values.update(printvals)
        return values

    @http.route('/aasmes/gp12/printlabel', type='json', auth="user")
    def aasmes_gp12_printlabel(self, labelid, printer_id):
        values = {'success': True, 'message': ''}
        printvals = request.env['aas.product.label'].action_print_label(printer_id, [labelid])
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
        label = request.env['aas.product.label'].search([('barcode', '=', barcode.upper())], limit=1)
        if not label:
            values.update({'success': False, 'message': u'未搜索到相应标签，请检查是否扫描了无效标签！'})
            return values
        if not label.isproduction:
            values.update({'success': False, 'message': u'GP12不可以扫描仓库标签！'})
            return values
        # 产线标签且不在GP12的标签自动调拨到GP12
        locationids = [mesline.location_production_id.id]
        if mesline.location_material_list and len(mesline.location_material_list) > 0:
            locationids += [mlocation.location_id.id for mlocation in mesline.location_material_list]
        finalocationids = request.env['stock.location'].search([('id', 'child_of', locationids)]).ids
        if label.location_id.id not in finalocationids:
            request.env['stock.move'].create({
                'name': label.name,
                'product_id': label.product_id.id, 'product_uom': label.product_uom.id,
                'create_date': fields.Datetime.now(), 'restrict_lot_id': label.product_lot.id,
                'product_uom_qty': label.product_qty, 'company_id': request.env.user.company_id.id,
                'location_id': label.location_id.id, 'location_dest_id': mesline.location_production_id.id
            }).action_done()
            label.write({'location_id': mesline.location_production_id.id})
        values['label'] = {
            'id': label.id, 'name': label.name, 'product_lot': label.product_lot.name, 'product_qty': label.product_qty,
            'customerpn': label.product_id.customer_product_code, 'internalpn': label.product_id.default_code
        }
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
            labellist.sudo().write({'locked': True, 'locked_order': receipt.name})
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        except ValidationError, ve:
            values.update({'success': False, 'message': ve.name})
            return values
        return values



    @http.route('/aasmes/gp12/loadreworksandrecords', type='json', auth="user")
    def aasmes_gp12_loadreworksandrecords(self, serialnumberid):
        values = {'success': True, 'message': '', 'operationlist': [], 'reworklist': []}
        serialnumber = request.env['aas.mes.serialnumber'].browse(serialnumberid)
        tempoperation = serialnumber.operation_id
        if not tempoperation:
            tempoperation = request.env['aas.mes.operation'].search([('serialnumber_id', '=', serialnumber.id)], limit=1)
        values['serialnumber'] = serialnumber.name
        # 操作记录
        operationlist = request.env['aas.mes.operation.record'].search([('operation_id', '=', tempoperation.id)])
        if operationlist and len(operationlist) > 0:
            values['operationlist'] = [{
                'operate_result': record.operate_result,
                'operation_name': '' if not record.operate_name else record.operate_name,
                'operator_name': '' if not record.employee_id else record.employee_id.name,
                'scanner_name': '' if not record.scanning_employee else record.scanning_employee,
                'checker_name': '' if not record.checking_employee else record.checking_employee,
                'operate_equipment': '' if not record.equipment_id else record.equipment_id.code,
                'operate_time': fields.Datetime.to_china_string(record.operate_time)
            } for record in operationlist]
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




    @http.route('/aasmes/gp12/checking/query', type='http', auth="user")
    def aasmes_gp12_checking_query(self):
        values = {'success': True, 'message': '', 'labelist': []}
        loginuser = request.env.user
        values['checker'] = loginuser.name
        gpdomain = [('lineuser_id', '=', loginuser.id), ('mesrole', '=', 'gp12checker')]
        lineuser = request.env['aas.mes.lineusers'].search(gpdomain, limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return request.render('aas_mes.aas_gp12_checking_query', values)
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定GP12工位'})
            return request.render('aas_mes.aas_gp12_checking_query', values)
        return request.render('aas_mes.aas_gp12_checking_query', values)


    @http.route('/aasmes/gp12/checking/query/labelist', type='json', auth="user")
    def aasmes_gp12_checking_query_labelist(self, checkdate):
        values = {'success': True, 'message': '', 'labelist': []}
        templabelist = request.env['aas.mes.production.label'].search([('action_date', '=', checkdate)])
        if not templabelist or len(templabelist) <= 0:
            return values
        values['labelist'] = [{
            'label_id': tlabel.label_id.id, 'label_name': tlabel.label_id.name, 'label_qty': tlabel.product_qty
        } for tlabel in templabelist]
        return values


    @http.route('/aasmes/gp12/checking/query/serialist', type='json', auth="user")
    def aasmes_gp12_checking_query_serialist(self, labelid):
        values = {'success': True, 'message': '', 'serialist': []}
        tempserialnumberlist = request.env['aas.mes.serialnumber'].search([('label_id', '=', labelid)])
        if not tempserialnumberlist or len(tempserialnumberlist) <= 0:
            return values
        values['serialist'] = [{
            'serialnumber_id': tserialnumber.id, 'serialnumber_name': tserialnumber.name
        } for tserialnumber in tempserialnumberlist]
        return values




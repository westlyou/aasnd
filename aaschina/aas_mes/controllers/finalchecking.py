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
        values = {'success': True, 'message': '', 'equipmentlist': '', 'workorder_id': '0'}
        loginuser = request.env.user
        values.update({
            'checker': loginuser.name, 'equipment_id': '0', 'equipment_code': '',
            'workorder_name': '', 'customer_code': '', 'product_code': '', 'scan_employee': '', 'check_employee': ''
        })
        userdomain = [('lineuser_id', '=', loginuser.id), ('mesrole', '=', 'fqcchecker')]
        lineuser = request.env['aas.mes.lineusers'].search(userdomain, limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
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
        temployees = request.env['aas.mes.workstation.employee'].search(wkdomain)
        if temployees and len(temployees) > 0:
            scanemployees, checkemployees = [], []
            for temployee in temployees:
                if temployee.action_type == 'scan':
                    scanemployees.append(temployee.employee_id.name)
                elif temployee.action_type == 'check':
                    checkemployees.append(temployee.employee_id.name)
            values['scan_employee'] = ','.join(scanemployees)
            values['check_employee'] = ','.join(checkemployees)
        tequipments = request.env['aas.mes.workstation.equipment'].search(wkdomain)
        if tequipments and len(tequipments) > 0:
            values['equipmentlist'] = ','.join([tequipment.equipment_id.code for tequipment in tequipments])
        return request.render('aas_mes.aas_finalchecking', values)


    @http.route('/aasmes/finalchecking/serialcount', type='json', auth="user")
    def aasmes_finalchecking_serialcount(self):
        values = {'success': True, 'message': '', 'serialcount': '0'}
        loginuser = request.env.user
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', loginuser.id)], limit=1)
        if not lineuser:
            return values
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        if not mesline or not workstation:
            return values
        workorder = mesline.workorder_id
        if not workorder:
            return values
        productid = workorder.product_id.id
        scheduleid = False if not mesline.schedule_id else mesline.schedule_id.id
        outputdate = fields.Datetime.to_china_today() if not mesline.workdate else mesline.workdate
        return request.env['aas.production.product'].loading_serialcount(productid, mesline.id, workstation.id,
                                                                         outputdate, scheduleid=scheduleid)



    @http.route('/aasmes/finalchecking/scanemployee', type='json', auth="user")
    def aasmes_finalchecking_scanemployee(self, barcode):
        values = {
            'success': True, 'message': '', 'action': 'working', 'needrole': False,
            'employee_id': '0', 'employee_name': '', 'employee_code': ''
        }
        employee = request.env['aas.hr.employee'].search([('barcode', '=', barcode.upper())], limit=1)
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
        values.update(request.env['aas.mes.work.attendance'].action_scanning(employee, mesline, workstation))
        tdomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id), ('action_type', '=', 'scan')]
        if request.env['aas.mes.workstation.employee'].search_count(tdomain) <= 0:
            values['needrole'] = True
        return values

    @http.route('/aasmes/finalchecking/changemployeerole', type='json', auth="user")
    def aasmes_finalchecking_changemployeerole(self, employeeid, action_type='check'):
        values = {'success': True, 'message': ''}
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
        tdomain = [('employee_id', '=', employeeid)]
        tdomain += [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        wemployee = request.env['aas.mes.workstation.employee'].search(tdomain, limit=1)
        if wemployee:
            wemployee.write({'action_type': action_type})
        return values


    def action_checking_finalchecker(self, meslineid, workstationid):
        values = {'success': True, 'message': ''}
        tempemployeedomain = [('mesline_id', '=', meslineid), ('workstation_id', '=', workstationid)]
        tempemloyeelist = request.env['aas.mes.workstation.employee'].search(tempemployeedomain)
        if not tempemloyeelist or len(tempemloyeelist) <= 0:
            values.update({'success': False, 'message': u'当前岗位可能没有员工在岗，请先让员工上岗再继续操作！'})
            return values
        scaner, checker = False, False
        for temployee in tempemloyeelist:
            if temployee.action_type == 'scan':
                scaner = True
            if checker:
                continue
            if temployee.action_type == 'check':
                checker = True
        if not scaner:
            values.update({'success': False, 'message': u'当前岗位没有扫描员工，请先让扫描员工上岗再继续操作！'})
            return values
        if not checker:
            values.update({'success': False, 'message': u'当前岗位没有检测员工，请先让检测员工上岗再继续操作！'})
            return values
        return values


    def loading_serial_record_rework_and_count(self, mesline, soperation, workstation):
        productid = soperation.product_id.id
        meslineid, workstationid = mesline.id, workstation.id
        scheduleid = False if not mesline.schedule_id else mesline.schedule_id.id
        outputdate = fields.Datetime.to_china_today() if not mesline.workdate else mesline.workdate
        orvalues = request.env['aas.mes.operation'].action_loading_operation_rework_list(soperation.id)
        scvalues = request.env['aas.production.product'].loading_serialcount(productid, meslineid, workstationid,
                                                                             outputdate, scheduleid=scheduleid)
        return {
            'serialcount': scvalues['serialcount'],
            'recordlist': orvalues['recordlist'], 'reworklist': orvalues['reworklist']
        }


    @http.route('/aasmes/finalchecking/scanserialnumber', type='json', auth="user")
    def aasmes_finalchecking_scanserialnumber(self, barcode):
        logger.info(u'扫描序列号%s开始时间：%s'% (barcode, fields.Datetime.now()))
        values = {
            'success': True, 'message': '', 'serialnumber': barcode, 'done': False,
            'recordlist': [], 'reworklist': [], 'rework': False, 'serialcount': 0,
            'operationid': '0', 'internal_code': '', 'customer_code': '', 'badmode_name': '', 'rescan': False
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
        serialnumber = request.env['aas.mes.serialnumber'].search([('name', '=', barcode)], limit=1)
        if not serialnumber:
            values.update({'success': False, 'message': u'请仔细检查是否是有效条码'})
            return values
        tempoperation, isreworked = serialnumber.operation_id, serialnumber.reworked
        values.update({
            'rework': isreworked, 'operationid': tempoperation.id,
            'internal_code': serialnumber.internal_product_code, 'customer_code': serialnumber.customer_product_code
        })
        workorder = mesline.workorder_id if not serialnumber.workorder_id else serialnumber.workorder_id
        if not isreworked and workorder and workorder.state == 'done':
            values.update({'success': False, 'message': u'当前工单已完工；继续生产请开新工单'})
            return values
        checkervals = self.action_checking_finalchecker(mesline.id, workstation.id)
        if not checkervals.get('success', False):
            return checkervals
        if not tempoperation.function_test:
            values.update({'success': False, 'message': u'功能测试未完成或未通过'})
            return values
        if tempoperation.final_quality_check:
            values['rescan'] = True
            values.update({'message': u'已扫描，请不要重复操作'})
            return values
        if isreworked:
            values['badmode_name'] = '' if not serialnumber.badmode_name else serialnumber.badmode_name
            values['message'] = u'%s返工，请仔细检查确认'% values['badmode_name']
            # 加载操作记录返工记录以及产出数量
            values.update(self.loading_serial_record_rework_and_count(mesline, tempoperation, workstation))
            return values
        if workorder:
            if serialnumber.product_id.id != workorder.product_id.id:
                values.update({'success': False, 'message': u'扫描序列号异常，此序列号产品与当前产线上生产的产品不相符！'})
                return values
            if not serialnumber.stocked:
                tvalues = request.env['aas.mes.workorder'].action_flowingline_output(workorder, workstation, serialnumber)
                if not tvalues.get('success', False):
                    values.update(tvalues)
                    return values
        tempoperation.action_finalcheck(mesline, workstation)
        # 加载操作记录返工记录以及产出数量
        values.update(self.loading_serial_record_rework_and_count(mesline, tempoperation, workstation))
        serialnumber.write({'stocked': True})
        logger.info(u'扫描序列号%s结束时间：%s'% (barcode, fields.Datetime.now()))
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
        tserialnumber = tempoperation.serialnumber_id
        workorder = mesline.workorder_id if not tserialnumber.workorder_id else tserialnumber.workorder_id
        if workorder and not tserialnumber.stocked:
            if tserialnumber.product_id.id != workorder.product_id.id:
                values.update({'success': False, 'message': u'扫描异常，当前产品型号与产线正在生产的型号不符！'})
                return values
            tvalues = request.env['aas.mes.workorder'].action_flowingline_output(workorder, workstation, tserialnumber)
            if not tvalues.get('success', False):
                values.update(tvalues)
                return values
        if not tempoperation.final_quality_check:
            tempoperation.action_finalcheck(mesline, workstation)
        if not tserialnumber.stocked:
            tserialnumber.write({'stocked': True})
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



    @http.route('/aasmes/finalchecking/query', type='http', auth="user")
    def aasmes_finalchecking_query(self):
        values = {'success': True, 'message': '', 'mesline_id': '0', 'workstation_id': '0'}
        loginuser = request.env.user
        values['checker'] = loginuser.name
        finaldomain = [('lineuser_id', '=', loginuser.id), ('mesrole', '=', 'fqcchecker')]
        lineuser = request.env['aas.mes.lineusers'].search(finaldomain, limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'当前登录账号还未绑定产线和工位，无法继续其他操作！'})
            return request.render('aas_mes.aas_finalchecking_query', values)
        mesline, workstation = lineuser.mesline_id, lineuser.workstation_id
        values.update({'mesline_name': mesline.name, 'mesline_id': mesline.id})
        if not workstation:
            values.update({'success': False, 'message': u'当前登录账号还未绑定终检工位！'})
            return request.render('aas_mes.aas_finalchecking_query', values)
        values['workstation_id'] = workstation.id
        return request.render('aas_mes.aas_finalchecking_query', values)



    @http.route('/aasmes/finalchecking/query/loadrecords', type='json', auth="user")
    def aasmes_finalchecking_query_loadrecords(self, meslineid, starttime, finishtime, productid=False):
        values = {'success': True, 'message': '', 'records': []}
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
        workstationid = workstation.id
        timestart = fields.Datetime.to_utc_string(fields.Datetime.from_string(starttime), 'Asia/Shanghai')
        timefinish = fields.Datetime.to_utc_string(fields.Datetime.from_string(finishtime), 'Asia/Shanghai')
        if not productid:
            productid = False
        tvalues = request.env['aas.production.product'].action_build_outputlist(timestart, timefinish,
                                                                                meslineid=meslineid,
                                                                                workstationid=workstationid,
                                                                                productid=productid)
        values.update(tvalues)
        return values





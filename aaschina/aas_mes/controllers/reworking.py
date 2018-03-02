# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-11-21 10:59
"""

import logging
import werkzeug

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

REWORKSTATEDICT = {'commit': u'不良上报', 'repair': u'返工维修', 'ipqc': u'IPQC确认', 'done': u'完成'}

class AASMESReworkingController(http.Controller):

    @http.route('/aasmes/reworking', type='http', auth="user")
    def aasmes_reworking(self):
        values = {'success': True, 'message': '', 'checker': request.env.user.name}
        return request.render('aas_mes.aas_reworking', values)


    @http.route('/aasmes/reworking/scanemployee', type='json', auth="user")
    def aasmes_reworking_scanemployee(self, barcode):
        values = {'success': True, 'message': '', 'employee_id': '0', 'employee_name': ''}
        employee = request.env['aas.hr.employee'].search([('barcode', '=', barcode)], limit=1)
        if not employee:
            values.update({'success': False, 'message': u'员工卡扫描异常，请检查系统中是否存在该员工！'})
            return values
        values.update({'employee_id': employee.id, 'employee_name': employee.name})
        return values


    @http.route('/aasmes/reworking/scanserialnumber', type='json', auth="user")
    def aasmes_reworking_scanserialnumber(self, barcode):
        values = {'success': True, 'message': '', 'reworklist': []}
        serialnumber = request.env['aas.mes.serialnumber'].search([('name', '=', barcode)])
        if not serialnumber:
            values.update({'success': False, 'message': u'扫描序列号异常，请仔细检查当前扫描的条码是否是序列号条码！'})
            return values
        rework = request.env['aas.mes.rework'].search([('serialnumber_id', '=', serialnumber.id), ('repairer_id', '=', False)], limit=1)
        if rework:
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


    @http.route('/aasmes/reworking/actioncommit', type='json', auth="user")
    def aasmes_reworking_actioncommit(self, employeeid, workstationid, badmodeid, serialnumberlist):
        values = {'success': True, 'message': ''}
        if serialnumberlist and len(serialnumberlist) > 0:
            for serialnumberid in serialnumberlist:
                request.env['aas.mes.rework'].action_commit(serialnumberid, workstationid, badmodeid, employeeid)
        return values




    @http.route('/aasmes/repairing', type='http', auth="user")
    def aasmes_repairing(self):
        values = {'success': True, 'message': '', 'checker': request.env.user.name}
        return request.render('aas_mes.aas_repairing', values)


    @http.route('/aasmes/repairing/scanemployee', type='json', auth="user")
    def aasmes_repairing_scanemployee(self, barcode):
        values = {'success': True, 'message': '', 'employee_id': '0', 'employee_name': ''}
        employee = request.env['aas.hr.employee'].search([('barcode', '=', barcode)], limit=1)
        if not employee:
            values.update({'success': False, 'message': u'员工卡扫描异常，请检查系统中是否存在该员工！'})
            return values
        values.update({'employee_id': employee.id, 'employee_name': employee.name})
        return values

    @http.route('/aasmes/repairing/scanserialnumber', type='json', auth="user")
    def aasmes_repairing_scanserialnumber(self, barcode):
        values = {'success': True, 'message': '', 'reworklist': []}
        serialnumber = request.env['aas.mes.serialnumber'].search([('name', '=', barcode)])
        if not serialnumber:
            values.update({'success': False, 'message': u'扫描序列号异常，请仔细检查当前扫描的条码是否是序列号条码！'})
            return values
        rework = request.env['aas.mes.rework'].search([('serialnumber_id', '=', serialnumber.id)], order='id desc', limit=1)
        if not rework:
            values.update({'success': False, 'message': u'%s还未上报过不良，暂时无需维修！'% barcode})
            return values
        if rework.state != 'repair':
            values.update({'success': False, 'message': u'%s已经维修，请不要重复操作！'% barcode})
            return values
        # 返工记录
        reworklist = request.env['aas.mes.rework'].search([('serialnumber_id', '=', serialnumber.id)], order='id desc')
        if reworklist and len(reworklist) > 0:
            values['reworklist'] = [{
                'serialnumber': serialnumber.name, 'badmode_date': rework.badmode_date,
                'product_code': rework.customerpn, 'workcenter_name': rework.workstation_id.name,
                'badmode_name': rework.badmode_id.name, 'commiter_name': rework.commiter_id.name,
                'state_name': REWORKSTATEDICT[rework.state]
            } for rework in reworklist]
        values.update({
            'serialnumber_id': serialnumber.id, 'serialnumber_name': serialnumber.name,
            'customerpn': serialnumber.customer_product_code,
            'internalpn': serialnumber.internal_product_code
        })
        return values


    @http.route('/aasmes/repairing/actiondone', type='json', auth="user")
    def aasmes_repairing_actiondone(self, repairerid, serialnumberid, repairesult):
        values = {'success': True, 'message': ''}
        rework = request.env['aas.mes.rework'].search([('serialnumber_id', '=', serialnumberid)], order='id desc', limit=1)
        if not rework:
            values.update({'success': False, 'message': u'%s还未上报过不良，暂时无需维修！'% rework.serialnumber_id.name})
            return values
        if rework.repairer_id and rework.state != 'repair':
            values.update({'success': False, 'message': u'%s已经维修，请不要重复操作！'% rework.serialnumber_id.name})
            return values
        rework.action_repair(repairerid, repairesult)
        return values


    @http.route('/aasmes/ipqcchecking', type='http', auth="user")
    def aasmes_ipqcchecking(self):
        values = {'success': True, 'message': '', 'checker': request.env.user.name, 'todolist': [], 'donelist': []}
        todolist = request.env['aas.mes.rework'].search([('state', '=', 'ipqc')])
        if todolist and len(todolist) > 0:
            tsequence = 1
            for rework in todolist:
                values['todolist'].append({
                    'lineno': tsequence, 'state_name': REWORKSTATEDICT[rework.state],
                    'serialnumber': rework.serialnumber_id.name, 'badmode_date': rework.badmode_date,
                    'product_code': rework.customerpn, 'workcenter_name': rework.workstation_id.name,
                    'badmode_name': rework.badmode_id.name, 'commiter_name': rework.commiter_id.name
                })
                tsequence += 1
        chinatoday = fields.Datetime.to_china_today()
        donelist = request.env['aas.mes.rework'].search([('state', '=', 'done'), ('badmode_date', '=', chinatoday)])
        if donelist and len(donelist) > 0:
            tsequence = 1
            for rework in donelist:
                values['donelist'].append({
                    'lineno': tsequence, 'state_name': REWORKSTATEDICT[rework.state],
                    'serialnumber': rework.serialnumber_id.name, 'badmode_date': rework.badmode_date,
                    'product_code': rework.customerpn, 'workcenter_name': rework.workstation_id.name,
                    'badmode_name': rework.badmode_id.name, 'commiter_name': rework.commiter_id.name
                })
                tsequence += 1
        return request.render('aas_mes.aas_ipqcchecking', values)

    @http.route('/aasmes/ipqcchecking/scanemployee', type='json', auth="user")
    def aasmes_ipqcchecking_scanemployee(self, barcode):
        values = {'success': True, 'message': '', 'employee_id': '0', 'employee_name': ''}
        employee = request.env['aas.hr.employee'].search([('barcode', '=', barcode)], limit=1)
        if not employee:
            values.update({'success': False, 'message': u'员工卡扫描异常，请检查系统中是否存在该员工！'})
            return values
        values.update({'employee_id': employee.id, 'employee_name': employee.name})
        return values

    @http.route('/aasmes/ipqcchecking/scanserialnumber', type='json', auth="user")
    def aasmes_ipqcchecking_scanserialnumber(self, barcode):
        values = {'success': True, 'message': ''}
        serialnumber = request.env['aas.mes.serialnumber'].search([('name', '=', barcode)])
        if not serialnumber:
            values.update({'success': False, 'message': u'扫描序列号异常，请仔细检查当前扫描的条码是否是序列号条码！'})
            return values
        rework = request.env['aas.mes.rework'].search([('serialnumber_id', '=', serialnumber.id)], order='id desc', limit=1)
        if not rework:
            values.update({'success': False, 'message': u'%s还未上报过不良，暂时无需维修！'% barcode})
            return values
        if rework.state != 'ipqc':
            values.update({'success': False, 'message': u'%s可能还未维修或已经IPQC确认完成，暂时不需要IPQC确认！'% barcode})
            return values
        values.update({
            'serialnumber_id': serialnumber.id, 'serialnumber_name': serialnumber.name,
            'customerpn': serialnumber.customer_product_code,
            'internalpn': serialnumber.internal_product_code
        })
        return values


    @http.route('/aasmes/ipqcchecking/actiondone', type='json', auth="user")
    def aasmes_ipqcchecking_actiondone(self, ipqccheckerid, serialnumberid, checkresult):
        values = {'success': True, 'message': ''}
        rework = request.env['aas.mes.rework'].search([('serialnumber_id', '=', serialnumberid)], order='id desc', limit=1)
        if not rework:
            values.update({'success': False, 'message': u'%s还未上报过不良，暂时无需维修！'% rework.serialnumber_id.name})
            return values
        if rework.state != 'ipqc':
            values.update({'success': False, 'message': u'%s可能还未维修或已经IPQC确认完成，暂时不需要IPQC确认'% rework.serialnumber_id.name})
            return values
        rework.action_ipqcchecking(ipqccheckerid, checkresult)
        return values

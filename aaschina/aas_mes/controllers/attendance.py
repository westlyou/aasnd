# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-8-26 15:49
"""

import logging
import werkzeug

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied,UserError,ValidationError

logger = logging.getLogger(__name__)

class AASMESAttendanceController(http.Controller):

    @http.route('/aasmes/attendance/scanner', type='http', auth="user")
    def aasmes_attendance_scanner(self):
        login = request.env.user
        values = {'success': True, 'message': u'上岗需要先选择工位，再扫描员工卡；如果是离岗直接扫描员工卡即可！', 'workstations': []}
        values['checker'] = login.name
        checker = request.env['aas.mes.attendance.checker'].search([('checker_id', '=', login.id)], limit=1)
        mesline = checker.mesline_id
        values['mesline_name'] = mesline.name
        workstations = request.env['aas.mes.workstation'].search([('mesline_id', '=', mesline.id)])
        if workstations and len(workstations) > 0:
            stationlist = []
            for station in workstations:
                stationitem = {'station_id': station.id, 'station_name': station.name, 'station_type': station.station_type, 'employees': []}
                employeelen = 0 if not station.employee_lines or len(station.employee_lines) <= 0 else len(station.employee_lines)
                if employeelen > 0:
                    stationitem['employees'] = [{'employee_name': employee.name, 'employee_code': employee.code} for employee in station.employee_lines]
                if employeelen < 2:
                    for index in range(0, 2-employeelen):
                        stationitem['employees'].append({'employee_name': '', 'employee_code': ''})
                stationlist.append(stationitem)
            values['workstations'] = stationlist
        else:
            values.update({'success': False, 'message': u'暂时没有工位可以选择，请联系管理员或相关负责人！'})
        return request.render('aas_mes.aas_attendance_scanner', values)


    @http.route('/aasmes/attendance/actionscan', type='json', auth="user")
    def aasmes_attendance_actionscan(self, barcode):
        values = {'success': True, 'message': ''}
        employee = request.env['aas.hr.employee'].search([('barcode', '=', barcode)], limit=1)
        if not employee:
            values.update({'success': False, 'message': u'无效条码，请确认扫描的是否是员工卡！'})
            return values
        mesattendance = request.env['aas.mes.work.attendance'].search([('employee_id', '=', employee.id), ('attend_done', '=', False)], limit=1)
        if mesattendance:
            mesattendance.action_done()
            values.update({'success': True, 'message': u'亲，您已离岗了哦！'})
            return values
        else:
            values.update({'employee_id': employee.id, 'employee_name': employee.name})
        return values


    @http.route('/aasmes/attendance/actionworking', type='json', auth="user")
    def aasmes_attendance_actionworking(self, stationid, employeeid):
        values = {'success': True, 'message': ''}
        if not stationid or not employeeid:
            values.update({'success': False, 'message': u'请确认已选择了工位并扫描了员工卡！'})
            return values
        request.env['aas.mes.work.attendance'].create({'employee_id': employeeid, 'workstation_id': stationid})
        values['message'] = u'亲，您已上岗！努力工作吧，加油！'
        return values


    @http.route('/aasmes/attendance/refreshstations', type='json', auth="user")
    def aasmes_attendance_refreshstations(self):
        values = {'success': True, 'message': '', 'workstations': []}
        checker = request.env['aas.mes.attendance.checker'].search([('checker_id', '=', request.env.user.id)], limit=1)
        if not checker:
            values.update({'success': False, 'message': u'请确认，当前用户可能已经不是生产考勤员了！'})
            return values
        workstations = request.env['aas.mes.workstation'].search([('mesline_id', '=', checker.mesline_id.id)])
        if workstations and len(workstations) > 0:
            stationlist = []
            for station in workstations:
                stationitem = {'station_id': station.id, 'station_name': station.name, 'station_type': station.station_type, 'employees': []}
                employeelen = 0 if not station.employee_lines or len(station.employee_lines) <= 0 else len(station.employee_lines)
                if employeelen > 0:
                    stationitem['employees'] = [{'employee_name': employee.name, 'employee_code': employee.code} for employee in station.employee_lines]
                if employeelen < 2:
                    for index in range(0, 2-employeelen):
                        stationitem['employees'].append({'employee_name': '', 'employee_code': ''})
                stationlist.append(stationitem)
            values['workstations'] = stationlist
        return values
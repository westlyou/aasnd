# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-8-26 15:49
"""

import logging

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

class AASMESAttendanceController(http.Controller):

    @http.route('/aasmes/attendance/scanner', type='http', auth="user")
    def aasmes_attendance_scanner(self):
        values = {'success': True, 'message': u'上岗需要先选择工位，再扫描员工卡；如果是离岗直接扫描员工卡即可！'}
        login = request.env.user
        values.update({'checker': login.name, 'workstations': [], 'workstation_id': '0', 'workstation_name': '', 'mesline_name': ''})
        checkdomain = [('lineuser_id', '=', login.id)]
        lineuser = request.env['aas.mes.lineusers'].search(checkdomain, limit=1)
        if not lineuser or lineuser.mesrole != 'checker':
            values.update({'success': False, 'message': u'当前登录用户可能不是考勤员，请仔细检查！'})
            return request.render('aas_mes.aas_attendance_scanner', values)
        mesline = lineuser.mesline_id
        values['mesline_name'] = mesline.name
        if mesline.workstation_id:
            values.update({'workstation_id': mesline.workstation_id.id, 'workstation_name': mesline.workstation_id.name})
        workstationlines = request.env['aas.mes.line.workstation'].search([('mesline_id', '=', mesline.id)])
        if workstationlines and len(workstationlines) > 0:
            stationlist = []
            for wline in workstationlines:
                station = wline.workstation_id
                stationitem = {'station_id': station.id, 'station_name': station.name, 'station_type': station.station_type, 'employees': []}
                employeedomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', station.id)]
                employeelist = request.env['aas.mes.workstation.employee'].search(employeedomain)
                if not employeelist or len(employeelist) <= 0:
                    employeelen = 0
                else:
                    employeelen = len(employeelist)
                if employeelen > 0:
                    stationitem['employees'] = [{'employee_name': temployee.employee_id.name, 'employee_code': temployee.employee_id.code} for temployee in employeelist]
                if employeelen < 2:
                    for index in range(0, 2-employeelen):
                        stationitem['employees'].append({'employee_name': '', 'employee_code': ''})
                stationlist.append(stationitem)
            values['workstations'] = stationlist
        else:
            values.update({'success': False, 'message': u'暂时没有工位可以选择，请联系管理员或相关负责人设置产线工位！'})
        return request.render('aas_mes.aas_attendance_scanner', values)


    @http.route('/aasmes/attendance/actionscan', type='json', auth="user")
    def aasmes_attendance_actionscan(self, barcode):
        values = {'success': True, 'message': ''}
        employee = request.env['aas.hr.employee'].search([('barcode', '=', barcode)], limit=1)
        if not employee:
            values.update({'success': False, 'message': u'无效条码，请确认扫描的是否是员工卡！'})
            return values
        lineusersdomain = [('lineuser_id', '=', request.env.user.id)]
        lineuser = request.env['aas.mes.lineusers'].search(lineusersdomain, limit=1)
        if not lineuser or lineuser.mesrole != 'checker':
            values.update({'success': False, 'message': u'当前登录用户可能不是考勤员，请仔细检查！'})
            return values
        searchdomain = [('employee_id', '=', employee.id), ('attend_done', '=', False)]
        mesattendances = request.env['aas.mes.work.attendance'].search(searchdomain)
        if mesattendances and len(mesattendances) > 0:
            for tattendance in mesattendances:
                tattendance.action_done()
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
        lineusersdomain = [('lineuser_id', '=', request.env.user.id)]
        lineuser = request.env['aas.mes.lineusers'].search(lineusersdomain, limit=1)
        if not lineuser or lineuser.mesrole != 'checker':
            values.update({'success': False, 'message': u'当前登录用户可能不是考勤员，请仔细检查！'})
        mesline = lineuser.mesline_id
        searchdomain = [('employee_id', '=', employeeid), ('attend_done', '=', False)]
        mesattendance = request.env['aas.mes.work.attendance'].search(searchdomain, limit=1)
        if not mesattendance or mesattendance.workstation_id.id != stationid:
            attendancevals = {'employee_id': employeeid, 'workstation_id': stationid, 'mesline_id': mesline.id}
            request.env['aas.mes.work.attendance'].create(attendancevals)
        values['message'] = u'亲，您已上岗！努力工作吧，加油！'
        return values


    @http.route('/aasmes/attendance/refreshstations', type='json', auth="user")
    def aasmes_attendance_refreshstations(self):
        values = {'success': True, 'message': '', 'workstations': []}
        checkdomain = [('lineuser_id', '=', request.env.user.id)]
        lineuser = request.env['aas.mes.lineusers'].search(checkdomain, limit=1)
        if not lineuser:
            values.update({'success': False, 'message': u'请确认，当前用户可能已经不是生产考勤员了！'})
            return values
        mesline = lineuser.mesline_id
        workstationlines = request.env['aas.mes.line.workstation'].search([('mesline_id', '=', mesline.id)])
        if workstationlines and len(workstationlines) > 0:
            stationlist = []
            for wline in workstationlines:
                station = wline.workstation_id
                stationitem = {'station_id': station.id, 'station_name': station.name, 'station_type': station.station_type, 'employees': []}
                employeedomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', station.id)]
                employeelist = request.env['aas.mes.workstation.employee'].search(employeedomain)
                if not employeelist or len(employeelist) <= 0:
                    employeelen = 0
                else:
                    employeelen = len(employeelist)
                if employeelen > 0:
                    stationitem['employees'] = [{'employee_name': temployee.employee_id.name, 'employee_code': temployee.employee_id.code} for temployee in employeelist]
                if employeelen < 2:
                    for index in range(0, 2-employeelen):
                        stationitem['employees'].append({'employee_name': '', 'employee_code': ''})
                stationlist.append(stationitem)
            values['workstations'] = stationlist
        return values
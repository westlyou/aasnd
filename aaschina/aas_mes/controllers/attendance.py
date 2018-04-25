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
        values = {'success': True, 'message': u'上岗需要先选择工位，再扫描员工卡；如果是离岗扫描员工卡后必须选择离岗原因方可离开！'}
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
    def aasmes_attendance_actionscan(self, barcode, stationid=None):
        values = {'success': True, 'message': ''}
        employee = request.env['aas.hr.employee'].search([('barcode', '=', barcode.upper())], limit=1)
        if not employee:
            values.update({'success': False, 'message': u'无效条码，请确认扫描的是否是员工卡！'})
            return values
        values.update({'employee_id': employee.id, 'employee_name': employee.name})
        lineusersdomain = [('lineuser_id', '=', request.env.user.id)]
        lineuser = request.env['aas.mes.lineusers'].search(lineusersdomain, limit=1)
        if not lineuser or lineuser.mesrole != 'checker':
            values.update({'success': False, 'message': u'当前登录用户可能不是考勤员，请仔细检查！'})
            return values
        mesline, workstation = lineuser.mesline_id, False
        if stationid:
            workstation = request.env['aas.mes.workstation'].browse(stationid)
            if not workstation:
                values.update({'success': False, 'message': u'工位异常，请仔细检查！'})
                return values
        avalues = request.env['aas.mes.work.attendance'].action_scanning(employee, mesline, workstation)
        values.update(avalues)
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

    @http.route('/aasmes/attendance/loadingleavelist', type='json', auth="user")
    def aasmes_attendance_loadingleavelist(self):
        values = {'success': True, 'message': '', 'leavelist': []}
        leavelist = request.env['aas.mes.work.attendance.leave'].search([])
        if leavelist and len(leavelist) > 0:
            values['leavelist'] = [{'leave_id': tleave.id, 'leave_name': tleave.name} for tleave in leavelist]
        return values


    @http.route('/aasmes/attendance/actionleave', type='json', auth="user")
    def aasmes_attendance_actionleave(self, attendanceid, leaveid):
        values = {'success': True, 'message': ''}
        attendance = request.env['aas.mes.work.attendance'].browse(attendanceid)
        attendance.write({'leave_id': leaveid})
        attendlines = request.env['aas.mes.work.attendance.line'].search([('attendance_id', '=', attendanceid), ('leave_id', '=', False)])
        if attendlines and len(attendlines) > 0:
            attendlines.write({'leave_id': leaveid})
        return values



    @http.route('/aasmes/attendance/workstation/equipmentlist', type='json', auth="user")
    def aasmes_attendance_actionleave(self, workstationid):
        values = {'success': True, 'message': '', 'equipmentlist': []}
        login = request.env.user
        checkdomain = [('lineuser_id', '=', login.id)]
        lineuser = request.env['aas.mes.lineusers'].search(checkdomain, limit=1)
        if not lineuser or lineuser.mesrole != 'checker':
            values.update({'success': False, 'message': u'当前登录用户可能不是考勤员，请仔细检查！'})
            return values
        tempdomain = [('mesline_id', '=', lineuser.mesline_id.id), ('workstation_id', '=', workstationid)]
        tempequipments = request.env['aas.mes.workstation.equipment'].search(tempdomain)
        if tempequipments and len(tempequipments) > 0:
            equipmentlist = []
            for tequipment in tempequipments:
                equipment = tequipment.equipment_id
                equipmentlist.push({
                    'equipment_id': equipment.id, 'equipment_name': equipment.name, 'equipment_code': equipment.code
                })
            values['equipmentlist'] = equipmentlist
        return values
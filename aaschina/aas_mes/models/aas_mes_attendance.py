# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-12-13 23:33
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

class AASMESWorkAttendance(models.Model):
    _name = 'aas.mes.work.attendance'
    _description = 'AAS MES Work Attendance'
    _rec_name = 'employee_name'
    _order = 'attendance_start desc,attendance_finish desc'

    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', ondelete='restrict', index=True)
    employee_name = fields.Char(string=u'员工名称', copy=False)
    employee_code = fields.Char(string=u'员工工号', copy=False)
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='restrict', index=True)
    equipment_name = fields.Char(string=u'设备名称', copy=False)
    equipment_code = fields.Char(string=u'设备编码', copy=False)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict', index=True)
    mesline_name = fields.Char(string=u'产线名称', copy=False)
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict', index=True)
    workstation_name = fields.Char(string=u'工位名称', copy=False)
    attendance_date = fields.Char(string=u'在岗日期', compute='_compute_attendance_date', store=True)
    attendance_start = fields.Datetime(string=u'上岗时间', default=fields.Datetime.now, copy=False)
    attendance_finish = fields.Datetime(string=u'离岗时间', copy=False)
    attendance_hours = fields.Float(string=u'工时', compute='_compute_attendance_hours', store=True)
    attend_done = fields.Boolean(string=u'是否结束', default=False, copy=False)

    @api.depends('attendance_start', 'attendance_finish')
    def _compute_attendance_hours(self):
        for record in self:
            record.attendance_hours = 0.0
            if record.attendance_start and record.attendance_finish:
                temptimes = fields.Datetime.from_string(record.attendance_finish) - fields.Datetime.from_string(record.attendance_start)
                record.attendance_hours = temptimes.total_seconds() / 3600.00


    @api.depends('attendance_start')
    def _compute_attendance_date(self):
        for record in self:
            if record.attendance_start:
                tz_name = self.env.context.get('tz') or self.env.user.tz or 'Asia/Shanghai'
                record.attendance_date = fields.Datetime.to_timezone_string(record.attendance_start, tz_name)[0:10]
            else:
                record.attendance_date = False



    @api.model
    def action_trace_employees_equipments(self, mesline_id, schedule_id, workstation_id, attendance_date):
        """
        获取相应日期的产线班次上指定工位的员工和设备信息
        :param mesline_id:
        :param schedule_id:
        :param workstation_id:
        :param attendance_date:
        :return:
        """
        tracingdomain, tracevals = [], {'employeelist': '', 'equipmentlist': ''}
        if mesline_id:
            tracingdomain.append(('mesline_id', '=', mesline_id))
        if schedule_id:
            tracingdomain.append(('schedule_id', '=', schedule_id))
        if workstation_id:
            tracingdomain.append(('workstation_id', '=', workstation_id))
        if attendance_date:
            tracingdomain.append(('attendance_date', '=', attendance_date))
        if not tracingdomain or len(attendance_date) <= 0:
            return tracevals
        attendances = self.env['aas.mes.work.attendance'].search(tracingdomain)
        if attendances and len(tracingdomain) > 0:
            employeeids, employees, equipmentids, equipments = [], [], [], []
            for attendance in attendances:
                temployee, tequipment = attendance.employee_id, attendance.equipment_id
                if temployee and temployee.id not in employeeids:
                    employeeids.append(temployee.id)
                    employees.append(attendance.employee_name+'['+attendance.employee_code+']')
                if tequipment and tequipment.id not in equipmentids:
                    equipmentids.append(tequipment.id)
                    equipments.append(attendance.equipment_name+'['+attendance.equipment_code+']')
            if employees and len(employees) > 0:
                tracevals['employeelist'] = ','.join(employees)
            if equipments and len(equipments) > 0:
                tracevals['equipmentlist'] = ','.join(equipments)
        return tracevals


    @api.model
    def create(self, vals):
        record = super(AASMESWorkAttendance, self).create(vals)
        record.action_after_create()
        return record

    @api.one
    def action_after_create(self):
        empvals, employee = {'state': 'working'}, self.employee_id
        attendvals = {'employee_name': employee.name, 'employee_code': employee.code}
        if self.equipment_id:
            attendvals.update({'equipment_name': self.equipment_id.name, 'equipment_code': self.equipment_id.code})
        if self.mesline_id:
            attendvals['mesline_name'] = self.mesline_id.name
            if self.mesline_id.schedule_id:
                attendvals['schedule_id'] = self.mesline_id.schedule_id.id
                empvals['schedule_id'] = self.mesline_id.schedule_id.id
            empvals['mesline_id'] = self.mesline_id.id
        if self.workstation_id:
            attendvals['workstation_name'] = self.workstation_id.name
        if attendvals and len(attendvals) > 0:
            self.write(attendvals)
        employee.write(empvals)
        self.env['aas.mes.workstation.employee'].create({
            'workstation_id': self.workstation_id.id, 'mesline_id': self.mesline_id.id,
            'employee_id': self.employee_id.id, 'equipment_id': False if not self.equipment_id else self.equipment_id.id
        })

    @api.one
    def action_done(self):
        self.write({'attendance_finish': fields.Datetime.now(), 'attend_done': True})
        employeedomain = [('workstation_id', '=', self.workstation_id.id), ('employee_id', '=', self.employee_id.id)]
        employeedomain.append(('mesline_id', '=', self.mesline_id.id))
        workstation_employees = self.env['aas.mes.workstation.employee'].search(employeedomain)
        if workstation_employees and len(workstation_employees) > 0:
            workstation_employees.unlink()
        attendancecount = self.env['aas.mes.work.attendance'].search_count([('employee_id', '=', self.employee_id.id), ('attend_done', '=', False)])
        if attendancecount <= 0:
            self.employee_id.write({'state': 'leave'})

    @api.model
    def action_workstation_scanning(self, equipment_code, employee_barcode):
        """
        工控工位扫描员工卡
        :param equipment_code:
        :param employee_barcode:
        :return:
        """
        result = {'success': True, 'message': '', 'action': 'working'}
        if not equipment_code:
            result.update({'success': False, 'message': u'您确认已经设置了设备编码吗？'})
            return result
        equipment = self.env['aas.equipment.equipment'].search([('code', '=', equipment_code)], limit=1)
        if not equipment:
            result.update({'success': False, 'message': u'设备异常，请仔细检查系统是否存在此设备！'})
            return result
        if not equipment.mesline_id or not equipment.workstation_id:
            result.update({'success': False, 'message': u'当前设备可能还未设置产线工位！'})
            return result
        employee = self.env['aas.hr.employee'].search([('barcode', '=', employee_barcode)], limit=1)
        if not employee:
            result.update({'success': False, 'message': u'请确认是否有此员工存在，或许当前员已被删除，请仔细检查！'})
            return result
        result.update({'employee_name': employee.name, 'employee_code': employee.code})
        attendance_domain = [('employee_id', '=', employee.id), ('attend_done', '=', False)]
        attendance = self.env['aas.mes.work.attendance'].search(attendance_domain, limit=1)
        if attendance:
            message = u"%s,您已经离开工位%s"% (attendance.employee_name, attendance.workstation_name)
            attendance.action_done()
            result.update({'message': message, 'action': 'leave'})
            return result
        mesline, workstation = equipment.mesline_id, equipment.workstation_id
        attendancevals = {
            'employee_id': employee.id, 'equipment_id': equipment.id,
            'workstation_id': workstation.id, 'mesline_id': mesline.id
        }
        self.env['aas.mes.work.attendance'].create(attendancevals)
        result['message'] = u"%s,您已经在工位%s上上岗了，加油工作吧！"% (employee.name, workstation.name)
        return result

# 出勤明细
class AASMESWorkAttendanceLine(models.Model):
    _name = 'aas.mes.work.attendance.line'
    _description = 'AAS MES Attendance Line'

    attendance_id = fields.Many2one(comodel_name='aas.mes.work.attendance', string=u'出勤', ondelete='cascade')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='restrict')
    attendance_start = fields.Datetime(string=u'开始时间', default=fields.Datetime.now)
    attendance_finish = fields.Datetime(string=u'结束时间')
    attendance_time = fields.Float(string=u'在岗工时', compute='_compute_attendance_time', store=True)
    leave_id = fields.Many2one(comodel_name='aas.mes.work.attendance.leave', string=u'离开原因', ondelete='restrict')
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='restrict', default=lambda self:self.env.user.company_id)

    @api.depends('attendance_start', 'attendance_finish')
    def _compute_attendance_time(self):
        for record in self:
            if record.attendance_start and record.attendance_finish:
                temptimes = fields.Datetime.from_string(record.attendance_finish) - fields.Datetime.from_string(record.attendance_start)
                record.attendance_time = temptimes.total_seconds() / 3600.00
            else:
                record.attendance_time = 0.0


# 员工出勤离开原因
class AASMESWorkAttendanceLeave(models.Model):
    _name = 'aas.mes.work.attendance.leave'
    _description = 'AAS MES Attendance Leave'

    name = fields.Char(string=u'名称', required=True, copy=False, index=True)
    active = fields.Boolean(string=u'是否有效', default=True)
    operate_time = fields.Datetime(string=u'创建时间', default=fields.Datetime.now)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'创建人', ondelete='restrict', default=lambda self: self.env.user)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='restrict', default=lambda self:self.env.user.company_id)

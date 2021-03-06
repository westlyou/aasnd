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
from odoo.tools.sql import drop_view_if_exists

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
    attendance_date = fields.Char(string=u'在岗日期')
    attendance_start = fields.Datetime(string=u'上岗时间', default=fields.Datetime.now, copy=False)
    attendance_finish = fields.Datetime(string=u'离岗时间', copy=False, help=u'最近一次离开的时间')
    attend_hours = fields.Float(string=u'总工时', default=0.0, copy=False)
    overtime_hours = fields.Float(string=u'加班工时', default=0.0, copy=False)
    attend_done = fields.Boolean(string=u'是否结束', default=False, copy=False)
    leave_id = fields.Many2one(comodel_name='aas.mes.work.attendance.leave', string=u'离岗原因', ondelete='restrict')
    worktime_min = fields.Float(string=u'最短工时')
    worktime_max = fields.Float(string=u'最长工时')
    worktime_standard = fields.Float(string=u'标准工时')
    worktime_advance = fields.Float(string=u'提前工时')
    worktime_delay = fields.Float(string=u'延迟工时')
    company_id = fields.Many2one('res.company', string=u'公司', index=True, default=lambda self: self.env.user.company_id)

    leave_hours = fields.Float(string=u'离岗工时', default=0.0, copy=False)
    attend_lines = fields.One2many(comodel_name='aas.mes.work.attendance.line', inverse_name='attendance_id', string=u'出勤明细')



    @api.model
    def action_scanning(self, employee, mesline, workstation=None, equipment=None):
        """扫描上下岗
        :param employee:
        :param mesline:
        :param worstation:
        :return:
        """
        values = {'success': True, 'message': '', 'action': 'working'}
        tempdomain = [('employee_id', '=', employee.id), ('attend_done', '=', False)]
        tattendance = self.env['aas.mes.work.attendance'].search(tempdomain, limit=1)
        if tattendance:
            # 检测在岗时间是否达到最大工时，达到最大工时就关闭此出勤记录
            tattendance.action_done()
            if tattendance.attend_done:
                tattendance = False
        equipmentid = False if not equipment else equipment.id
        if tattendance:
            values.update({'attendance_id': tattendance.id})
            linedomain = [('attendance_id', '=', tattendance.id)]
            linedomain += [('equipment_id', '=', equipmentid), ('attend_done', '=', False)]
            if workstation:
                attenddomain = [('workstation_id', '=', workstation.id)]
                attenddomain += linedomain
                attendancelines = self.env['aas.mes.work.attendance.line'].search(attenddomain)
                if not attendancelines or len(attendancelines) <= 0:
                    tresult = self.action_attend(employee, mesline, workstation, tattendance, equipment=equipment)
                    if not tresult.get('success', False):
                        values.update(tresult)
                    else:
                        values.update({'message': u'您已经在%s上岗，祝您工作愉快！'% workstation.name})
                else:
                    self.action_attendance_leave(tattendance.id)
                    values['action'] = 'leave'
                return values
            else:
                attendancelines = self.env['aas.mes.work.attendance.line'].search(linedomain)
                if attendancelines and len(attendancelines) > 0:
                    self.action_attendance_leave(tattendance.id)
                    values['action'] = 'leave'
                else:
                    values.update({'success': False, 'message': u'您还未选择上岗工位！'})
                return values
        elif not workstation:
            values.update({'success': False, 'message': u'您还未选择上岗工位！'})
            return values
        else:
            tvalues = self.action_attend(employee, mesline, workstation, equipment=equipment)
            values.update({'message': u'您已经在%s上岗，祝您工作愉快！'% workstation.name})
            if not tvalues.get('success', False):
                values.update(tvalues)
                return values
            values['attendance_id'] = tvalues['attendance_id']
        return values

    @api.model
    def action_attendance_leave(self, attendanceid):
        tempdomain = [('attendance_id', '=', attendanceid), ('attend_done', '=', False)]
        templines = self.env['aas.mes.work.attendance.line'].search(tempdomain)
        if templines and len(templines) > 0:
            templines.action_done()



    @api.model
    def action_attend(self, employee, mesline, workstation, attendance=None, equipment=None):
        """更新出勤信息，添加出勤明细
        :param employee:
        :param mesline:
        :param workstation:
        :param attendance:
        :param equipment:
        :return:
        """
        values = {'success': True, 'message': ''}
        if attendance and employee.id != attendance.employee_id.id:
            values = {'success': False, 'message': u'出勤记录异常，请仔细检查！'}
            return values
        firstscheduleid = False
        if not attendance:
            tempdomain = [('employee_id', '=', employee.id), ('attend_done', '=', False)]
            attendance = self.env['aas.mes.work.attendance'].search(tempdomain, limit=1)
        if not attendance:
            tvalues = self.action_addattendance(employee, mesline)
            if not tvalues.get('success', False):
                values.update(tvalues)
                return values
            attendance = tvalues['attendance']
            firstscheduleid = tvalues['scheduleid']
        values.update({'attendance_id': attendance.id})
        equipmentid = False if not equipment else equipment.id
        alinedomain = [
            ('attendance_id', '=', attendance.id), ('employee_id', '=', employee.id),
            ('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id), ('attend_done', '=', False)
        ]
        if equipmentid:
            alinedomain.append(('equipment_id', '=', equipmentid))
        if self.env['aas.mes.work.attendance.line'].search_count(alinedomain) <= 0:
            self.env['aas.mes.work.attendance.line'].create({
                'attendance_id': attendance.id,
                'employee_id': employee.id, 'equipment_id': equipmentid,
                'mesline_id': mesline.id, 'workstation_id': workstation.id,
                'attendance_date': attendance.attendance_date, 'schedule_id': firstscheduleid
            })
        return values


    @api.model
    def action_addattendance(self, employee, mesline):
        """添加出勤
        :param employee:
        :param mesline:
        :return:
        """
        values = {'success': True, 'message': '', 'attendance': False, 'scheduleid': False}
        attendancevals = {'employee_id': employee.id, 'employee_name': employee.name}
        worktime_min = self.env['ir.values'].sudo().get_default('aas.mes.settings', 'worktime_min')
        worktime_max = self.env['ir.values'].sudo().get_default('aas.mes.settings', 'worktime_max')
        worktime_advance = self.env['ir.values'].sudo().get_default('aas.mes.settings', 'worktime_advance')
        worktime_standard = self.env['ir.values'].sudo().get_default('aas.mes.settings', 'worktime_standard')
        worktime_delay = self.env['ir.values'].sudo().get_default('aas.mes.settings', 'worktime_delay')
        attendancevals.update({
            'worktime_advance': worktime_advance, 'worktime_delay': worktime_delay,
            'worktime_min': worktime_min, 'worktime_max': worktime_max, 'worktime_standard': worktime_standard
        })
        if not mesline.schedule_lines and len(mesline.schedule_lines) <= 0:
            values.update({'success': False, 'message': u'产线%s还未设置班次，请联系管理员设置班次信息！'% mesline.name})
            return values
        if not mesline.workdate:
            mesline.sudo().action_refresh_schedule()
        timestart = fields.Datetime.now()
        attendancevals.update({'attendance_start': timestart, 'attendance_date': mesline.workdate})
        nextvalues = self.env['aas.mes.line'].loading_nextschedule(mesline)
        if not nextvalues.get('success', False):
            values.update(nextvalues)
            return values
        nextschedule = nextvalues['schedule']
        temptimes = fields.Datetime.from_string(nextschedule['actual_start']) - fields.Datetime.from_string(timestart)
        tempinterval = temptimes.total_seconds() / 3600.00
        if float_compare(tempinterval, 0.0, precision_rounding=0.000001) < 0.0:
            attendancevals.update({
                'attendance_start': timestart,
                'attendance_date': nextschedule['workdate'], 'scheduleid': nextschedule['schedule_id']
            })
        elif float_compare(tempinterval, worktime_advance, precision_rounding=0.000001) <= 0.0:
            attendancevals.update({
                'attendance_start': nextschedule['actual_start'],
                'attendance_date': nextschedule['workdate'], 'scheduleid': nextschedule['schedule_id']
            })
        values['attendance'] = self.env['aas.mes.work.attendance'].create(attendancevals)
        return values


    @api.multi
    def action_done(self, donedirectly=False):
        """完成出勤，更新相关信息
        :return:
        """
        currentstr = fields.Datetime.now()
        currenttime = fields.Datetime.from_string(currentstr)
        for record in self:
            starttime = fields.Datetime.from_string(record.attendance_start)
            timeinterval = (currenttime - starttime).total_seconds() / 3600.0
            maxworktime = record.worktime_max
            if record.worktime_delay and float_compare(record.worktime_delay, 0.0, precision_rounding=0.000001) >= 0.0:
                maxworktime += record.worktime_delay
            unfinished = float_compare(timeinterval, maxworktime, precision_rounding=0.000001) < 0.0
            if not donedirectly and unfinished:
                continue
            linedomain = [('attendance_id', '=', record.id), ('attend_done', '=', False)]
            templines = self.env['aas.mes.work.attendance.line'].search(linedomain)
            if templines and len(templines) > 0:
                templines.action_done()
            attendancevals = {'attend_done': True}
            if not record.attendance_finish:
                finishtime = currenttime
                attendancevals['attendance_finish'] = currentstr
            else:
                finishtime = fields.Datetime.from_string(record.attendance_finish)
            totaltime = (finishtime - starttime).total_seconds() / 3600.0
            if float_compare(totaltime, 0.0, precision_rounding=0.000001) <= 0.0:
                totaltime = 0.0
            attendancevals['attend_hours'] = totaltime
            overtime = totaltime - record.worktime_standard
            if float_compare(overtime, 0.0, precision_rounding=0.000001) > 0.0:
                attendancevals['overtime_hours'] = overtime
            record.write(attendancevals)
            if not record.attend_lines or len(record.attend_lines) <= 0:
                continue
            # 关闭出勤明细
            record.attend_lines.action_done()
            # 更新工作日信息
            linedict = {}
            for aline in record.attend_lines:
                if not aline.schedule_id:
                    continue
                akey = aline.attendance_date + '-' + str(aline.schedule_id.id)
                if akey not in linedict:
                    linedict[akey] = {'attendance_date': aline.attendance_date, 'attend_hours': aline.attend_hours}
                else:
                    linedict[akey]['attend_hours'] += aline.attend_hours
            if linedict and len(linedict) > 0:
                workdate, thours = False, 0.0
                for lkey, lval in linedict.items():
                    if float_compare(lval['attend_hours'], thours, precision_rounding=0.000001) > 0.0:
                        thours, workdate = lval['attend_hours'], lval['attendance_date']
                record.update({'attendance_date': workdate})

    @api.model
    def action_workstation_scanning(self, equipment_code, employee_barcode):
        """工控工位扫描员工卡
        :param equipment_code:
        :param employee_barcode:
        :return:
        """
        values = {'success': True, 'message': '', 'action': 'working'}
        if not equipment_code:
            values.update({'success': False, 'message': u'您确认已经设置了设备编码吗？'})
            return values
        equipment = self.env['aas.equipment.equipment'].search([('code', '=', equipment_code)], limit=1)
        if not equipment:
            values.update({'success': False, 'message': u'设备异常，请仔细检查系统是否存在此设备！'})
            return values
        mesline, workstation = equipment.mesline_id, equipment.workstation_id
        if not mesline or not workstation:
            values.update({'success': False, 'message': u'当前设备可能还未设置产线工位，请仔细检查！'})
            return values
        employee = self.env['aas.hr.employee'].search([('barcode', '=', employee_barcode)], limit=1)
        if not employee:
            values.update({'success': False, 'message': u'请确认是否有此员工存在，或许当前员已被删除，请仔细检查！'})
            return values
        values = self.action_scanning(employee, mesline, workstation, equipment)
        if not values.get('success', False):
            return values
        values.update({'employee_name': employee.name, 'employee_code': employee.code})
        return values


    @api.model
    def action_done_attendances(self):
        attendances = self.env['aas.mes.work.attendance'].search([('attend_done', '=', False)])
        if attendances and len(attendances) > 0:
            attendances.action_done()




# 出勤明细
class AASMESWorkAttendanceLine(models.Model):
    _name = 'aas.mes.work.attendance.line'
    _description = 'AAS MES Attendance Line'
    _rec_name = 'employee_id'
    _order = 'id desc'

    attendance_id = fields.Many2one(comodel_name='aas.mes.work.attendance', string=u'出勤', ondelete='cascade', index=True)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict', index=True)
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次', ondelete='restrict', index=True)
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', ondelete='restrict', index=True)
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict', index=True)
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='restrict', index=True)
    attendance_date = fields.Char(string=u'在岗日期', copy=False)
    attendance_start = fields.Datetime(string=u'开始时间', default=fields.Datetime.now)
    attendance_finish = fields.Datetime(string=u'结束时间')
    attend_done = fields.Boolean(string=u'出勤结束', default=False, copy=False)
    attend_hours = fields.Float(string=u'在岗工时', compute='_compute_attend_hours', store=True)
    leave_id = fields.Many2one(comodel_name='aas.mes.work.attendance.leave', string=u'离开原因', ondelete='restrict')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self:self.env.user.company_id)

    mesline_name = fields.Char(string=u'产线名称', copy=False)
    schedule_name = fields.Char(string=u'班次名称', copy=False)
    employee_name = fields.Char(string=u'员工名称', copy=False)
    leave_hours = fields.Float(string=u'离岗工时', default=0.0, copy=False)
    recentlyleave = fields.Boolean(string=u'最近离开', default=False, copy=False)

    @api.depends('attendance_start', 'attendance_finish')
    def _compute_attend_hours(self):
        for record in self:
            if record.attendance_start and record.attendance_finish:
                temptimes = fields.Datetime.from_string(record.attendance_finish) - fields.Datetime.from_string(record.attendance_start)
                record.attend_hours = temptimes.total_seconds() / 3600.00
            else:
                record.attend_hours = 0.0

    @api.model
    def create(self, vals):
        record = super(AASMESWorkAttendanceLine, self).create(vals)
        record.action_after_create()
        return record



    @api.one
    def action_after_create(self):
        mesline, workstation, employee = self.mesline_id, self.workstation_id, self.employee_id
        linevals = {'mesline_name': mesline.name, 'employee_name': employee.name}
        if not self.schedule_id and mesline.schedule_id:
            linevals.update({'schedule_id': mesline.schedule_id.id, 'schedule_name': mesline.schedule_id.name})
            if mesline.workdate and self.attendance_date and mesline.workdate < self.attendance_date:
                tschedule = self.env['aas.mes.schedule'].get_next_schedule(mesline, shcedule=mesline.schedule_id)
                if tschedule:
                    linevals.update({'schedule_id': tschedule.id, 'schedule_name': tschedule.name})
        if not self.attendance_date and mesline.workdate:
            linevals['attendance_date'] = mesline.workdate
        if linevals and len(linevals) > 0:
            self.write(linevals)
        # 更新工位员工信息
        self.action_update_workstationemployee()
        attendance = self.attendance_id
        # 计算当前工位上的离岗工时
        linedomain = [('attendance_id', '=', attendance.id), ('recentlyleave', '=', True), ('attend_done', '=', True)]
        linedomain += [('workstation_id', '=', workstation.id), ('mesline_id', '=', mesline.id)]
        templine = self.env['aas.mes.work.attendance.line'].search(linedomain, limit=1)
        if templine:
            currenttime = fields.Datetime.from_string(fields.Datetime.now())
            leavetime = fields.Datetime.from_string(templine.attendance_finish)
            templine.write({
                'recentlyleave': False,
                'leave_hours': (currenttime - leavetime).total_seconds() / 3600.00
            })
        # 更新员工当日的出勤信息和离岗工时
        if attendance.attendance_finish:
            tempstart = fields.Datetime.from_string(attendance.attendance_finish)
            tempfinish = fields.Datetime.from_string(fields.Datetime.now())
            leave_hours = (tempfinish - tempstart).total_seconds() / 3600.00 + attendance.leave_hours
            attendance.write({'attendance_finish': False, 'leave_id': False, 'leave_hours': leave_hours})




    @api.one
    def action_update_workstationemployee(self):
        """更新工位员工信息
        :return:
        """
        employee, mesline, workstation = self.employee_id, self.mesline_id, self.workstation_id
        equipment_id = False if not self.equipment_id else self.equipment_id.id
        tempdomain = [('employee_id', '=', employee.id)]
        tempdomain += [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        if equipment_id:
            tempdomain.append(('equipment_id', '=', equipment_id))
        if self.env['aas.mes.workstation.employee'].search_count(tempdomain) <= 0:
            self.env['aas.mes.workstation.employee'].create({
                'employee_id': self.employee_id.id, 'equipment_id': equipment_id,
                'mesline_id': self.mesline_id.id, 'workstation_id': workstation.id
            })
        if employee.state != 'working':
            employee.write({'state': 'working'})


    @api.multi
    def action_done(self):
        """出勤结束
        :return:
        """
        employeeids, attendanceids, attendlines = [], [], self.env['aas.mes.work.attendance.line']
        for record in self:
            if record.attend_done:
                continue
            attendlines |= record
            if record.employee_id.id not in employeeids:
                employeeids.append(record.employee_id.id)
            if record.attendance_id and record.attendance_id.id not in attendanceids:
                attendanceids.append(record.attendance_id.id)
        currenttime = fields.Datetime.now()
        attendancevals = {'attendance_finish': currenttime, 'attend_done': True, 'recentlyleave': True}
        if attendlines and len(attendlines) > 0:
            attendlines.write(attendancevals)
        if attendanceids and len(attendanceids) > 0:
            attendancelist = self.env['aas.mes.work.attendance'].browse(attendanceids)
            attendancelist.write({'attendance_finish': currenttime})
        if employeeids and len(employeeids) > 0:
            wsemployees = self.env['aas.mes.workstation.employee'].search([('employee_id', 'in', employeeids)])
            if wsemployees and len(wsemployees) > 0:
                wsemployees.unlink()
            employeelist = self.env['aas.hr.employee'].browse(employeeids)
            employeelist.write({'state': 'leave'})


    @api.multi
    def action_split(self):
        """
        出勤记录分割
        :return:
        """
        for record in self:
            if record.attend_done:
                continue
            attendancevals, mesline, workdate = {}, record.mesline_id, record.attendance_date
            oldscheduleid = False if not record.schedule_id else record.schedule_id.id
            if mesline.workdate != workdate:
                attendancevals['attendance_date'] = mesline.workdate
            newscheduleid = False if not mesline.schedule_id else mesline.schedule_id.id
            if newscheduleid != oldscheduleid:
                attendancevals['schedule_id'] = newscheduleid
            if attendancevals and len(attendancevals) > 0:
                attendancevals.update({
                    'attendance_id': record.attendance_id.id, 'mesline_id': mesline.id,
                    'employee_id': record.employee_id.id, 'workstation_id': record.workstation_id.id,
                    'company_id': record.company_id.id, 'schedule_id': newscheduleid,
                    'equipment_id': False if not record.equipment_id else record.equipment_id.id
                })
                record.action_done()
                self.env['aas.mes.work.attendance.line'].create(attendancevals)

    @api.model
    def get_schedule(self, mesline, workstationid, employeeid):
        """获取员工所在产线工位的当前班次
        :param meslineid:
        :param workstationid:
        :param employeeid:
        :return:
        """
        values, schedule = {'success': True, 'message': '', 'schedule': False}, False
        tempdomain = [('employee_id', '=', employeeid)]
        tempdomain += [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstationid)]
        tattendance = self.env['aas.mes.work.attendance.line'].search(tempdomain, limit=1)
        if tattendance and tattendance.schedule_id:
            schedule = tattendance.schedule_id
        if not schedule and mesline.schedule_id:
            schedule = mesline.schedule_id
        values['schedule'] = schedule
        return values





# 员工出勤离开原因
class AASMESWorkAttendanceLeave(models.Model):
    _name = 'aas.mes.work.attendance.leave'
    _description = 'AAS MES Attendance Leave'

    name = fields.Char(string=u'名称', required=True, copy=False, index=True)
    active = fields.Boolean(string=u'是否有效', default=True)
    operate_time = fields.Datetime(string=u'创建时间', default=fields.Datetime.now)
    operator_id = fields.Many2one('res.users', string=u'创建人', ondelete='restrict', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string=u'公司', ondelete='restrict', default=lambda self:self.env.user.company_id)




class AASMESWorkAttendanceReport(models.Model):
    _auto = False
    _name = 'aas.mes.work.attendance.report'
    _description = 'AAS MES Work Attendance Report'
    _order = 'attendance_date desc, attendance_finish desc'
    _rec_name = 'employee_id'


    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', readonly=True)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', readonly=True)
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次', readonly=True)
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', readonly=True)
    attendance_date = fields.Char(string=u'出勤日期', readonly=True)
    attendance_start = fields.Datetime(string=u'开始时间', readonly=True)
    attendance_finish = fields.Datetime(string=u'结束时间', readonly=True)
    actual_hours = fields.Float(string=u'总工时', default=0.0, readonly=True)
    overtime_hours = fields.Float(string=u'加班工时', default=0.0, readonly=True)
    standard_hours = fields.Float(string=u'正常工时', default=0.0, readonly=True)
    leave_hours = fields.Float(string=u'离岗工时', default=0.0, readonly=True)

    def _select_sql(self):
        _select_sql = """
        SELECT id,
        employee_id,
        mesline_id,
        schedule_id,
        workstation_id,
        attendance_date,
        attendance_start,
        attendance_finish,
        actual_hours,
        leave_hours,
        CASE WHEN overtime_hours > 0 THEN 8 ELSE actual_hours END AS standard_hours,
        CASE WHEN overtime_hours > 0 THEN overtime_hours ELSE 0 END AS overtime_hours
        FROM (
        SELECT MIN(id) AS id,
        employee_id,
        mesline_id,
        schedule_id,
        workstation_id,
        attendance_date,
        SUM(leave_hours) AS leave_hours,
        MIN(attendance_start) AS attendance_start,
        MAX(attendance_finish) AS attendance_finish,
        round((date_part('epoch', max(attendance_finish) - min(attendance_start)) / 3600.0)::numeric, 3) AS actual_hours,
        round((date_part('epoch', max(attendance_finish) - min(attendance_start)) / 3600.0)::numeric, 3) - 8 AS overtime_hours
        FROM aas_mes_work_attendance_line
        WHERE attend_done = true
        GROUP BY employee_id, mesline_id, schedule_id, workstation_id, attendance_date
        ) AS wattendance
        """
        return _select_sql


    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (self._table, self._select_sql()))

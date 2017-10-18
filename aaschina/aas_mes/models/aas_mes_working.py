# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-8-25 11:05
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import math
import pytz
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)



# 生产班次表
class AASMESSchedule(models.Model):
    _name = 'aas.mes.schedule'
    _description = 'AAS MES Schedule'
    _order = 'mesline_id,sequence'

    name = fields.Char(string=u'名称')
    sequence = fields.Integer(string=u'序号')
    work_start = fields.Float(string=u'开始时间', default=0.0)
    work_finish = fields.Float(string=u'结束时间', default=0.0)
    actual_start = fields.Datetime(string=u'实际开始时间', copy=False)
    actual_finish = fields.Datetime(string=u'实际结束时间', copy=False)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    state = fields.Selection(selection=[('working', u'生产'), ('break', u'休息')], string=u'状态', default='break')
    employee_lines = fields.One2many(comodel_name='aas.hr.employee', inverse_name='schedule_id', string=u'员工清单')

    _sql_constraints = [
        ('uniq_name', 'unique (mesline_id, name)', u'同一产线的名称不能重复！'),
        ('uniq_sequence', 'unique (mesline_id, sequence)', u'同一产线的序号不能重复！')
    ]

    @api.one
    @api.constrains('work_start', 'work_finish')
    def action_check_constrains(self):
        if float_compare(self.work_start, 0.0, precision_rounding=0.0001) < 0.0 or float_compare(self.work_start, 24.0, precision_rounding=0.0001) >= 0.0:
            raise ValidationError(u'班次开始时间只能在24小时以内！')
        if float_compare(self.work_finish, 0.0, precision_rounding=0.0001) < 0.0 or float_compare(self.work_finish, 24.0, precision_rounding=0.0001) >= 0.0:
            raise ValidationError(u'班次结束时间只能在24小时以内！')


    @api.multi
    def action_checkemployees(self):
        self.ensure_one()
        wizardvals = {'schedule_id': self.id, 'sequence': self.sequence, 'work_start': self.work_start, 'work_finish': self.work_finish}
        if self.employee_lines and len(self.employee_lines) > 0:
            wizardvals['employee_lines'] = [(0, 0, {'employee_id': temployee.id, 'employee_code': temployee.code}) for temployee in self.employee_lines]
        wizard = self.env['aas.mes.schedule.employee.wizard'].create(wizardvals)
        view_form = self.env.ref('aas_mes.view_form_aas_mes_schedule_employee_wizard')
        return {
            'name': u"员工调整",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.schedule.employee.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }

    @api.multi
    def action_refresh_actualtime(self):
        currenttime = fields.Datetime.to_timezone_time(fields.Datetime.now(), 'Asia/Shanghai')
        for record in self:
            start_hour = int(math.floor(record.work_start))
            start_minutes = int(math.floor((record.work_start - start_hour) * 60))
            starttime = currenttime.replace(hour=start_hour, minute=start_minutes)
            finish_hour = int(math.floor(record.work_finish))
            finish_minutes = int(math.floor((record.work_finish - finish_hour) * 60))
            if record.work_finish >= record.work_start:
                finishtime = currenttime.replace(hour=finish_hour, minute=finish_minutes)
            else:
                temptime = currenttime + timedelta(days=1)
                finishtime = temptime.replace(hour=finish_hour, minute=finish_minutes)
            record.write({
                'actual_start': fields.Datetime.to_utc_string(starttime, 'Asia/Shanghai'),
                'actual_finish': fields.Datetime.to_utc_string(finishtime, 'Asia/Shanghai')
            })




class AASMESWorkstation(models.Model):
    _name = 'aas.mes.workstation'
    _description = 'AAS MES Workstation'

    name = fields.Char(string=u'名称', required=True, copy=False)
    code = fields.Char(string=u'编码', required=True, copy=False)
    barcode = fields.Char(string=u'条码', compute='_compute_barcode', store=True, index=True)
    sequence = fields.Integer(string=u'序号', default=1)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'生产线', ondelete='restrict')
    active = fields.Boolean(string=u'是否有效', default=True, copy=False)
    station_type = fields.Selection(selection=[('scanner', u'扫描工位'), ('controller', u'工控工位')], string=u'工位类型', default='scanner', copy=False)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)
    employee_lines = fields.One2many(comodel_name='aas.hr.employee', inverse_name='workstation_id', string=u'员工明细')
    employeelist = fields.Char(string=u'员工清单', compute='_compute_employeelist', store=True)
    equipment_lines = fields.One2many(comodel_name='aas.equipment.equipment', inverse_name='workstation_id', string=u'设备明细')
    equipmentlist = fields.Char(string=u'设备清单', compute='_compute_equipmentlist', store=True)

    _sql_constraints = [
        ('uniq_code', 'unique (code)', u'工位编码不可以重复！'),
        ('uniq_sequence', 'unique (mesline_id, sequence)', u'同一产线的工位序号不可以重复！')
    ]

    @api.multi
    def name_get(self):
        return [(record.id, '%s[%s]' % (record.name, record.code)) for record in self]

    @api.multi
    @api.depends('employee_lines')
    def _compute_employeelist(self):
        for record in self:
            if not record.employee_lines or len(record.employee_lines) <= 0:
                record.employeelist = False
            else:
                record.employeelist = ','.join([empline.name for empline in record.employee_lines])

    @api.multi
    @api.depends('equipment_lines')
    def _compute_equipmentlist(self):
        for record in self:
            if not record.equipment_lines or len(record.equipment_lines) <= 0:
                record.equipmentlist = False
            else:
                record.equipmentlist = ','.join([equline.code for equline in record.equipment_lines])

    @api.depends('code')
    def _compute_barcode(self):
        for record in self:
            record.barcode = 'AS'+record.code

    @api.one
    def action_clear_employees(self):
        attendancelist = self.env['aas.mes.work.attendance'].search([('workstation_id', '=', self.id), ('attend_done', '=', False)])
        if attendancelist and len(attendancelist) > 0:
            for attendance in attendancelist:
                attendance.action_done()



class AASHREmployee(models.Model):
    _inherit = 'aas.hr.employee'

    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')

class AASEquipmentEquipment(models.Model):
    _inherit = 'aas.equipment.equipment'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')


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
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict', index=True)
    workstation_name = fields.Char(string=u'工位名称', copy=False)
    attend_date = fields.Date(string=u'日期', compute='_compute_attend_date', store=True)
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
    def _compute_attend_date(self):
        for record in self:
            if record.attendance_start:
                utctime = fields.Datetime.from_string(record.attendance_start)
                tz_name = self.env.context.get('tz') or self.env.user.tz or 'Asia/Shanghai'
                temptime = pytz.timezone('UTC').localize(utctime, is_dst=False)
                record.attend_date = fields.Date.to_string(temptime.astimezone(pytz.timezone(tz_name)))
            else:
                record.attend_date = False


    @api.model
    def create(self, vals):
        record = super(AASMESWorkAttendance, self).create(vals)
        record.action_after_create()
        return record

    @api.one
    def action_after_create(self):
        attendvals, empvals = {}, {'state': 'working'}
        if self.employee_id:
            attendvals.update({'employee_name': self.employee_id.name, 'employee_code': self.employee_id.code})
        if self.equipment_id:
            attendvals.update({'equipment_name': self.equipment_id.name, 'equipment_code': self.equipment_id.code})
        if self.mesline_id:
            attendvals['mesline_name'] = self.mesline_id.name
            empvals['mesline_id'] = self.mesline_id.id
        if self.workstation_id:
            empvals['workstation_id'] = self.workstation_id.id
            attendvals['workstation_name'] = self.workstation_id.name
            if not self.mesline_id and self.workstation_id.mesline_id:
                empvals['mesline_id'] = self.workstation_id.mesline_id.id
                attendvals.update({'mesline_id': self.workstation_id.mesline_id.id, 'mesline_name': self.workstation_id.mesline_id.name})
        if attendvals and len(attendvals) > 0:
            self.write(attendvals)
        if self.employee_id and empvals and len(empvals) > 0:
            self.employee_id.write(empvals)

    @api.one
    def action_done(self):
        self.write({'attendance_finish': fields.Datetime.now(), 'attend_done': True})
        self.employee_id.write({'workstation_id': False, 'state': 'leave'})


    @api.model
    def action_workstation_scanning(self, workstation_code, employee_code, equipment_code=None):
        """
        工控工位扫描员工卡
        :param workstation_code:
        :param employee_code:
        :param equipment_code:
        :return:
        """
        result = {'success': True, 'message': '', 'action': 'working'}
        if not employee_code:
            result.update({'success': False, 'message': u'您确认已经扫描了员工卡了吗？'})
            return result
        if not workstation_code:
            result.update({'success': False, 'message': u'您确认已经配置好工位的编码了吗？'})
            return result
        employee = self.env['aas.hr.employee'].search([('code', '=', employee_code)], limit=1)
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
        workstation = self.env['aas.mes.workstation'].search([('code', '=', workstation_code)], limit=1)
        if not workstation:
            result.update({'success': False, 'message': u'库位异常可能已删除，请仔细检查库位信息！'})
            return result
        attendancevals = {'employee_id': employee.id, 'workstation_id': workstation.id}
        if equipment_code:
            equipment = self.env['aas.equipment.equipment'].search([('code', '=', equipment_code)], limit=1)
            if not equipment:
                result.update({'success': False, 'message': u'设备异常，请仔细检查系统是否存在此设备！'})
                return result
            attendancevals['equipment_id'] = equipment.id
        self.env['aas.mes.work.attendance'].create(attendancevals)
        result['message'] = u"%s,您已经在工位%s上上岗了，加油工作吧！"% (employee.name, workstation.name)
        return result


# 生产考勤员
class AASMESAttendanceChecker(models.Model):
    _name = 'aas.mes.attendance.checker'
    _description = 'AAS MES Attendance Checker'
    _rec_name = 'checker_id'
    
    checker_id = fields.Many2one(comodel_name='res.users', string=u'考勤员', ondelete='restrict')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'生产线', ondelete='restrict')

    _sql_constraints = [
        ('uniq_checker', 'unique (checker_id)', u'请不要重复添加同一个考勤员！')
    ]

    @api.model
    def create(self, vals):
        record = super(AASMESAttendanceChecker, self).create(vals)
        record.action_after_create()
        return record

    @api.one
    def action_after_create(self):
        self.checker_id.write({
            'action_id': self.env.ref('aas_mes.aas_mes_attendance_scanner').id,
            'groups_id': [(4, self.env.ref('aas_mes.group_aas_attendance_checker').id, False)]
        })

    @api.multi
    def write(self, vals):
        oldcheckers, currentcheckerid = self.env['res.users'], False
        if vals.get('checker_id'):
            currentcheckerid = vals.get('checker_id', False)
            for record in self:
                oldcheckers |= record.checker_id
        result = super(AASMESAttendanceChecker, self).write(vals)
        if oldcheckers and len(oldcheckers) > 0:
            oldcheckers.write({
                'action_id': False,
                'groups_id': [(3, self.env.ref('aas_mes.group_aas_attendance_checker').id, False)]
            })
        if currentcheckerid:
            currentchecker = self.env['res.users'].browse(currentcheckerid)
            currentchecker.write({
                'action_id': self.env.ref('aas_mes.aas_mes_attendance_scanner').id,
                'groups_id': [(4, self.env.ref('aas_mes.group_aas_attendance_checker').id, False)]
            })
        return result

    @api.multi
    def unlink(self):
        users = self.env['res.users']
        for record in self:
            users |= record.checker_id
        result = super(AASMESAttendanceChecker, self).unlink()
        users.write({
            'action_id': False,
            'groups_id': [(3, self.env.ref('aas_mes.group_aas_attendance_checker').id, False)]
        })
        return result



#######################向导#################################

# 生产班次调整员工
class AASMESScheduleEmployeeWizard(models.TransientModel):
    _name = 'aas.mes.schedule.employee.wizard'
    _description = 'AAS MES Schedule Employee Wizard'

    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次', ondelete='cascade')
    sequence = fields.Integer(string=u'序号')
    work_start = fields.Float(string=u'开始时间', default=0.0)
    work_finish = fields.Float(string=u'结束时间', default=0.0)
    employee_lines = fields.One2many(comodel_name='aas.mes.schedule.employee.line.wizard', inverse_name='wizard_id', string=u'员工明细')

    @api.one
    def action_done(self):
        self.schedule_id.employee_lines.write({'schedule_id': False})
        if self.employee_lines and len(self.employee_lines) > 0:
            employeelist = self.env['aas.hr.employee']
            for temployee in self.employee_lines:
                employeelist |= temployee.employee_id
            employeelist.write({'schedule_id': self.schedule_id.id})



class AASMESScheduleEmployeeLineWizard(models.TransientModel):
    _name = 'aas.mes.schedule.employee.line.wizard'
    _description = 'AAS MES Schedule Employee Line Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.mes.schedule.employee.wizard', string=u'员工调整', ondelete='cascade')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', ondelete='restrict')
    employee_code = fields.Char(string=u'员工工号')

    _sql_constraints = [
        ('uniq_employee', 'unique (wizard_id, employee_id)', u'请不要重复添加同一个员工！')
    ]

    @api.onchange('employee_id')
    def action_change_employee(self):
        if self.employee_id:
            self.employee_code = self.employee_id.code
        else:
            self.employee_code = False

    @api.model
    def create(self, vals):
        if vals.get('employee_id', False) and not vals.get('employee_code', False):
            employee = self.env['aas.hr.employee'].browse(vals.get('employee_id'))
            vals['employee_code'] = employee.code
        return super(AASMESScheduleEmployeeLineWizard, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('employee_id', False) and not vals.get('employee_code', False):
            employee = self.env['aas.hr.employee'].browse(vals.get('employee_id'))
            vals['employee_code'] = employee.code
        return super(AASMESScheduleEmployeeLineWizard, self).write(vals)
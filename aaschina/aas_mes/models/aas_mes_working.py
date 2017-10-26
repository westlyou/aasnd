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
    active = fields.Boolean(string=u'是否有效', default=True, copy=False)
    station_type = fields.Selection(selection=[('scanner', u'扫描工位'), ('controller', u'工控工位')], string=u'工位类型', default='scanner', copy=False)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    employee_lines = fields.One2many(comodel_name='aas.mes.workstation.employee', inverse_name='workstation_id', string=u'员工清单')
    equipment_lines = fields.One2many(comodel_name='aas.mes.workstation.equipment', inverse_name='workstation_id', string=u'设备清单')

    _sql_constraints = [
        ('uniq_code', 'unique (code)', u'工位编码不可以重复！')
    ]

    @api.multi
    def name_get(self):
        return [(record.id, '%s[%s]' % (record.name, record.code)) for record in self]

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


class AASMESWorkstationEmployee(models.Model):
    _name = 'aas.mes.workstation.employee'
    _description = 'AAS MES Workstation Employee'

    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'库位', required=True, ondelete='cascade')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', required=True, ondelete='cascade')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', ondelete='restrict')
    action_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)

    _sql_constraints = [
        ('uniq_employee', 'unique (workstation_id, mesline_id, employee_id)', u'请不要重复添加员工！')
    ]



class AASMESWorkstationEquipment(models.Model):
    _name = 'aas.mes.workstation.equipment'
    _description = 'AAS MES Workstation Equipment'

    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'库位', required=True, ondelete='cascade')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', required=True, ondelete='cascade')
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='restrict')
    action_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)

    _sql_constraints = [
        ('uniq_equipment', 'unique (workstation_id, mesline_id, equipment_id)', u'请不要重复添加同一个设备！')
    ]

class AASEquipmentEquipment(models.Model):
    _inherit = 'aas.equipment.equipment'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')


    @api.multi
    def action_mesline_workstation(self):
        """
        向导，触发此方法弹出向导并进行业务处理
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.mes.equipment.workstation.wizard'].create({
            'equipment_id': self.id
        })
        view_form = self.env.ref('aas_mes.view_form_aas_mes_equipment_workstation_wizard')
        return {
            'name': u"产线工位",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.equipment.workstation.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }



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


    @api.constrains('mesline_id', 'employee_id')
    def action_checking_employee(self):
        meslineids, meslines = [], []
        attendancelist = self.env['aas.mes.work.attendance'].search([('employee_id', '=', self.employee_id.id)])
        if attendancelist and len(attendancelist) > 0:
            for tattendance in attendancelist:
                if tattendance.mesline_id.id not in meslineids:
                    meslineids.append(tattendance.mesline_id.id)
                    meslines.append(tattendance.mesline_id)
        if len(meslines) > 1:
            raise ValidationError(u'同一个员工不可以在多个产线同时开工！')





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
            if self.mesline_id.schedule_id:
                attendvals['schedule_id'] = self.mesline_id.schedule_id.id
                empvals['schedule_id'] = self.mesline_id.schedule_id.id
            empvals['mesline_id'] = self.mesline_id.id
        if self.workstation_id:
            attendvals['workstation_name'] = self.workstation_id.name
        if attendvals and len(attendvals) > 0:
            self.write(attendvals)
        self.employee_id.write({'state': 'working'})
        self.env['aas.mes.workstation.employee'].create({
            'workstation_id': self.workstation_id.id, 'mesline_id': self.mesline_id.id, 'employee_id': self.employee_id.id
        })

    @api.one
    def action_done(self):
        self.write({'attendance_finish': fields.Datetime.now(), 'attend_done': True})
        attendancecount = self.env['aas.mes.work.attendance'].search_count([('employee_id', '=', self.employee_id.id), ('attend_done', '=', False)])
        if attendancecount <= 0:
            self.employee_id.write({'state': 'leave'})


    @api.model
    def action_workstation_scanning(self, workstation_code, employee_code, equipment_code):
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
            if not equipment.mesline_id or not equipment.workstation_id:
                result.update({'success': False, 'message': u'设备还没有设置产线工位！'})
                return result
            if equipment.workstation_id.id != workstation.id:
                result.update({'success': False, 'message': u'设备和工位不匹配，请仔细检查！'})
                return result
            attendancevals.update({
                'equipment_id': equipment.id, 'mesline_id': equipment.mesline_id.id
            })
        self.env['aas.mes.work.attendance'].create(attendancevals)
        result['message'] = u"%s,您已经在工位%s上上岗了，加油工作吧！"% (employee.name, workstation.name)
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


# 设备产线和工位设置
class AASMESEquipmentWorkstationWizard(models.TransientModel):
    _name = 'aas.mes.equipment.workstation.wizard'
    _description = 'AAS MES Equipment Workstation Wizard'

    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='cascade')
    mesline_workstation = fields.Many2one(comodel_name='aas.mes.line.workstation', string=u'产线工位', ondelete='cascade')

    @api.one
    def action_done(self):
        if not self.mesline_workstation:
            raise UserError(u'请先设置好产线工位！')
        self.equipment_id.write({
            'mesline_id': self.mesline_workstation.mesline_id.id,
            'workstation_id': self.mesline_workstation.workstation_id.id
        })
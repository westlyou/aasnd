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

import logging

_logger = logging.getLogger(__name__)


class AASMESWorkstation(models.Model):
    _name = 'aas.mes.workstation'
    _description = 'AAS MES Workstation'

    name = fields.Char(string=u'名称', required=True, copy=False)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'生产线', ondelete='restrict')
    active = fields.Boolean(string=u'是否有效', default=True, copy=False)
    station_type = fields.Selection(selection=[('scanner', u'扫描工位'), ('controller', u'工控工位')], string=u'工位类型', default='scanner', copy=False)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    employee_lines = fields.One2many(comodel_name='aas.hr.employee', inverse_name='workstation_id', string=u'员工明细')
    employeelist = fields.Char(string=u'员工清单', compute='_compute_employeelist', store=True)

    equipment_lines = fields.One2many(comodel_name='aas.equipment.equipment', inverse_name='workstation_id', string=u'设备明细')
    equipmentlist = fields.Char(string=u'设备清单', compute='_compute_equipmentlist', store=True)

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


    _sql_constraints = [
        ('uniq_mesline_name', 'unique (mesline_id, name)', u'同一产线的工位名称不能重复！')
    ]

    @api.one
    def action_clear_employees(self):
        attendancelist = self.env['aas.mes.work.attendance'].search([('workstation_id', '=', self.id), ('attend_done', '=', False)])
        if attendancelist and len(attendancelist) > 0:
            for attendance in attendancelist:
                attendance.action_done()



class AASHREmployee(models.Model):
    _inherit = 'aas.hr.employee'

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
    attend_date = fields.Date(string=u'日期', default=fields.Date.today, copy=False)
    attendance_start = fields.Datetime(string=u'上岗时间', default=fields.Datetime.now, copy=False)
    attendance_finish = fields.Datetime(string=u'离岗时间', copy=False)
    attend_done = fields.Boolean(string=u'是否结束', default=False, copy=False)

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
        self.checker_id.write({'action_id': self.env.ref('aas_mes.aas_mes_attendance_scanner').id})

    @api.multi
    def unlink(self):
        users = self.env['res.users']
        for record in self:
            users |= record.checker_id
        result = super(AASMESAttendanceChecker, self).unlink()
        users.write({'action_id': False})
        return result





# 主工单 aas.mes.mainorder   子工单 aas.mes.workorder  工票 aas.mes.workticket
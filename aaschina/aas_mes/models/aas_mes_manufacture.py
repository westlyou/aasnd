# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-8-19 17:04
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


# 生产线
class AASMESLine(models.Model):
    _name = 'aas.mes.line'
    _description = 'AAS MES Line'

    name = fields.Char(string=u'名称')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    employees = fields.One2many(comodel_name='aas.hr.employee', inverse_name='mesline_id', string=u'员工清单')

    @api.multi
    def action_allocate_employee(self):
        """
        直接对班次分配员工
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.mes.line.allocate.wizard'].create({
            'mesline_id': self.id
        })
        view_form = self.env.ref('aas_mes.view_form_aas_mes_line_allocate_wizard')
        return {
            'name': u"员工分配",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.line.allocate.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }



# 生产班次
class AASMESSchedule(models.Model):
    _name = 'aas.mes.schedule'
    _description = 'AAS MES Schedule'

    name = fields.Char(string=u'名称', index=True)
    work_start = fields.Float(string=u'开始时间')
    work_finish = fields.Float(string=u'结束时间')
    work_time = fields.Float(string=u'工时', compute='_compute_work_time', store=True)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'生产线')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    employees = fields.One2many(comodel_name='aas.hr.employee', inverse_name='schedule_id', string=u'员工清单')

    @api.depends('work_start', 'work_finish')
    def _compute_work_time(self):
        for record in self:
            if not record.work_start and not record.work_finish:
                record.work_time = 0.0
            elif float_compare(record.work_finish, record.work_start, precision_rounding=0.0001) < 0:
                record.work_time = record.work_finish + 24.00 - record.work_start
            else:
                record.work_time = record.work_finish - record.work_start


    _sql_constraints = [
        ('uniq_name', 'unique (mesline_id, name)', u'同一产线的班次名称请不要重复！')
    ]

    @api.one
    @api.constrains('work_start', 'work_finish')
    def action_check_worktime(self):
        if float_compare(self.work_start, 0.0, precision_rounding=0.0001) < 0 or float_compare(self.work_start, 24.00, precision_rounding=0.0001) >= 0:
            raise ValidationError(u'开始时间请设置在00:00~23:59!')
        if float_compare(self.work_finish, 0.0, precision_rounding=0.0001) < 0 or float_compare(self.work_finish, 24.00, precision_rounding=0.0001) >= 0:
            raise ValidationError(u'结束时间请设置在00:00~23:59!')


    @api.multi
    def action_allocate_employee(self):
        """
        直接对班次分配员工
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.mes.schedule.allocate.wizard'].create({
            'schedule_id': self.id, 'mesline_id': self.mesline_id.id
        })
        view_form = self.env.ref('aas_mes.view_form_aas_mes_schedule_allocate_wizard')
        return {
            'name': u"员工分配",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.schedule.allocate.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }



class AASHRAttendance(models.Model):
    _inherit = 'aas.hr.attendance'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线')
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次')

    @api.model
    def action_attend(self, employee_id):
        attendance = super(AASHRAttendance, self).action_attend(employee_id)
        attendvals = {}
        if attendance.employee_id.mesline_id:
            attendvals['mesline_id'] = attendance.employee_id.mesline_id.id
        if attendance.employee_id.schedule_id:
            attendvals['schedule_id'] = attendance.employee_id.schedule_id.id
        if attendvals and len(attendvals) > 0:
            attendance.write(attendvals)
        return attendance


class AASHREmployee(models.Model):
    _inherit = 'aas.hr.employee'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线')
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次')
    meslines = fields.One2many(comodel_name='aas.mes.line.employee', inverse_name='employee_id', string=u'产线调整记录')

    @api.multi
    def action_allocate_mesline(self):
        """
        员工分配产线
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.mes.employee.allocate.mesline.wizard'].create({'employee_id': self.id})
        view_form = self.env.ref('aas_mes.view_form_aas_mes_employee_allocate_mesline_wizard')
        return {
            'name': u"分配产线",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.employee.allocate.mesline.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }





# 员工产线调整记录
class AASMESLineEmployee(models.Model):
    _name = 'aas.mes.line.employee'
    _description = 'AAS MES Line Employee'
    _order = 'id desc'

    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', ondelete='restrict')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次', ondelete='restrict')
    action_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    action_user = fields.Many2one(comodel_name='res.users', string=u'操作人', ondelete='restrict', default=lambda self: self.env.user)


    @api.model
    def create(self, vals):
        record = super(AASMESLineEmployee, self).create(vals)
        record.action_after_create()
        return record

    @api.one
    def action_after_create(self):
        empvals = {}
        if self.mesline_id:
            empvals['mesline_id'] = self.mesline_id.id
        if self.schedule_id:
            empvals['schedule_id'] = self.schedule_id.id
        if empvals and len(empvals) > 0:
            self.employee_id.write(empvals)


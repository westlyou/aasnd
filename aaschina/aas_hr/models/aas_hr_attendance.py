# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-8-19 15:48
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import pytz
import logging

_logger = logging.getLogger(__name__)

class AASHRAttendance(models.Model):
    _name = 'aas.hr.attendance'
    _description = 'AAS HR Attendance'
    _rec_name = 'employee_id'
    _order = 'id desc'

    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', index=True, ondelete='restrict')
    time_start = fields.Datetime(string=u'开始时间', default=fields.Datetime.now, copy=False)
    time_finish = fields.Datetime(string=u'结束时间', copy=False)
    work_time = fields.Float(string=u'工时', compute='_compute_worktime', store=True)
    work_date = fields.Char(string=u'工作日', compute='_compute_workdate', store=True, index=True)
    work_over = fields.Boolean(string=u'出勤结束', compute='_compute_worktime', store=True)

    @api.model
    def get_local_work_date(self, datetime, tz='Asia/Shanghai'):
        if not datetime:
            return ''
        temptime = fields.Datetime.from_string(datetime)
        timeutc = pytz.timezone('UTC').localize(temptime, is_dst=False)
        tempworktime = timeutc.astimezone(pytz.timezone(tz))
        return tempworktime.strftime('%Y-%m-%d')


    @api.depends('time_start', 'time_finish')
    def _compute_worktime(self):
        for record in self:
            if record.time_start and record.time_finish:
                temptimes = fields.Datetime.from_string(record.time_finish) - fields.Datetime.from_string(record.time_start)
                record.work_time = temptimes.total_seconds() / 3600.00
                record.work_over = True
            else:
                record.work_time = 0.00
                record.work_over = False


    @api.depends('time_start')
    def _compute_workdate(self):
        tz_name = self._context.get('tz') or self.env.user.tz
        for record in self:
            if record.time_start:
                record.work_date = self.get_local_work_date(record.time_start, tz=tz_name)
            else:
                record.work_date = ''

    @api.model
    def action_attend(self, employee_id):
        attendance = self.env['aas.hr.attendance'].search([('employee_id', '=', employee_id.id), ('work_over', '=', False)], limit=1)
        if not attendance:
            attendance = self.env['aas.hr.attendance'].create({'employee_id': employee_id.id, 'time_start': fields.Datetime.now()})
            employee_id.write({'state': 'working'})
        else:
            attendance.write({'time_finish': fields.Datetime.now()})
            employee_id.write({'state': 'leave'})
        return attendance



# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-11-10 16:22
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

from . import MESLINETYPE

import math
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)


class AASBaseCron(models.Model):
    _inherit = 'aas.base.cron'

    @api.model
    def action_thirty_minutes_cron(self):
        # 切换产线班次
        self.env['aas.mes.line'].action_switch_schedule()

# 生产线
class AASMESLine(models.Model):
    _name = 'aas.mes.line'
    _description = 'AAS MES Line'

    name = fields.Char(string=u'名称')
    line_type = fields.Selection(selection=MESLINETYPE, string=u'生产类型', default='station', copy=False)
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'当前班次')
    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'当前工单')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)
    employees = fields.One2many(comodel_name='aas.hr.employee', inverse_name='mesline_id', string=u'员工清单')
    location_production_id = fields.Many2one(comodel_name='stock.location', string=u'成品库位', ondelete='restrict')
    location_material_list = fields.One2many(comodel_name='aas.mes.line.material.location', inverse_name='mesline_id', string=u'原料库位')
    schedule_lines = fields.One2many(comodel_name='aas.mes.schedule', inverse_name='mesline_id', string=u'班次清单')
    workstation_lines = fields.One2many(comodel_name='aas.mes.line.workstation', inverse_name='mesline_id', string=u'工位清单')

    workdate = fields.Char(string=u'工作日期', copy=False)
    workday_start = fields.Datetime(string=u'当天开工时间', copy=False)
    workday_finish = fields.Datetime(string=u'当天完工时间', copy=False)
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'默认工位')
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'新序列号', ondelete='restrict', help=u'最近一次产出的序列号')

    _sql_constraints = [
        ('uniq_name', 'unique (name)', u'产线名称不可以重复！')
    ]

    @api.model
    def create(self, vals):
        if not vals.get('location_material_list', False):
            raise UserError(u'当前产线还未设置原料库位，请先设置原料库位信息！')
        if not vals.get('schedule_lines', False):
            raise UserError(u'当前产线还未设置班次信息，请先设置班次信息！')
        return super(AASMESLine, self).create(vals)


    @api.model
    def action_switch_schedule(self):
        """
        切换产线班次
        :return:
        """
        meslines = self.env['aas.mes.line'].search([])
        if not meslines or len(meslines) <= 0:
            return True
        for mesline in meslines:
            mesline.action_refresh()


    @api.one
    def action_refresh_schedule(self):
        if not self.schedule_lines or len(self.schedule_lines) <= 0:
            return
        refresh_flag, current_time = False, fields.Datetime.now()
        if not self.workdate:
            refresh_flag = True
        if not self.workday_finish:
            refresh_flag = True
        elif self.workday_finish < current_time:
            refresh_flag = True
        if not refresh_flag:
            return
        workday_start, workday_finish = False, False
        currenttime = fields.Datetime.to_timezone_time(current_time, 'Asia/Shanghai')
        workdate = fields.Datetime.to_timezone_string(current_time, 'Asia/Shanghai')[0:10]
        for schedule in self.schedule_lines:
            start_hour = int(math.floor(schedule.work_start))
            start_minutes = int(math.floor((schedule.work_start - start_hour) * 60))
            starttime = currenttime.replace(hour=start_hour, minute=start_minutes)
            finish_hour = int(math.floor(schedule.work_finish))
            finish_minutes = int(math.floor((schedule.work_finish - finish_hour) * 60))
            if schedule.work_finish >= schedule.work_start:
                finishtime = currenttime.replace(hour=finish_hour, minute=finish_minutes)
            else:
                temptime = currenttime + timedelta(days=1)
                finishtime = temptime.replace(hour=finish_hour, minute=finish_minutes)
            actual_start = fields.Datetime.to_utc_string(starttime, 'Asia/Shanghai')
            actual_finish = fields.Datetime.to_utc_string(finishtime, 'Asia/Shanghai')
            schedule.write({'actual_start': actual_start, 'actual_finish': actual_finish})
            if not workday_start or workday_start > actual_start:
                workday_start = actual_start
            if not workday_finish or workday_finish < actual_finish:
                workday_finish = actual_finish
        self.write({'workdate': workdate, 'workday_start': workday_start, 'workday_finish': workday_finish})


    @api.one
    def action_refresh(self):
        self.action_refresh_schedule()
        currenttime = fields.Datetime.now()
        searchdomain = [('actual_start', '<=', currenttime), ('actual_finish', '>=', currenttime)]
        searchdomain.append(('mesline_id', '=', self.id))
        schedule = self.env['aas.mes.schedule'].search(searchdomain, limit=1)
        if not schedule or not self.schedule_id or schedule.id != self.schedule_id.id:
            if self.workorder_id and self.workorder_id.isproducing:
                self.workorder_id.write({'isproducing': False})
            ordervals = {'workorder_id': False, 'schedule_id': False}
            if self.schedule_id:
                self.schedule_id.write({'state': 'break'})
            if schedule:
                ordervals['schedule_id'] = schedule.id
                schedule.write({'state': 'working'})
            self.write(ordervals)
            # 清理上一个班次用料
            self.action_clear_feeding(self.id)
            # 清理上一个班次员工上岗信息
            self.action_clear_employees(self.id)

    @api.model
    def loading_nextschedule(self, mesline):
        """加载下一个班次信息
        :param mesline:
        :return:
        """
        values = {'success': True, 'message': '', 'schedule': False}
        if not mesline.schedule_lines or len(mesline.schedule_lines) <= 0:
            values.update({'success': False, 'message': u'产线%s还未设置班次，请联系管理员设置班次信息！'% mesline.name})
            return values
        if not mesline.workdate:
            mesline.action_refresh_schedule()
        tschedule = mesline.schedule_lines[0]
        if mesline.schedule_id:
            tdomain = [('mesline_id', '=', mesline.id), ('sequence', '>', mesline.schedule_id.sequence)]
            ntschedule = self.env['aas.mes.schedule'].search(tdomain, limit=1)
            if ntschedule:
                values['schedule'] = {
                    'workdate': mesline.workdate,
                    'actual_start': ntschedule.actual_start, 'actual_finish': ntschedule.actual_finish
                }
                return values
        tempstart = fields.Datetime.from_string(tschedule.actual_start) + timedelta(days=1)
        tempfinish = fields.Datetime.from_string(tschedule.actual_finish) + timedelta(days=1)
        actual_start, actual_finish = fields.Datetime.to_string(tempstart), fields.Datetime.to_string(tempfinish)
        values['schedule'] = {
            'actual_start': actual_start, 'actual_finish': actual_finish, 'workdate': actual_start[0:10]
        }
        return values


    @api.model
    def action_clear_feeding(self, mesline_id):
        """
        清除当前产线的上料记录
        :param mesline_id:
        :return:
        """
        feedmateriallist = self.env['aas.mes.feedmaterial'].search([('mesline_id', '=', mesline_id)])
        if not feedmateriallist or len(feedmateriallist) <= 0:
            return True
        feedmateriallist.unlink()
        return True


    @api.model
    def action_clear_employees(self, mesline_id):
        """
        清空当前产线上的员工，并更新上岗记录信息
        :param mesline_id:
        :return:
        """
        tempdomain = [('mesline_id', '=', mesline_id), ('attend_done', '=', False)]
        attendancelist = self.env['aas.mes.work.attendance'].search(tempdomain)
        if attendancelist and len(attendancelist) > 0:
            attendancelist.action_done()
        # 更新并分割出勤明细
        attendancelines = self.env['aas.mes.work.attendance.line'].search(tempdomain)
        if attendancelines and len(attendancelines) > 0:
            attendancelines.action_split()




#产线原料库位
class AASMESLineMaterialLocation(models.Model):
    _name = 'aas.mes.line.material.location'
    _description = 'AAS MES Line Material Location'
    _rec_name = 'location_id'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')
    location_note = fields.Char(string=u'描述', copy=False)

    _sql_constraints = [
        ('uniq_location', 'unique (mesline_id, location_id)', u'同一产线的原料库位请不要重复！')
    ]


# 产线工位
class AASMESLineWorkstation(models.Model):
    _name = 'aas.mes.line.workstation'
    _description = 'AAS MES Line Workstation'
    _order = 'mesline_id,sequence'

    name = fields.Char(string=u'名称', compute='_compute_name', store=True)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade')
    sequence = fields.Integer(string=u'序号')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')

    _sql_constraints = [
        ('uniq_sequence', 'unique (mesline_id, sequence)', u'同一产线序号不能重复！'),
        ('uniq_workstation', 'unique (mesline_id, workstation_id)', u'同一产线库位不能重复！')
    ]

    @api.depends('mesline_id', 'workstation_id')
    def _compute_name(self):
        for record in self:
            if record.mesline_id and record.workstation_id:
                record.name = record.workstation_id.name + '[' + record.mesline_id.name + ']'
            else:
                record.name = False

    @api.model
    def create(self, vals):
        record = super(AASMESLineWorkstation, self).create(vals)
        record.action_after_create()
        return record

    @api.one
    def action_after_create(self):
        stationcount = self.env['aas.mes.line.workstation'].search_count([('mesline_id', '=', self.mesline_id.id)])
        if stationcount == 1:
            self.mesline_id.write({'workstation_id': self.workstation_id.id})
        else:
            self.mesline_id.write({'workstation_id': False})

    @api.multi
    def unlink(self):
        meslineids, meslines = [], []
        for record in self:
            mesline_id = record.mesline_id.id
            if mesline_id not in meslineids:
                meslineids.append(mesline_id)
                meslines.append(record.mesline_id)
        result = super(AASMESLineWorkstation, self).unlink()
        for mesline in meslines:
            if mesline.workstation_lines and len(mesline.workstation_lines) == 1:
                workstation = mesline.workstation_lines[0].workstation_id
                mesline.write({'workstation_id': workstation.id})
            else:
                mesline.write({'workstation_id': False})
        return result



# 员工产线调整记录
class AASMESLineEmployee(models.Model):
    _name = 'aas.mes.line.employee'
    _description = 'AAS MES Line Employee'
    _order = 'id desc'

    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', ondelete='restrict')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    action_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    action_user = fields.Many2one(comodel_name='res.users', string=u'操作人', ondelete='restrict', default=lambda self: self.env.user)


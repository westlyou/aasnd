# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-8-25 11:05
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

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
    @api.constrains('work_start', 'work_finish', 'sequence')
    def action_check_schedule(self):
        if float_compare(self.work_start, 0.0, precision_rounding=0.0001) < 0.0 or float_compare(self.work_start, 24.0, precision_rounding=0.0001) >= 0.0:
            raise ValidationError(u'班次开始时间只能在24小时以内！')
        if float_compare(self.work_finish, 0.0, precision_rounding=0.0001) < 0.0 or float_compare(self.work_finish, 24.0, precision_rounding=0.0001) >= 0.0:
            raise ValidationError(u'班次结束时间只能在24小时以内！')
        if float_compare(self.work_start, self.work_finish, precision_rounding=0.000001) == 0.0:
            raise ValidationError(u'无效设置，开始时间和结束时间不可以相同！')
        if float_compare(self.work_start, self.work_finish, precision_rounding=0.000001) > 0:
            scheduledomain = [('mesline_id', '=', self.mesline_id.id), ('sequence', '>', self.sequence)]
            schedulecount = self.env['aas.mes.schedule'].search_count(scheduledomain)
            if schedulecount > 0:
                raise ValidationError(u'无效设置，同一个产线只有最后一个班次的时间区间可以跨天！')
        prevdomain = [('mesline_id', '=', self.mesline_id.id), ('sequence', '<', self.sequence)]
        prevschedule = self.env['aas.mes.schedule'].search(prevdomain, order='sequence desc', limit=1)
        if prevschedule and float_compare(prevschedule.work_finish, self.work_start, precision_rounding=0.000001) > 0.0:
            raise ValidationError(u'无效设置，当前班次的开始时间不能小于上一个班次的结束时间！')
        nextdomain = [('mesline_id', '=', self.mesline_id.id), ('sequence', '>', self.sequence)]
        nextschedule = self.env['aas.mes.schedule'].search(nextdomain, order='sequence', limit=1)
        if nextschedule and float_compare(self.work_finish, nextschedule.work_start, precision_rounding=0.000001) > 0.0:
            raise ValidationError(u'无效设置，当前班次的结束时间不能大于下一个班次的开始时间！')


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
    def unlink(self):
        meslineids, meslines = []
        for record in self:
            if record.mesline_id.id not in meslineids:
                meslines.append(record.mesline_id)
                meslineids.append(record.mesline_id.id)
        result = super(AASMESSchedule, self).unlink()
        for mesline in meslines:
            schedulecount = self.env['aas.mes.schedule'].search_count([('mesline_id', '=', mesline.id)])
            if schedulecount <= 0:
                raise UserError(u'产线%s下至少要保留一个班次！'% mesline.name)
        return result




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
    badmode_lines = fields.One2many(comodel_name='aas.mes.badmode', inverse_name='workstation_id', string=u'不良模式')

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


    @api.model
    def action_list_employees(self, mesline_id, workstation_id):
        """
        获取指定产线工位上的员工清单
        :param mesline_id:
        :param workstation_id:
        :return:
        """
        employeelist = self.env['aas.mes.workstation.employee'].search([('mesline_id', '=', mesline_id), ('workstation_id', '=', workstation_id)])
        if not employeelist or len(employeelist) <= 0:
            employeelist = []
        return employeelist

    @api.model
    def action_get_employeestr(self, mesline_id, workstation_id):
        stationemployees = self.action_list_employees(mesline_id, workstation_id)
        if not stationemployees or len(stationemployees) <= 0:
            return False
        employeeids, employeelist = [], []
        for semployee in stationemployees:
            employee = semployee.employee_id
            if employee.id not in employeeids:
                employeeids.append(employee.id)
                employeelist.append(employee.name+'['+employee.code+']')
        return ','.join(employeelist)

    @api.model
    def action_list_equipments(self, mesline_id, workstation_id):
        """
        获取指定产线工位上的设备清单
        :param mesline_id:
        :param workstation_id:
        :return:
        """
        equipmentlist = self.env['aas.mes.workstation.equipment'].search([('mesline_id', '=', mesline_id), ('workstation_id', '=', workstation_id)])
        if not equipmentlist or len(equipmentlist) <= 0:
            equipmentlist = []
        return equipmentlist

    @api.model
    def action_get_equipmentstr(self, mesline_id, workstation_id):
        stationequipments = self.action_list_equipments(mesline_id, workstation_id)
        if not stationequipments or len(stationequipments) <= 0:
            return False
        equipmentids, equipmentlist = [], []
        for sequipment in stationequipments:
            equipment = sequipment.equipment_id
            if equipment.id not in equipmentids:
                equipmentids.append(equipment.id)
                equipmentlist.append(equipment.name+'['+equipment.code+']')
        return ','.join(equipmentlist)

    @api.model
    def get_employeelist(self, equipment_code):
        """
        根据设备编码获取设备上的员工信息
        :param equipment_code:
        :return:
        """
        values = {'success': True, 'message': '', 'employeelist': []}
        tequipment = self.env['aas.equipment.equipment'].search([('code', '=', equipment_code)], limit=1)
        if not tequipment:
            values.update({'success': False, 'message': u'请仔细检查系统是否存在此设备！'})
            return values
        if not tequipment.mesline_id or not tequipment.workstation_id:
            values.update({'success': False, 'message': u'当前设备可能还未设置产线工位！'})
            return values
        tempdomain = [('workstation_id', '=', tequipment.workstation_id.id), ('mesline_id', '=', tequipment.mesline_id.id)]
        tempdomain.append(('equipment_id', '=', tequipment.id))
        employeelist = self.env['aas.mes.workstation.employee'].search(tempdomain)
        if employeelist and len(employeelist) > 0:
            values['employeelist'] = [{
                'employee_id': temployee.employee_id.id,
                'employee_name': temployee.employee_id.name, 'employee_code': temployee.employee_id.code
            } for temployee in employeelist]
        return values




class AASMESWorkstationEmployee(models.Model):
    _name = 'aas.mes.workstation.employee'
    _description = 'AAS MES Workstation Employee'

    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'库位', required=True, ondelete='cascade')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', required=True, ondelete='cascade')
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='restrict')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', ondelete='restrict')
    action_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

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
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

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
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', ondelete='cascade')
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
        self.env['aas.mes.workstation.equipment'].create({
            'equipment_id': self.equipment_id.id,
            'mesline_id': self.mesline_workstation.mesline_id.id,
            'workstation_id': self.mesline_workstation.workstation_id.id
        })
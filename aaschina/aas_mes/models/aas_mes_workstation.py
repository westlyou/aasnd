# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-12-21 14:34
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


    @api.model
    def action_loading_badmodelist(self, equipment_code):
        values = {'success': True, 'message': '', 'badmodelist': []}
        tequipment = self.env['aas.equipment.equipment'].search([('code', '=', equipment_code)], limit=1)
        if not tequipment.mesline_id or not tequipment.workstation_id:
            values.update({'success': False, 'message': u'设备%s还未设置产线工位信息！'% equipment_code})
            return values
        workstation = tequipment.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'请仔细检查是否存在此工位！'})
            return values
        if not workstation.badmode_lines or len(workstation.badmode_lines) <= 0:
            values.update({'success': False, 'message': u'工位%s还未设置不良模式！'% workstation.name})
            return values
        values['badmodelist'] = [{'badmode_id': badmode.id, 'badmode_name': badmode.name} for badmode in workstation.badmode_lines]
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

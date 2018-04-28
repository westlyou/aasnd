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

STATIONTYPES = [('scanner', u'扫描工位'), ('controller', u'工控工位')]

class AASMESWorkstation(models.Model):
    _name = 'aas.mes.workstation'
    _description = 'AAS MES Workstation'

    name = fields.Char(string=u'名称', required=True, copy=False)
    code = fields.Char(string=u'编码', copy=False)
    shortname = fields.Char(string=u'简称', copy=False)
    barcode = fields.Char(string=u'条码', compute='_compute_barcode', store=True, index=True)
    active = fields.Boolean(string=u'是否有效', default=True, copy=False)
    ispublic = fields.Boolean(string=u'公共工位', default=False, copy=False)
    station_type = fields.Selection(selection=STATIONTYPES, string=u'工位类型', default='scanner', copy=False)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    employee_lines = fields.One2many(comodel_name='aas.mes.workstation.employee', inverse_name='workstation_id', string=u'员工清单')
    equipment_lines = fields.One2many(comodel_name='aas.mes.workstation.equipment', inverse_name='workstation_id', string=u'设备清单')
    badmode_lines = fields.One2many(comodel_name='aas.mes.workstation.badmode', inverse_name='workstation_id', string=u'不良模式')

    _sql_constraints = [
        ('uniq_code', 'unique (code)', u'工位编码不可以重复！')
    ]

    @api.multi
    def name_get(self):
        res = []
        for record in self:
            tempitems = []
            if record.name:
                tempitems.append(record.name)
            if record.code:
                tempitems += ['[', record.code, ']']
            res.append((record.id, ''.join(tempitems)))
        return res


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
        employeedomain = [('mesline_id', '=', mesline_id), ('workstation_id', '=', workstation_id)]
        employeelist = self.env['aas.mes.workstation.employee'].search(employeedomain)
        if not employeelist or len(employeelist) <= 0:
            employeelist = []
        return employeelist

    @api.model
    def action_get_employeestr(self, mesline_id, workstation_id):
        stationemployees = self.action_list_employees(mesline_id, workstation_id)
        if not stationemployees or len(stationemployees) <= 0:
            return ''
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
    def get_badmode_list(self, workstation_id, included=True):
        badmodelist = []
        workstation_badmodes = self.env['aas.mes.workstation.badmode'].search([('workstation_id', '=', workstation_id)])
        if workstation_badmodes and len(workstation_badmodes) > 0:
            badmodelist += [tbadmode.badmode_id for tbadmode in workstation_badmodes]
        if included:
            commonbadmodes = self.env['aas.mes.badmode'].search([('universal', '=', True)])
            if commonbadmodes and len(commonbadmodes) > 0:
                badmodelist += [badmode for badmode in commonbadmodes]
        return badmodelist


    @api.model
    def action_loading_badmodelist(self, equipment_code, included=False):
        values = {'success': True, 'message': '', 'badmodelist': []}
        tequipment = self.env['aas.equipment.equipment'].search([('code', '=', equipment_code)], limit=1)
        if not tequipment.mesline_id or not tequipment.workstation_id:
            values.update({'success': False, 'message': u'设备%s还未设置产线工位信息！'% equipment_code})
            return values
        workstation = tequipment.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'请仔细检查是否存在此工位！'})
            return values
        badmodelist = self.get_badmode_list(workstation.id, included)
        if not badmodelist or len(badmodelist) <= 0:
            values.update({'success': False, 'message': u'当前可能还未设置不良模式！'})
            return values
        values['badmodelist'] = [{
            'badmode_id': badmode.id, 'badmode_name': badmode.name, 'badmode_code': badmode.code
        } for badmode in badmodelist]
        return values




ACTIONTYPES = [('work', u'工作'), ('scan', u'扫描'), ('check', u'检测')]


class AASMESWorkstationEmployee(models.Model):
    _name = 'aas.mes.workstation.employee'
    _description = 'AAS MES Workstation Employee'

    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', required=True, ondelete='cascade')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', required=True, ondelete='cascade')
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='restrict')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', ondelete='restrict')
    action_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    action_type = fields.Selection(selection=ACTIONTYPES, string=u'操作类型', default='work', copy=False)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('uniq_employee', 'unique (workstation_id, mesline_id, employee_id, equipment_id)', u'请不要重复添加员工！')
    ]



class AASMESWorkstationEquipment(models.Model):
    _name = 'aas.mes.workstation.equipment'
    _description = 'AAS MES Workstation Equipment'

    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', required=True, ondelete='cascade')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', required=True, ondelete='cascade')
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='restrict')
    action_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('uniq_equipment', 'unique (workstation_id, mesline_id, equipment_id)', u'请不要重复添加同一个设备！')
    ]


class AASMESWorkstationBadmode(models.Model):
    _name = 'aas.mes.workstation.badmode'
    _description = 'AAS MES Workstation Badmode'

    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', required=True, ondelete='cascade')
    badmode_id = fields.Many2one(comodel_name='aas.mes.badmode', string=u'不良模式', ondelete='restrict')
    badmode_code = fields.Char(string=u'编码', copy=False)
    operate_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    operater_id = fields.Many2one('res.users', string=u'操作员', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('uniq_badmode', 'unique (workstation_id, badmode_id)', u'请不要重复添加同一个不良模式！')
    ]

    @api.onchange('badmode_id')
    def change_badmode(self):
        if not self.badmode_id:
            self.badmode_code = False
        else:
            self.badmode_code = self.badmode_id.code

    @api.model
    def create(self, vals):
        record = super(AASMESWorkstationBadmode, self).create(vals)
        record.action_after_create()
        return record


    @api.one
    def action_after_create(self):
        self.write({'badmode_code': self.badmode_id.code})
        if self.badmode_id.universal:
            self.badmode_id.write({'universal': False})


    @api.multi
    def unlink(self):
        badmodeids = []
        for record in self:
            if record.badmode_id.id not in badmodeids:
                badmodeids.append(record.badmode_id.id)
        result = super(AASMESWorkstationBadmode, self).unlink()
        for badmodeid in badmodeids:
            if self.env['aas.mes.workstation.badmode'].search_count([('badmode_id', '=', badmodeid)]) <= 0:
                badmode = self.env['aas.mes.badmode'].browse(badmodeid)
                badmode.write({'universal': True})
        return result




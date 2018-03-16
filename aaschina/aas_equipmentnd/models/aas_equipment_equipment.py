# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-3-15 13:45
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

class AASEquipmentCategoryParameter(models.Model):
    _name = 'aas.equipment.category.parameter'
    _description = 'AAS Equipment Category Parameter'

    field_id = fields.Many2one('ir.model.fields', string=u'数据字段',
                               domain=[('model', '=', 'aas.equipment.data.parameters'), ('ttype', 'in', ['float', 'char'])])
    field_name = fields.Char(string=u'字段名称', copy=False)
    param = fields.Char(string=u'设备参数')
    category_id = fields.Many2one(comodel_name='aas.equipment.category', string=u'类别', ondelete='cascade')
    company = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('uniq_field', 'unique (category_id, field_id)', u'请不要重复添加同一个名称！')
    ]

    @api.model
    def create(self, vals):
        record = super(AASEquipmentCategoryParameter, self).create(vals)
        if not vals.get('field_name', False):
            record.write({'field_name': record.field_id.name})
        return record


class AASEquipmentCategory(models.Model):
    _inherit = 'aas.equipment.category'

    parameter_lines = fields.One2many('aas.equipment.category.parameter', inverse_name='category_id', string=u'参数清单')


    @api.one
    def action_loading_parameters(self):
        if not self.parameter_lines or len(self.parameter_lines) <= 0:
            raise UserError(u'当前类别还未添加设备参数清单！')
        equipmentlist = self.env['aas.equipment.equipment'].search([('category', '=', self.id)])
        if equipmentlist and len(equipmentlist) > 0:
            paramlines = [(0, 0, {
                'field_id': tparam.field_id.id, 'field_name': tparam.field_name, 'param': tparam.param
            }) for tparam in self.parameter_lines]
            for tequipment in equipmentlist:
                if tequipment.parameter_lines and len(tequipment.parameter_lines) > 0:
                    continue
                tequipment.write({'parameter_lines': paramlines})








class AASEquipmentEquipmentParameter(models.Model):
    _name = 'aas.equipment.equipment.parameter'
    _description = 'AAS Equipment Equipment Parameter'

    field_id = fields.Many2one('ir.model.fields', string=u'数据字段',
                               domain=[('model', '=', 'aas.equipment.data.parameters'), ('ttype', 'in', ['float', 'char'])])
    field_name = fields.Char(string=u'字段名称', copy=False)
    param = fields.Char(string=u'参数名称')
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='cascade')
    company = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)


    @api.model
    def create(self, vals):
        record = super(AASEquipmentEquipmentParameter, self).create(vals)
        if not vals.get('field_name', False):
            record.write({'field_name': record.field_id.name})
        return record



class AASEquipmentEquipment(models.Model):
    _inherit = 'aas.equipment.equipment'

    parameter_lines = fields.One2many('aas.equipment.equipment.parameter', inverse_name='equipment_id', string=u'参数清单')

# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-3-15 14:07
"""

from odoo.addons.aas_redis.models.aas_redis import RedisModel

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class AASEquipmentData(models.Model, RedisModel):
    _inherit = 'aas.equipment.data'

    @api.model
    def create(self, vals):
        record = super(AASEquipmentData, self).create(vals)
        record.action_parameters()
        return record


    @api.one
    def action_parameters(self):
        equipment = self.env['aas.equipment.equipment'].search([('code', '=', self.app_code)], limit=1)
        if not equipment:
            return
        if not equipment.parameter_lines or len(equipment.parameter_lines) <= 0:
            return
        paramdatas, tempdata = {'edata_id': self.id}, self.str2json(self.data)
        if not tempdata or len(tempdata) <= 0:
            return
        for paramline in equipment.parameter_lines:
            tempval = tempdata.get(paramline.param, False)
            if not tempval:
                continue
            paramdatas[paramline.field_name] = tempval
        self.env['aas.equipment.data.parameters'].create(paramdatas)







class AASEquipmentDataParameters(models.Model):
    _name = 'aas.equipment.data.parameters'
    _description = 'AAS Equipment Data Parameters'

    edata_id = fields.Many2one(comodel_name='aas.equipment.data', string=u'数据', ondelete='restrict')

    param_energy = fields.Float(string=u'能量')
    param_power = fields.Float(string=u'功率')
    param_pressure = fields.Float(string=u'压力')
    param_time = fields.Float(string=u'时间')
    param_amplitude = fields.Float(string=u'振幅')

    param_gnd = fields.Char(string='GND')
    param_ntc1 = fields.Char(string='NTC1')
    param_ntc2 = fields.Char(string='NTC2')
    param_ntc3 = fields.Char(string='NTC3')
    param_ntc4 = fields.Char(string='NTC4')
    param_ntcgap = fields.Char(string='NTC_GAP')

    param_v11 = fields.Char(string='V1-1')
    param_v12 = fields.Char(string='V1-2')
    param_v21 = fields.Char(string='V2-1')
    param_v22 = fields.Char(string='V2-2')
    param_v31 = fields.Char(string='V3-1')
    param_v32 = fields.Char(string='V3-2')
    param_v41 = fields.Char(string='V4-1')
    param_v42 = fields.Char(string='V4-2')
    param_v51 = fields.Char(string='V5-1')
    param_v52 = fields.Char(string='V5-2')
    param_v61 = fields.Char(string='V6-1')
    param_v62 = fields.Char(string='V6-2')
    param_v71 = fields.Char(string='V7-1')
    param_v72 = fields.Char(string='V7-2')
    param_v81 = fields.Char(string='V8-1')
    param_v82 = fields.Char(string='V8-2')
    param_v91 = fields.Char(string='V9-1')
    param_v92 = fields.Char(string='V9-2')
    param_v101 = fields.Char(string='V10-1')
    param_v102 = fields.Char(string='V10-2')
    param_v111 = fields.Char(string='V11-1')
    param_v112 = fields.Char(string='V11-2')
    param_v121 = fields.Char(string='V12-1')
    param_v122 = fields.Char(string='V12-2')
    param_v131 = fields.Char(string='V13-1')
    param_v132 = fields.Char(string='V13-2')
    param_v141 = fields.Char(string='V14-1')
    param_v142 = fields.Char(string='V14-2')
    param_v151 = fields.Char(string='V15-1')
    param_v152 = fields.Char(string='V15-2')

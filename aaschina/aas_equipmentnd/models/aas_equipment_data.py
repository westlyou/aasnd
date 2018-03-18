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
from odoo.tools.sql import drop_view_if_exists

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



###############################################Report###################################

class AASEquipmentNDWeldData(models.Model):
    _auto = False
    _name = 'aas.equipment.ndweld.data'
    _description = 'AAS Equipment ND Weld Data'

    app_code = fields.Char(string=u'设备编码', index=True)
    operate_time = fields.Datetime(string=u'操作时间')
    data_type = fields.Char(string=u'数据类型')
    serial_number = fields.Char(string=u'序列号')
    station_code = fields.Char(string=u'工位编码')
    product_code = fields.Char(string=u'成品编码')
    staff_code = fields.Char(string=u'员工编码')

    param_energy = fields.Float(string=u'能量')
    param_power = fields.Float(string=u'功率')
    param_pressure = fields.Float(string=u'压力')
    param_time = fields.Float(string=u'时间')
    param_amplitude = fields.Float(string=u'振幅')


    def _select_sql(self):
        _select_sql = """
        SELECT aed.id AS id,
        aed.app_code AS app_code,
        aed.operate_time AS operate_time,
        aed.data_type AS data_type,
        aed.serial_number AS serial_number,
        aed.station_code AS station_code,
        aed.product_code AS product_code,
        aed.staff_code AS staff_code,
        aedp.param_energy AS param_energy,
        aedp.param_power AS param_power,
        aedp.param_pressure AS param_pressure,
        aedp.param_amplitude AS param_amplitude,
        aedp.param_time AS param_time
        FROM aas_equipment_data aed JOIN aas_equipment_data_parameters aedp ON aed.id=aedp.edata_id
        """
        return _select_sql


    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (self._table, self._select_sql()))



class AASEquipmentNDFunctiontestData(models.Model):
    _auto = False
    _name = 'aas.equipment.ndfunctiontest.data'
    _description = 'AAS Equipment ND Function Test Data'

    app_code = fields.Char(string=u'设备编码', index=True)
    operate_time = fields.Datetime(string=u'操作时间')
    data_type = fields.Char(string=u'数据类型')
    serial_number = fields.Char(string=u'序列号')
    station_code = fields.Char(string=u'工位编码')
    product_code = fields.Char(string=u'成品编码')
    staff_code = fields.Char(string=u'员工编码')

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


    def _select_sql(self):
        _select_sql = """
        SELECT aed.id AS id,
        aed.app_code AS app_code,
        aed.operate_time AS operate_time,
        aed.data_type AS data_type,
        aed.serial_number AS serial_number,
        aed.station_code AS station_code,
        aed.product_code AS product_code,
        aed.staff_code AS staff_code,

        aedp.param_gnd AS param_gnd,
        aedp.param_ntc1 AS param_ntc1,
        aedp.param_ntc2 AS param_ntc2,
        aedp.param_ntc3 AS param_ntc3,
        aedp.param_ntc4 AS param_ntc4,
        aedp.param_ntcgap AS param_ntcgap,
        aedp.param_v11 AS param_v11,
        aedp.param_v12 AS param_v12,
        aedp.param_v21 AS param_v21,
        aedp.param_v22 AS param_v22,
        aedp.param_v31 AS param_v31,
        aedp.param_v32 AS param_v32,
        aedp.param_v41 AS param_v41,
        aedp.param_v42 AS param_v42,
        aedp.param_v51 AS param_v51,
        aedp.param_v52 AS param_v52,
        aedp.param_v61 AS param_v61,
        aedp.param_v62 AS param_v62,
        aedp.param_v71 AS param_v71,
        aedp.param_v72 AS param_v72,
        aedp.param_v81 AS param_v81,
        aedp.param_v82 AS param_v82,
        aedp.param_v91 AS param_v91,
        aedp.param_v92 AS param_v92,
        aedp.param_v101 AS param_v101,
        aedp.param_v102 AS param_v102,
        aedp.param_v111 AS param_v111,
        aedp.param_v112 AS param_v112,
        aedp.param_v121 AS param_v121,
        aedp.param_v122 AS param_v122,
        aedp.param_v131 AS param_v131,
        aedp.param_v132 AS param_v132,
        aedp.param_v141 AS param_v141,
        aedp.param_v142 AS param_v142,
        aedp.param_v151 AS param_v151,
        aedp.param_v152 AS param_v152
        FROM aas_equipment_data aed JOIN aas_equipment_data_parameters aedp ON aed.id=aedp.edata_id
        """
        return _select_sql


    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (self._table, self._select_sql()))

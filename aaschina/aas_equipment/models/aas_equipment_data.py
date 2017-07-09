# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-9 13:22
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
    _name = 'aas.equipment.data'
    _redis_name = 'aasequipment'
    _description = 'AAS Equipment Data'
    _rec_name = 'app_code'

    app_code = fields.Char(string=u'设备编码')
    app_secret = fields.Integer(string=u'秘钥')
    staff_code = fields.Char(string=u'员工编码')
    station_code = fields.Char(string=u'工位编码')
    job_code = fields.Char(string=u'工单编码')
    product_code = fields.Char(string=u'产品编码')
    operate_time = fields.Datetime(string=u'操作时间')
    timstamp = fields.Datetime(string=u'传输时间')
    data_type = fields.Selection(selection=[('D', 'Debug'), ('P', 'Production'), ('T', 'Test')], string=u'数据类型')
    data = fields.Text(string=u'数据集')

    @api.model
    def action_persist_data(self):
        """
        将redis中缓存的生产设备信息持久化到pg中
        :return:
        """
        loop = True
        while loop:
            try:
                record = self.redis_pop()
            except UserError, ue:
                loop = False
            if not loop:
                break
            if not record:
                continue
            recorddata = ''
            if record['data']:
                recorddata = record['data']
                if isinstance(record['data'], dict):
                    recorddata = self.json2str(record['data'])
            self.env['aas.equipment.data'].create({
                'app_code': record['app_code']+'01', 'app_secret': record['app_secret'], 'staff_code': record['staff_code'],
                'job_code': record['job_code'], 'product_code': record['product_code'], 'station_code': record['station_code'],
                'operate_time': '2017-07-09 14:29:11',
                'timstamp': '2017-07-09 14:29:50',
                # 'timstamp': fields.Datetime.to_string(fields.Datetime.context_timestamp(self, record.timstamp)),
                'data_type': record['data_type'], 'data': recorddata
            })


    @api.one
    def action_push_data(self):
        record = {
            'app_code': 'EQ0001', 'app_secret': 121232423, 'staff_code': 'EM0002', 'job_code': '1535530',
            'product_code': 'A-1743', 'station_code': 'ST00006', 'operate_time': '2017-07-09 14:29:50',
            'timstamp': '2017-07-09 14:29:50', 'data_type': 'P', 'data': {'Tempresure': 337.5, 'Presdf': 224}
        }
        self.redis_push(record)





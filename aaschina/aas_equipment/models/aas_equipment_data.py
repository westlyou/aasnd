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

import json
import pytz
import logging

_logger = logging.getLogger(__name__)

class AASEquipmentData(models.Model, RedisModel):
    _name = 'aas.equipment.data'
    _redis_name = 'aasequipment'
    _description = 'AAS Equipment Data'
    _rec_name = 'app_code'
    _order = 'operate_time desc'
    _checking = False

    data = fields.Text(string=u'设备参数')
    app_code = fields.Char(string=u'设备编码', index=True)
    app_secret = fields.Integer(string=u'秘钥')
    timstamp = fields.Datetime(string=u'传输时间')
    operate_time = fields.Datetime(string=u'操作时间')
    data_type = fields.Char(string=u'数据类型')

    lot_code = fields.Char(string=u'批次号')
    serial_number = fields.Char(string=u'序列号')
    station_code = fields.Char(string=u'工位编码')
    product_code = fields.Char(string=u'成品编码')
    job_id = fields.Integer(string=u'主工单')
    job_code = fields.Char(string=u'主工单号')
    workorder_id = fields.Integer(string=u'子工单')
    workorder_code = fields.Char(string=u'子工单号')
    staff_code = fields.Char(string=u'员工编码')
    staff_name = fields.Char(string=u'员工名称')
    material_info = fields.Text(string=u'原料信息')

    @api.model
    def localtimestr2utctimestr(self, localtimestr):
        if not localtimestr:
            return False
        tz_name = self.env.context.get('tz') or self.env.user.tz or 'Asia/Shanghai'
        temptime = pytz.timezone(tz_name).localize(fields.Datetime.from_string(localtimestr), is_dst=False)
        return fields.Datetime.to_string(temptime.astimezone(pytz.timezone('UTC')))

    @api.model
    def localtimestr2utctime(self, localtimestr):
        if not localtimestr:
            return False
        tz_name = self.env.context.get('tz') or self.env.user.tz or 'Asia/Shanghai'
        temptime = pytz.timezone(tz_name).localize(fields.Datetime.from_string(localtimestr), is_dst=False)
        return temptime.astimezone(pytz.timezone('UTC'))


    @api.model
    def localtime2utctimestr(self, localtime):
        if not localtime:
            return False
        tz_name = self.env.context.get('tz') or self.env.user.tz or 'Asia/Shanghai'
        temptime = pytz.timezone('UTC').localize(localtime, is_dst=False)
        return fields.Datetime.to_string(temptime.astimezone(pytz.timezone(tz_name)))



    @api.model
    def action_persist_data(self):
        """
        将redis中缓存的生产设备信息持久化到pg中
        :return:
        """
        if self._checking:
            _logger.info(u"Redis缓存正在出队，放弃本次操作；当前时间：" % fields.Datetime.now())
            return
        self._checking, loop = True, True
        while loop:
            try:
                record = self.redis_pop()
            except UserError, ue:
                loop = False
                _logger.info(ue.name)
                continue
            if not record or not isinstance(record, dict):
                continue
            datavals = {'data': False, 'app_code': record.get('app_code', False)}
            datavals.update({'app_secret': record.get('app_secret', False), 'data_type': record.get('data_type', False)})
            timstamp, operate_time = record.get('timstamp', False),  record.get('operate_time', False)
            if timstamp:
                if isinstance(timstamp, (str, unicode)):
                    datavals['timstamp'] = self.localtimestr2utctimestr(timstamp)
                else:
                    datavals['timstamp'] = self.localtime2utctimestr(timstamp)
            if operate_time:
                if isinstance(operate_time, (str, unicode)):
                    datavals['operate_time'] = self.localtimestr2utctimestr(operate_time)
                else:
                    datavals['operate_time'] = self.localtime2utctimestr(operate_time)
            appdata = record.get('data', False)
            if appdata and isinstance(appdata, dict):
                datavals.update({
                    'data': self.json2str(appdata), 'station_code': record.get('station_code', False),
                    'product_code': record.get('product_code', False), 'job_id': record.get('job_id', False),
                    'job_code': record.get('job_code', False), 'workorder_id': record.get('workorder_id', False),
                    'workorder_code': record.get('workorder_code', False), 'staff_code': record.get('staff_code', False),
                    'staff_name': record.get('staff_name', False), 'material_info': record.get('material_info', False),
                    'serial_number': record.get('serial_number', False), 'lot_code': record.get('lot_code', False)
                })
            self.env['aas.equipment.data'].create(datavals)
        # 循环结束，更新标志
        self._checking = False





    @api.one
    def action_push_data(self):
        record = {
            'app_code': 'ND20160006', 'app_secret': 0,
            'timstamp': '2018-03-16 12:00:00', 'data_type': 'Production', 'operate_time': '2018-03-16 12:00:00',
            'job_code': '20180314123338', 'product_code': 'CTTS-301309',  'station_code': 'TW_001',
            'staff_code': 'NC00000128', 'serial_number': '82010000125218114800290',
            'data': {
                u"操作时间": "2018-3-15  12:00:21", "GND": "0.053729", "V15-1": "0.012000", "mdc_state": 0,
                "V3-1": "0.012000", u"员工编码": "ND20160022", "NTC4": "11220.186523", "NTC3": "11161.617969",
                "NTC2": "11265.098242", "NTC1": "11329.813281", "\u6e29\u5ea6": "22.913302", "V9-1": "0.544803",
                "V9-2": "0.000000", "NTC_GAP": "168.195312", "V12-1": "0.012000", "V12-2": "0.000000",
                "V15-2": "0.000000", "V10-2": "0.000000", "V10-1": "0.012000", "V2-2": "0.000000", "V2-1": "0.012000",
                "\u6d4b\u8bd5\u6b21\u6570": " ", "V11-2": "0.000000", "V14-2": "0.000000", "V14-1": "0.235593",
                "V11-1": "0.012000", "V3-2": "0.000000", "V13-1": "2.162474", "V13-2": "0.000000", "VO": "0.093160",
                "V4-1": "0.012000", "V4-2": "0.000000", "\u9694\u79bb\u677f\u53f7\u7801": "82010000125218114800290",
                "V7-2": "0.000000", "V7-1": "0.012000", "PWR": "0.012000", "V6-2": "0.000000", "V6-1": "0.012000",
                "V1-1": "0.012000", "\u64cd\u4f5c\u5458": "NC00000128", "V5-1": "0.227345", "V5-2": "0.000000",
                "\u603b\u7ed3\u679c": "PASS", "V8-1": "0.148081", "V1-2": "0.000000", "V8-2": "0.000000",
                "Power": "620", "Amplitude": "50", "Energy": "120", "Time1": "0.26", "Pressure": "40.0"
            }
        }
        self.redis_push(record)





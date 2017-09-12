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

    data = fields.Text(string=u'数据集')
    app_code = fields.Char(string=u'设备编码')
    app_secret = fields.Integer(string=u'秘钥')
    timstamp = fields.Datetime(string=u'传输时间')
    operate_time = fields.Datetime(string=u'操作时间')
    data_type = fields.Selection(selection=[('D', 'Debug'), ('P', 'Production'), ('T', 'Test')], string=u'数据类型')

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
    def utctimestr2localtimestr(self, timestr):
        if not timestr:
            return False
        tz_name = self.env.context.get('tz') or self.env.user.tz or 'Asia/Shanghai'
        temptime = pytz.timezone('UTC').localize(fields.Datetime.from_string(timestr), is_dst=False)
        return fields.Datetime.to_string(temptime.astimezone(pytz.timezone(tz_name)))

    @api.model
    def localtimestr2utctimestr(self, localtimestr):
        if not localtimestr:
            return False
        tz_name = self.env.context.get('tz') or self.env.user.tz or 'Asia/Shanghai'
        temptime = pytz.timezone(tz_name).localize(fields.Datetime.from_string(localtimestr), is_dst=False)
        return fields.Datetime.to_string(temptime.astimezone(pytz.timezone('UTC')))


    @api.model
    def utctime2localtimestr(self, utctime):
        if not utctime:
            return False
        tz_name = self.env.context.get('tz') or self.env.user.tz or 'Asia/Shanghai'
        temptime = pytz.timezone('UTC').localize(utctime, is_dst=False)
        return fields.Datetime.to_string(temptime.astimezone(pytz.timezone(tz_name)))

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
                if not record:
                    continue
                record = json.loads(record.decode('raw_unicode-escape'))
            except UserError, ue:
                loop = False
                continue
            except Exception, te:
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
            'app_code': u'Temp-S-高温油槽-39', 'app_secret': 121232423,
            'timstamp': '2017-09-10 14:00:00', 'data_type': 'P', 'operate_time': '2017-09-10 14:00:00',
            'job_code': '1535530', 'product_code': 'A-1743', 'station_code': 'ST00006', 'staff_code': 'EM0002',
            'data': {'Tempresure': 337.5, 'Presdf': 224}
        }
        self.redis_push(record)





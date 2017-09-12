# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-8 14:08
"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import json
import logging
from datetime import date, datetime
#https://pypi.python.org/pypi/redis/
import redis


from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)


class DatetimeJSONEncoder(json.JSONEncoder):

    def default(self, tempdatetime):
        if isinstance(tempdatetime, date):
            return fields.Date.to_string(tempdatetime)
        elif isinstance(tempdatetime, datetime):
            return fields.Datetime.to_string(tempdatetime)
        else:
            return json.JSONEncoder.default(self, tempdatetime)



class RedisBase(object):

    _redis_name = ""
    _redis_record = None

    def get_redis(self):
        if not self._redis_record :
            self._redis_record = self.env['aas.base.redis'].get_redis(self._redis_name)
        return self._redis_record

    def json2str(self, value):
        if isinstance(value, str):
            pass
        else:
            value = json.dumps(value, cls=DatetimeJSONEncoder)
        return value


    def str2json(self, value):
        if isinstance(value, dict):
            pass
        else:
            value = json.loads(value)
        return value


class RedisModel(RedisBase):

    def redis_set(self, value):
        name = self._redis_name
        redis = self.get_redis()
        return redis.set_value(name, value)


    def redis_get(self):
        name = self._redis_name
        redis = self.get_redis()
        return redis.get_value(name)

    def redis_push(self, value):
        name = self._redis_name
        redis = self.get_redis()
        return redis.push_value(name, value)

    def redis_pop(self):
        name = self._redis_name
        redis = self.get_redis()
        return redis.pop_value(name)





class AASBaseRedis(models.Model):
    _name = 'aas.base.redis'
    _description = "AAS Base Redis"

    _redis_pool = None



    name = fields.Char(string=u'名称', compute='_compute_name', store=True)
    code = fields.Char(string=u'编码', required=True, copy=False)
    prefix = fields.Char(string=u'前缀', required=True, copy=False)
    host = fields.Char(u'主机', required=True, default="127.0.0.1")
    port = fields.Integer(u'端口', required=True, default=6379)
    password = fields.Char(u'密码')
    db = fields.Integer(u'库号', required=True, default=0)
    comment = fields.Text(u'备注')


    _sql_constraints = [
        ('uniq_code', 'unique(code)', u'缓存编码必须唯一！'),
    ]


    @api.depends('prefix', 'code')
    def _compute_name(self):
        for record in self:
            record.name = record.prefix+record.code


    def _get_connection_pool(self):
        if not self._redis_pool:
            self._redis_pool = redis.ConnectionPool(host=self.host, port=self.port, password=self.password, db=self.db)
        return self._redis_pool


    def _get_pool_redis(self):
        # redis.Redis(connection_pool=self._get_connection_pool(), charset='UTF-8')
        return redis.Redis(connection_pool=self._get_connection_pool())


    def _get_strict_redis(self):
        #redis://[:password]@localhost:6379/0
        #rediss://[:password]@localhost:6379/0
        #unix://[:password]@/path/to/socket.sock?db=0
        return redis.StrictRedis(host=self.host, port=self.port, password=self.password, db=self.db)


    @api.model
    def get_redis(self, key):
        record = self.search([('name', '=', key)], limit=1)
        if record:
            return record
        else:
            raise UserError(u"无对应Redis缓存名称配置")


    @api.multi
    def connect_test(self):
        self.ensure_one()
        try:
            redis = self._get_strict_redis()
            _logger.info("Redis Test Instance: %s" % redis)
            result = redis.info()
            _logger.info("Redis Test Info: %s" % result)
        except Exception, e:
            _logger.error("Redis Test Error: %s" % e)
            raise UserError(u"Redis连接测试错误，请检查配置：%s" % e)
        raise UserError(u"Redis连接测试成功：%s" % result)

    def json_dumps(self, value):
        if isinstance(value, str):
            pass
        else:
            value = json.dumps(value, cls=DatetimeJSONEncoder)
        return value


    def get_value(self, name):
        rconnection = self._get_pool_redis()
        value = rconnection.get(name)
        if value:
                value = value.decode('raw_unicode-escape')
        _logger.info("Redis Get Key(%s) : Value(%s)" % (name, value))
        return value


    def set_value(self, name, value):
        rconnection = self._get_pool_redis()
        tvalue = self.json_dumps(value)
        _logger.info("Redis Set Key(%s) Value(%s)" % (name, tvalue))
        try:
            result = rconnection.set(name, tvalue)
        except Exception, e:
            _logger.error("Redis Error: %s" % e)
            raise UserError(u"Redis Set错误，请检查配置")
        _logger.info("Redis Set Key(%s) Ret(%s) : Value(%s)" % (name, result, tvalue))
        return result


    def push_value(self, name, value, left=True):
        rconnection = self._get_pool_redis()
        tvalue = self.json_dumps(value)
        _logger.info("Redis Put Key(%s) Value(%s)" % (name, tvalue))
        try:
            if left:
                result = rconnection.lpush(name, tvalue)
            else:
                result = rconnection.rpush(name, tvalue)
        except Exception, e:
            _logger.error("Redis Error: %s" % e)
            raise UserError(u"Redis Put错误，请检查配置")
        _logger.info("Redis Put Key(%s) Ret(%s) : Value(%s)" % (name, result, tvalue))
        return result


    def pop_value(self, name, right=True):
        rconnection = self._get_pool_redis()
        _logger.info("Redis Pop Key(%s)" % name)
        try:
            tvalue = rconnection.rpop(name) if right else rconnection.lpop(name)
            _logger.info("Redis Pop Key(%s) Value(%s)" % (name, tvalue))
            if tvalue:
                tvalue = tvalue.decode('raw_unicode-escape')
            result = json.loads(tvalue)
        except Exception, e:
            _logger.error("Redis Error: %s" % e)
            raise UserError(u"Redis Pop错误，请检查配置")
        _logger.info("Redis Pop Key(%s) Ret(%s)" % (name, result))
        return result




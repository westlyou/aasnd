# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-8 14:08
"""



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

    _redis_type = ""
    _redis_record = None

    def get_redis(self):
        if not self._redis_record :
            self._redis_record = self.env['aas.base.redis'].get_redis(self._redis_type)
        return self._redis_record


class RedisModel(RedisBase):

    _redis_name = ""

    def redis_message_send(self, type, value):
        name = self._redis_name
        redis = self.get_redis()
        message = {'type': type, 'value': value}
        return redis.put_value(message, name)

    def redis_set(self, value, key=None):
        name = self._redis_name
        if key:
            name = "%s%s" % (name, key)
        redis = self.get_redis()
        return redis.set_value(value, name)


    def redis_get(self, key=None):
        name = self._redis_name
        if key:
            name = "%s%s" % (name, key)
        redis = self.get_redis()
        return redis.get_value(name)




class AASBaseRedis(models.Model):
    _name = 'aas.base.redis'
    _description = "AAS Base Redis"
    _rec_name = "type"
    _redis_pool = None

    type = fields.Char(u'类型', required=True, copy=False, help="label equipment")

    host = fields.Char(u'主机', required=True, default="localhost")
    port = fields.Integer(u'端口', required=True, default=6379)
    password = fields.Char(u'密码')
    db = fields.Integer(u'库号', required=True, default=0)
    name = fields.Char(u'名称前缀', required=True)

    comment = fields.Text(u'备注')

    _sql_constraints = [
        ('type_uniq', 'unique(type)', u'缓存类型必须唯一'),
    ]


    def _get_connection_pool(self):
        if not self._redis_pool:
            self._redis_pool = redis.ConnectionPool(host=self.host, port=self.port, password=self.password, db=self.db)
        return self._redis_pool


    def _get_pool_redis(self):
        return redis.Redis(connection_pool=self._get_connection_pool())


    def _get_strict_redis(self):
        #redis://[:password]@localhost:6379/0
        #rediss://[:password]@localhost:6379/0
        #unix://[:password]@/path/to/socket.sock?db=0
        return redis.StrictRedis(host=self.host, port=self.port, password=self.password, db=self.db)

    def _get_key(self, name):
        key = self.name
        if name:
            key = "%s%s" % (key, name)
        return key


    @api.multi
    @api.depends('type', 'name')
    def name_get(self):
        return [(record.id, u"%s（%s）" % (record.type, record.name)) for record in self]


    @api.one
    def copy(self, default=None):
        default = dict(default or {}, type=_("%s (Copy)") % self.type)
        return super(AASBaseRedis, self).copy(default=default)


    @api.model
    def get_redis(self, type):
        record = self.search([('type', '=', type)], limit=1)
        if record:
            return record;
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
        except Exception,e:
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
        r = self._get_pool_redis()
        key = self._get_key(name)
        value = r.get(key)
        _logger.info("Redis Get Key(%s) : Value(%s)" % (key, value))
        return value

    def set_value(self, value, name):
        r = self._get_pool_redis()
        key = self._get_key(name)
        val = self.json_dumps(value)
        _logger.info("Redis Set Key(%s) Value(%s)" % (key, val))
        try:
            ret = r.set(key, val)
        except Exception,e:
            _logger.error("Redis Error: %s" % e)
            raise UserError(u"Redis Set错误，请检查配置")
        _logger.info("Redis Set Key(%s) Ret(%s) : Value(%s)" % (key, ret, val))
        return ret

    def put_value(self, value, name):
        r = self._get_pool_redis()
        key = self._get_key(name)
        val = self.json_dumps(value)
        _logger.info("Redis Put Key(%s) Value(%s)" % (key, val))
        try:
            ret = r.lpush(key, val)
        except Exception,e:
            _logger.error("Redis Error: %s" % e)
            raise UserError(u"Redis Put错误，请检查配置")
        _logger.info("Redis Put Key(%s) Ret(%s) : Value(%s)" % (key, ret, val))
        return ret

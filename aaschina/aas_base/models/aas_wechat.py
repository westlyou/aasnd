# -*- coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-9 18:16
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class AASWechatENApplication(models.Model):
    _name = "aas.wechat.enapplication"
    _rec_name = "name"
    _description = u"安费诺企业号应用"

    name = fields.Char(string=u'应用名称', required=True)
    description = fields.Text(string=u'应用介绍')
    agent_id = fields.Integer(string=u'应用序号', required=True, help=u'应用序号，创建企业号应用时微信系统自动生成')
    app_code = fields.Char(string=u'应用代码', required=True)
    home_url = fields.Char(string=u'主页地址', required=True)
    callback_url = fields.Char(string=u'回调URL')
    app_token = fields.Char(string="Token")
    encoding_aes_key = fields.Char(string='EncodingAESKey')
    corp_id = fields.Char(string='CorpID', required=True)
    role_secret = fields.Char(string=u'权限组密钥', required=True, help=u'在微信企业号中为每一个应用创建一个权限分组，此字段即为当前应用对应分组密钥')
    user_id = fields.Many2one('res.users', string=u'创建人', ondelete='set null')
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('uniq_aas_wechat_enapplication_appcode', 'unique (app_code)', u'应用代码不能重复！')
    ]

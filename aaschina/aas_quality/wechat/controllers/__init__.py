# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-1-3 21:32
"""

import logging
import datetime
import time, random, string

from odoo import http, fields
from odoo.http import request
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.enterprise.client import WeChatClient

quality_crypto = None
quality_client = None

_logger = logging.getLogger(__name__)

class AASWechatQualityController(http.Controller):

    def __init__(self):
        aas_application = request.env['aas.wechat.enapplication'].sudo().search([('app_code', '=', 'aas_quality')], limit=1)
        self.TOKEN = aas_application.app_token
        self.EncodingAESKey = aas_application.encoding_aes_key
        self.CorpId = aas_application.corp_id
        self.RoleSecret = aas_application.role_secret

        global quality_crypto
        quality_crypto = WeChatCrypto(self.TOKEN, self.EncodingAESKey, self.CorpId)
        global quality_client
        quality_client = WeChatClient(self.CorpId, self.RoleSecret)


    @http.route('/aaswechat/quality', type='http', auth="user", methods=['GET', 'POST'])
    def aas_wechat_quality_index(self, **kwargs):
        values = request.params.copy()
        values['user'] = request.env.user.name
        return request.render('aas_quality.wechat_quality_index', values)


    @http.route('/aaswechat/quality/scaninit', type='json', auth="user")
    def aas_wechat_quality_scaninit(self, access_url=None):
        cticket = quality_client.jsapi.get_jsapi_ticket()
        curl = access_url
        cnoncestr = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(15))
        ctimestamp = int(time.time())
        csignature = quality_client.jsapi.get_jsapi_signature(noncestr=cnoncestr, ticket=cticket, timestamp=ctimestamp, url=curl)
        return {'debug': False, 'appId': self.CorpId, 'timestamp': ctimestamp, 'nonceStr': cnoncestr, 'signature': csignature, 'jsApiList': ['scanQRCode']}


import aas_quality

# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-10-7 16:45
"""

import logging
import werkzeug
import time, random, string

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError, ValidationError
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.enterprise.client import WeChatClient

logger = logging.getLogger(__name__)


mes_crypto, mes_client = None, None

class AASMESIndexWechatController(http.Controller):

    def __init__(self):
        appdomain = [('app_code', '=', 'aas_mes')]
        aas_application = request.env['aas.wechat.enapplication'].sudo().search(appdomain, limit=1)
        self.token = aas_application.app_token
        self.encoding_aeskey = aas_application.encoding_aes_key
        self.corpid = aas_application.corp_id
        self.role_secret = aas_application.role_secret

        global mes_crypto
        mes_crypto = WeChatCrypto(self.token, self.encoding_aeskey, self.corpid)
        global mes_client
        mes_client = WeChatClient(self.corpid, self.role_secret)


    @http.route('/aaswechat/mes', type='http', auth="user", methods=['GET', 'POST'])
    def aas_wechat_mes_index(self, **kwargs):
        values = request.params.copy()
        values['user'] = request.env.user.name
        return request.render('aas_mes.wechat_mes_index', values)

    @http.route('/aaswechat/mes/scaninit', type='json', auth="user")
    def aas_wechat_mes_scaninit(self, access_url=None):
        aasjsapi = mes_client.jsapi
        cticket = aasjsapi.get_jsapi_ticket()
        cnoncestr = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(15))
        ctimestamp = int(time.time())
        csignature = aasjsapi.get_jsapi_signature(noncestr=cnoncestr, ticket=cticket, timestamp=ctimestamp, url=access_url)
        wxvalues = {'debug': False, 'appId': self.corpid, 'timestamp': ctimestamp, 'nonceStr': cnoncestr}
        wxvalues.update({'signature': csignature, 'jsApiList': ['scanQRCode']})
        return wxvalues


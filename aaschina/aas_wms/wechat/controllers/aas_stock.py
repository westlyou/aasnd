# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-9 19:20
"""


import logging
import time, random, string

from odoo import http
from odoo.http import request

from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.enterprise.client import WeChatClient

logger = logging.getLogger(__name__)


wms_crypto, wms_client = None, None

class AASStockWechatController(http.Controller):

    token, encoding_aesey, corpid, role_secret = None, None, None, None

    @http.route('/aaswechat/wms', type='http', auth="user", methods=['GET', 'POST'])
    def aas_wechat_wms_index(self, **kwargs):

        if not wms_client or not wms_crypto:
            appdomain = [('app_code', '=', 'aas_wms'), ('company_id', '=', request.env.user.company_id.id)]
            aas_application = request.env['aas.wechat.enapplication'].sudo().search(appdomain, limit=1)
            self.token = aas_application.app_token
            self.encoding_aesey = aas_application.encoding_aes_key
            self.corpid = aas_application.corp_id
            self.role_secret = aas_application.role_secret
            global wms_crypto
            wms_crypto = WeChatCrypto(self.token, self.encoding_aesey, self.corpid)
            global wms_client
            wms_client = WeChatClient(self.corpid, self.role_secret)

        values = request.params.copy()
        values['user'] = request.env.user.name
        return request.render('aas_wms.wechat_wms_index', values)

    @http.route('/aaswechat/wms/scaninit', type='json', auth="user")
    def aas_wechat_wms_scaninit(self, access_url=None):
        aasjsapi = wms_client.jsapi
        cticket = aasjsapi.get_jsapi_ticket()
        cnoncestr = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(15))
        ctimestamp = int(time.time())
        csignature = aasjsapi.get_jsapi_signature(noncestr=cnoncestr, ticket=cticket, timestamp=ctimestamp, url=access_url)
        wxvalues = {'debug': False, 'appId': self.CorpId, 'timestamp': ctimestamp, 'nonceStr': cnoncestr}
        wxvalues.update({'signature': csignature, 'jsApiList': ['scanQRCode']})
        return wxvalues
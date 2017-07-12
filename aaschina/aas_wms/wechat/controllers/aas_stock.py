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

    def __init__(self):
        # appdomain = [('app_code', '=', 'aas_wms'), ('company_id', '=', request.env.user.company_id.id)]
        appdomain = [('app_code', '=', 'aas_wms')]
        aas_application = request.env['aas.wechat.enapplication'].sudo().search(appdomain, limit=1)
        self.TOKEN = aas_application.app_token
        self.EncodingAESKey = aas_application.encoding_aes_key
        self.CorpId = aas_application.corp_id
        self.RoleSecret = aas_application.role_secret

        global wms_crypto
        wms_crypto = WeChatCrypto(self.TOKEN, self.EncodingAESKey, self.CorpId)
        global wms_client
        wms_client = WeChatClient(self.CorpId, self.RoleSecret)

    @http.route('/aaswechat/wms', type='http', auth="user", methods=['GET', 'POST'])
    def aas_wechat_wms_index(self, **kwargs):
        values = request.params.copy()
        values['user'] = request.env.user.name
        return request.render('aas_wms.wechat_wms_index', values)

    @http.route('/aaswechat/wms/scaninit', type='json', auth="user")
    def aas_wechat_wms_scaninit(self, access_url=None):
        aasjsapi = wms_client.jsapi
        cticket = aasjsapi.get_jsapi_ticket()
        curl = access_url
        cnoncestr = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(15))
        ctimestamp = int(time.time())
        csignature = aasjsapi.get_jsapi_signature(noncestr=cnoncestr, ticket=cticket, timestamp=ctimestamp, url=access_url)
        wxvalues = {'debug': False, 'appId': self.CorpId, 'timestamp': ctimestamp, 'nonceStr': cnoncestr}
        wxvalues.update({'signature': csignature, 'jsApiList': ['scanQRCode']})
        return wxvalues
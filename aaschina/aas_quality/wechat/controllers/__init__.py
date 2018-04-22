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
from odoo.exceptions import AccessDenied, UserError, ValidationError

quality_crypto = None
quality_client = None

_logger = logging.getLogger(__name__)

class AASWechatQualityController(http.Controller):

    def __init__(self):
        aas_application = request.env['aas.wechat.enapplication'].sudo().search([('app_code', '=', 'aas_quality')], limit=1)
        self.token = aas_application.app_token
        self.encoding_aeskey = aas_application.encoding_aes_key
        self.corpid = aas_application.corp_id
        self.role_secret = aas_application.role_secret

        global quality_crypto
        quality_crypto = WeChatCrypto(self.token, self.encoding_aeskey, self.corpid)
        global quality_client
        quality_client = WeChatClient(self.corpid, self.role_secret)


    @http.route('/aaswechat/quality', type='http', auth="user", methods=['GET', 'POST'])
    def aas_wechat_quality_index(self, **kwargs):
        values = request.params.copy()
        values['user'] = request.env.user.name
        return request.render('aas_quality.wechat_quality_index', values)


    @http.route('/aaswechat/quality/scaninit', type='json', auth="user")
    def aas_wechat_quality_scaninit(self, access_url=None):
        aasjsapi = quality_client.jsapi
        cticket = aasjsapi.get_jsapi_ticket()
        cnoncestr = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(15))
        ctimestamp = int(time.time())
        csignature = aasjsapi.get_jsapi_signature(noncestr=cnoncestr, ticket=cticket, timestamp=ctimestamp, url=access_url)
        wxvalues = {'debug': False, 'appId': self.corpid, 'timestamp': ctimestamp, 'nonceStr': cnoncestr}
        wxvalues.update({'signature': csignature, 'jsApiList': ['scanQRCode']})
        return wxvalues


    @http.route('/aaswechat/quality/printlabels', type='json', auth="user")
    def aas_wechat_quality_printlabels(self, printerid, labelids=[]):
        values = {'success': True, 'message': ''}
        try:
            tempvals = request.env['aas.product.label'].action_print_label(printerid, ids=labelids)
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        values.update(tempvals)
        printer = request.env['aas.label.printer'].browse(printerid)
        values.update({'printer': printer.name, 'printurl': printer.serverurl})
        return values


import aas_quality

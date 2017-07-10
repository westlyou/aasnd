# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-9 18:16
"""

import logging
import werkzeug

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied,UserError,ValidationError

logger = logging.getLogger(__name__)

RECEIPTDICT = {'purchase': u'采购收货', 'manufacture': u'成品入库', 'manreturn': u'生产退料', 'sundry': u'杂项入库'}

class AASReceiptWechatController(http.Controller):

    @http.route('/aaswechat/wms/receiptlinelist', type='http', auth='user')
    def aas_wechat_wms_receiptlinelist(self, limit=20):
        values = {'success': True, 'message': '', 'receiptlines': [], 'lineindex': '0'}
        linesdomain = ['&', '|']
        linesdomain.extend(['&', ('receipt_type', '=', 'purchase'), ('state', 'in', ['checked', 'receipt'])])
        linesdomain.extend(['&', ('receipt_type', '!=', 'purchase'), ('state', 'in', ['confirm', 'receipt'])])
        linesdomain.extend([('company_id', '=', request.env.user.company_id.id)])
        receiptlines = request.env['aas.stock.receipt.line'].search(linesdomain, limit=limit)
        if receiptlines and len(receiptlines) > 0:
            values['receiptlines'] = [{
                'line_id': rline.id,
                'product_code': rline.product_id.default_code, 'receipt_qty':  rline.product_qty - rline.receipt_qty - rline.doing_qty,
                'location_name': '' if not rline.push_location else rline.push_location.name, 'receipt_type': RECEIPTDICT[rline.receipt_type]
            } for rline in receiptlines]
            values['lineindex'] = len(receiptlines)
        return request.render('aas_wms.wechat_wms_receipt_line_list', values)


    @http.route('/aaswechat/wms/receiptlinemore', type='json', auth="user")
    def aas_wechat_wms_receiptlinemore(self, lineindex=0, product_code=None, limit=20):
        values = {'receiptlines': [], 'lineindex': lineindex, 'linecount': 0}
        linesdomain = ['&', '|']
        linesdomain.extend(['&', ('receipt_type', '=', 'purchase'), ('state', 'in', ['checked', 'receipt'])])
        linesdomain.extend(['&', ('receipt_type', '!=', 'purchase'), ('state', 'in', ['confirm', 'receipt'])])
        if not product_code:
            linesdomain.extend([('company_id', '=', request.env.user.company_id.id)])
        else:
            linesdomain.extend(['&', ('company_id', '=', request.env.user.company_id.id), ('product_id', 'ilike', product_code)])
        receiptlines = request.env['aas.stock.receipt.line'].search(linesdomain, offset=lineindex, limit=limit)
        if receiptlines and len(receiptlines) > 0:
            values['receiptlines'] = [{
                'line_id': rline.id,
                'product_code': rline.product_id.default_code, 'receipt_qty':  rline.product_qty - rline.receipt_qty - rline.doing_qty,
                'location_name': '' if not rline.push_location else rline.push_location.name, 'receipt_type': RECEIPTDICT[rline.receipt_type]
            } for rline in receiptlines]
            values['linecount'] = len(receiptlines)
            values['lineindex'] = values['linecount'] + lineindex
        return values



    @http.route('/aaswechat/wms/receiptlinesearch', type='json', auth="user")
    def aas_wechat_wms_receiptlinesearch(self, product_code, limit=20):
        values = {'receiptlines': [], 'lineindex': '0'}
        linesdomain = ['&', '|']
        linesdomain.extend(['&', ('receipt_type', '=', 'purchase'), ('state', 'in', ['checked', 'receipt'])])
        linesdomain.extend(['&', ('receipt_type', '!=', 'purchase'), ('state', 'in', ['confirm', 'receipt'])])
        linesdomain.extend(['&', ('company_id', '=', request.env.user.company_id.id), ('product_id', 'ilike', product_code)])
        receiptlines = request.env['aas.stock.receipt.line'].search(linesdomain, limit=limit)
        if receiptlines and len(receiptlines) > 0:
            values['receiptlines'] = [{
                'line_id': rline.id,
                'product_code': rline.product_id.default_code, 'receipt_qty':  rline.product_qty - rline.receipt_qty - rline.doing_qty,
                'location_name': '' if not rline.push_location else rline.push_location.name, 'receipt_type': RECEIPTDICT[rline.receipt_type]
            } for rline in receiptlines]
            values['lineindex'] = len(receiptlines)
        return values


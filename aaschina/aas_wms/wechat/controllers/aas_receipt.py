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
from odoo.tools.float_utils import float_compare
from odoo.exceptions import AccessDenied,UserError,ValidationError

logger = logging.getLogger(__name__)

RECEIPTTYPEDICT = {'purchase': u'采购收货', 'manufacture': u'成品入库', 'manreturn': u'生产退料', 'sundry': u'杂项入库'}
RECEIPTSTATEDICT = {'draft': u'草稿', 'confirm': u'确认', 'tocheck': u'待检', 'checked': u'已检', 'receipt': u'收货', 'done': u'完成', 'cancel': u'取消'}

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
                'line_id': rline.id, 'receipt_name': rline.receipt_id.name, 'product_code': rline.product_id.default_code,
                'location_name': '' if not rline.push_location else rline.push_location.name, 'receipt_type': RECEIPTTYPEDICT[rline.receipt_type]
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
                'line_id': rline.id, 'receipt_name': rline.receipt_id.name, 'product_code': rline.product_id.default_code,
                'location_name': '' if not rline.push_location else rline.push_location.name, 'receipt_type': RECEIPTTYPEDICT[rline.receipt_type]
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
                'line_id': rline.id, 'receipt_name': rline.receipt_id.name, 'product_code': rline.product_id.default_code,
                'location_name': '' if not rline.push_location else rline.push_location.name, 'receipt_type': RECEIPTTYPEDICT[rline.receipt_type]
            } for rline in receiptlines]
            values['lineindex'] = len(receiptlines)
        return values

    @http.route('/aaswechat/wms/receiptline/<int:receiptlineid>', type='http', auth='user')
    def aas_wechat_wms_receiptlinedetail(self, receiptlineid):
        values = {'success': True, 'message': '', 'labellist': [], 'operationlist': []}
        receiptline = request.env['aas.stock.receipt.line'].browse(receiptlineid)
        values.update({
            'receiptlineid': receiptlineid, 'receipt_name': receiptline.receipt_id.name, 'product_code': receiptline.product_id.default_code,
            'product_uom': receiptline.product_uom.name, 'origin_order': receiptline.origin_order, 'receipt_type': receiptline.receipt_type,
            'type_name': RECEIPTTYPEDICT[receiptline.receipt_type], 'state': receiptline.state, 'state_name': RECEIPTSTATEDICT[receiptline.state],
            'push_location_id': '0' if not receiptline.push_location else receiptline.push_location.id,
            'push_location_name': '' if not receiptline.push_location else receiptline.push_location.name,
            'product_qty': receiptline.product_qty, 'receipt_qty': receiptline.receipt_qty, 'doing_qty': receiptline.doing_qty,
            'labelscan': 'none', 'pushall': 'none', 'pushdone': 'none'
        })
        if (receiptline.receipt_type=='purchase' and receiptline.state in ['checked', 'receipt']) or (receiptline.receipt_type!='purchase' and receiptline.state in ['confirm', 'receipt']):
            values.update({'labelscan': 'block', 'pushall': 'block'})
        if float_compare(receiptline.doing_qty, 0.0, precision_rounding=0.000001) > 0:
            values.update({'pushdone': 'block'})
        if receiptline.label_list and len(receiptline.label_list) > 0:
            values['labellist'] = [{
                'label_id': llist.label_id.id, 'label_name': llist.label_id.name, 'checked': llist.checked,
                'product_code': llist.product_id.default_code,'product_lot': llist.product_lot.name, 'product_qty': llist.product_qty
            } for llist in receiptline.label_list]
        if receiptline.operation_list and len(receiptline.operation_list) > 0:
            values['operationlist'] = [{
                'label_id': roperation.rlabel_id.label_id.id, 'operation_id': roperation.id,
                'roperation_id': roperation.id, 'label_name': roperation.rlabel_id.label_id.name, 'push_onshelf': roperation.push_onshelf,
                'product_code': roperation.product_id.default_code,'product_lot': roperation.product_lot.name, 'product_qty': roperation.product_qty
            } for roperation in receiptline.operation_list]
        return request.render('aas_wms.wechat_wms_receipt_line_detail', values)



    @http.route('/aaswechat/wms/receiptlinelocationscan', type='json', auth="user")
    def aas_wechat_wms_receiptlinelocationscan(self, lineid, barcode):
        values = {'success': True, 'message': ''}
        receiptline = request.env['aas.stock.receipt.line'].browse(lineid)
        if not receiptline:
            values.update({'success': False, 'message': u'请仔细检查收货明细可能被删除了！'})
            return values
        push_location = request.env['stock.location'].search([('barcode', '=', barcode)], limit=1)
        if not push_location:
            values.update({'success': False, 'message': u'无效库位， 请仔细检查是否库位已删除！'})
            return values
        values.update({'location_id': push_location.id, 'location_name': push_location.name})
        return values


    @http.route('/aaswechat/wms/receiptlinelabelscan', type='json', auth="user")
    def aas_wechat_wms_receiptlinelabelscan(self, lineid, barcode):
        values = {'success': True, 'message': ''}
        receiptline = request.env['aas.stock.receipt.line'].browse(lineid)
        if not receiptline:
            values.update({'success': False, 'message': u'请仔细检查收货明细可能被删除了！'})
            return values
        label = request.env['aas.product.label'].search([('barcode', '=', barcode)])
        if not label:
            values.update({'success': False, 'message': u'无效标签， 请仔细检查是否标签已删除！'})
            return values
        receiptlabel = request.env['aas.stock.receipt.label'].search([('line_id', '=', lineid), ('label_id', '=', label.id)], limit=1)
        if not receiptlabel:
            values.update({'success': False, 'message': u'无效标签， 当前标签不在上架范围内！'})
            return values
        receiptoperation = request.env['aas.stock.receipt.operation'].search([('line_id', '=', lineid), ('rlabel_id', '=', receiptlabel.id)], limit=1)
        if receiptoperation:
            values.update({'success': False, 'message': u'标签已作业，请不要重复操作！'})
            return values
        tempoperation = request.env['aas.stock.receipt.operation'].create({
            'rlabel_id': receiptlabel.id, 'location_id': receiptline.push_location.id
        })
        values.update({
            'label_id': label.id, 'label_name': label.name, 'product_code': label.product_code,
            'product_lot': label.product_lot.name, 'product_qty': label.product_qty, 'operation_id': tempoperation.id
        })
        return values


    @http.route('/aaswechat/wms/receiptlineoperationdel', type='json', auth="user")
    def aas_wechat_wms_receiptlineoperationdel(self, operation_id):
        values = {'success': True, 'message': ''}
        receiptoperation = request.env['aas.stock.receipt.operation'].browse(operation_id)
        if not receiptoperation:
            values.update({'success': False, 'message': u'请仔细检查收货明细可能已删除了！'})
            return values
        receiptline = receiptoperation.line_id
        receiptoperation.unlink()
        values.update({'doing_qty': receiptline.doing_qty})
        return values


    @http.route('/aaswechat/wms/receiptlinepushall', type='json', auth="user")
    def aas_wechat_wms_receiptlinepushall(self, lineid):
        values = {'success': True, 'message': ''}
        receiptline = request.env['aas.stock.receipt.line'].browse(lineid)
        try:
            receiptline.action_push_all()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        return values


    @http.route('/aaswechat/wms/receiptlinepushdone', type='json', auth="user")
    def aas_wechat_wms_receiptlinepushall(self, lineid):
        values = {'success': True, 'message': ''}
        receiptline = request.env['aas.stock.receipt.line'].browse(lineid)
        try:
            receiptline.action_push_done()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        return values

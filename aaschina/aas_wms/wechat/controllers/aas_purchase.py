# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-11 14:38
"""

import logging
import werkzeug

from odoo import http
from odoo.http import request
from odoo.tools.float_utils import float_compare
from odoo.exceptions import AccessDenied,UserError,ValidationError

logger = logging.getLogger(__name__)


class AASPurchaseWechatController(http.Controller):

    @http.route('/aaswechat/wms/purchaselist', type='http', auth='user')
    def aas_wechat_wms_purchaselist(self, limit=20):
        values = {'success': True, 'message': '', 'purchaselist': [], 'purchaseindex': '0'}
        searchdomain = [('receiptable', '=', True)]
        purchaselist = request.env['aas.stock.purchase.order'].search(searchdomain, limit=limit)
        if purchaselist and len(purchaselist) > 0:
            values['purchaselist'] = [{
                'order_id': purchase.id, 'order_name': purchase.name, 'partner_name': purchase.partner_id.name
            } for purchase in purchaselist]
            values['purchaseindex'] = len(purchaselist)
        return request.render('aas_wms.wechat_wms_purchase_list', values)

    @http.route('/aaswechat/wms/purchasemore', type='json', auth="user")
    def aas_wechat_wms_purchasemore(self, purchaseindex=0, limit=20):
        values = {'success': True, 'message': '', 'purchases': [], 'purchaseindex': purchaseindex, 'purchasecount': 0}
        searchdomain = [('receiptable', '=', True)]
        purchase_list = request.env['aas.stock.purchase.order'].search(searchdomain, offset=purchaseindex, limit=limit, order='id desc')
        if purchase_list:
            values['purchases'] = [{
                'order_id': porder.id, 'order_name': porder.name, 'partner_name': porder.partner_id.name
            } for porder in purchase_list]
            values['purchasecount'] = len(purchase_list)
            values['purchaseindex'] = purchaseindex + values['purchasecount']
        return values


    @http.route('/aaswechat/wms/purchaseimport', type='http', auth="user")
    def aas_wechat_wms_purchaseimport(self):
        values = request.params.copy()
        return request.render('aas_wms.wechat_wms_purchase_import', values)


    @http.route('/aaswechat/wms/purchaseimportdone', type='json', auth="user")
    def aas_wechat_wms_purchaseimportdone(self, order_name=None):

        return request.env['aas.stock.purchase.order'].action_import_order(order_name)


    @http.route('/aaswechat/wms/purchasedetail/<int:purchaseid>', type='http', auth='user')
    def aas_wechat_wms_purchasedetail(self, purchaseid):
        porder = request.env['aas.stock.purchase.order'].browse(purchaseid)
        values = {'purchase_id': porder.id, 'purchase_name': porder.name, 'partner_name': porder.partner_id.name}
        values['order_lines'] = [{
            'product_id': oline.product_id.id,
            'product_code':oline.product_id.default_code,
            'product_qty': str(oline.product_qty),
            'receipt_qty': str(oline.receipt_qty),
            'doing_qty': str(oline.doing_qty),
            'rejected_qty': str(oline.rejected_qty)} for oline in porder.order_lines]
        return request.render('aas_wms.wechat_wms_purchase_detail', values)


    @http.route('/aaswechat/wms/purchasereceipt/<int:purchaseid>', type='http', auth="user")
    def aas_wechat_wms_purchasereceipt(self, purchaseid):
        purchaseorder = request.env['aas.stock.purchase.order'].browse(purchaseid)
        values = {'purchase_id': purchaseorder.id, 'purchase_name': purchaseorder.name, 'partner_name': purchaseorder.partner_id.name, 'order_lines':[]}
        for oline in purchaseorder.order_lines:
            temp_qty = oline.product_qty - oline.receipt_qty + oline.rejected_qty - oline.doing_qty
            if float_compare(temp_qty, 0.0, precision_rounding=0.000001) > 0.0:
                values['order_lines'].append({'product_id': oline.product_id.id, 'product_name': oline.product_id.name, 'product_code': oline.product_id.default_code, 'product_qty': temp_qty})
        return request.render('aas_wms.wechat_wms_purchase_receipt', values)


    @http.route('/aaswechat/wms/purchasereceiptdone', type='json', auth="user")
    def aas_wechat_wms_purchasereceiptdone(self, purchaseid, receiptlines):
        values = {'success': True, 'message': ''}
        purchase_order = request.env['aas.stock.purchase.order'].browse(purchaseid)
        purchase_receipt = request.env['aas.stock.receipt'].create({
            'partner_id': purchase_order.partner_id.id,
            'receipt_type': 'purchase',
            'receipt_user': request.env.user.id,
            'receipt_lines': [(0, 0, rline) for rline in receiptlines]
        })
        values['receiptid'] = purchase_receipt.id
        productdict = {}
        for rline in purchase_receipt.receipt_lines:
            pkey = 'P_'+str(rline.product_id.id)
            if pkey not in productdict:
                productdict[pkey] = rline.product_qty
            else:
                productdict[pkey] += rline.product_qty
        for oline in purchase_order.order_lines:
            pkey = 'P_'+str(oline.product_id.id)
            if pkey in productdict:
                oline.write({'doing_qty': oline.doing_qty+productdict[pkey]})
        return values


# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-3-5 14:36
"""

import logging
import werkzeug

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

class AASQualityOQCCheckingController(http.Controller):

    @http.route('/aasquality/deliveryoqc/<int:deliveryid>', type='http', auth="user")
    def aasquality_deliveryoqc(self, deliveryid):
        values = {
            'success': True, 'message': '', 'checker': request.env.user.name,
            'productlist': [], 'pickinglist': [], 'delivery_id': deliveryid, 'delivery_name': ''
        }
        delivery = request.env['aas.stock.delivery'].browse(deliveryid)
        if not delivery.picking_list or len(delivery.picking_list) <= 0:
            delivery.action_picking_list()
        values['delivery_name'] = delivery.name
        productlist = []
        if delivery.delivery_lines and len(delivery.delivery_lines) > 0:
            for dline in delivery.delivery_lines:
                if dline.state in ['done', 'cancel']:
                    continue
                productlist.append({
                    'product_id': dline.product_id.id, 'product_code': dline.product_id.default_code,
                    'picking_qty': '0.0', 'todo_qty': dline.product_qty - dline.delivery_qty,
                })
            values['productlist'] = productlist
        if delivery.picking_list and len(delivery.picking_list) > 0:
            values['pickinglist'] = [{
                'product_code': dpicking.product_id.default_code, 'product_lot': dpicking.product_lot.name,
                'product_qty': dpicking.product_qty, 'location_name': dpicking.location_id.name
            } for dpicking in delivery.picking_list]
        return request.render('aas_quality.aas_deliveryoqc_order', values)


    @http.route('/aasquality/deliveryoqc/scanlabel', type='json', auth="user")
    def aasquality_deliveryoqc_scanlabel(self, barcode, deliveryid):
        values = {'success': True, 'message': ''}
        label = request.env['aas.product.label'].search([('barcode', '=', barcode.upper())], limit=1)
        if not label:
            values.update({'success': False, 'message': u'标签异常，你扫描的可能不是标签条码！'})
            return values
        if label.isproduction:
            values.update({'success': False, 'message': u'请不要扫描生产线边库标签！'})
            return values
        if label.locked:
            values.update({'success': False, 'message': u'标签已经被锁定，请解锁后再继续操作'})
            return values
        if label.state != 'normal':
            values.update({'success': False, 'message': u'标签状态异常，只有正常状态的标签才可以报检！'})
            return values
        if label.oqcpass:
            values.update({'success': False, 'message': u'标签已报检，请不要重复重复操作！'})
            return values
        dldomain = [('delivery_id', '=', deliveryid), ('product_id', '=', label.product_id.id)]
        dldomain.append(('state', 'not in', ['done', 'cancel']))
        if request.env['aas.stock.delivery.line'].search_count(dldomain) <= 0:
            values.update({'success': False, 'message': u'当前发货单不需要报检此产成品，请放弃此标签扫描！'})
            return values
        oqcdomain = [('label_id', '=', label.id), ('checked', '=', False)]
        if request.env['aas.quality.oqcorder.label'].sudo().search_count(oqcdomain) > 0:
            values.update({'success': False, 'message': u'标签已报检，还未处理；请耐心等待！'})
            return values
        values.update({
            'label_id': label.id, 'label_name': label.name, 'product_qty': label.product_qty,
            'product_id': label.product_id.id, 'product_code': label.product_id.default_code,
            'product_lot': label.product_lot.name, 'location_name': label.location_id.name
        })
        return values


    @http.route('/aasquality/deliveryoqc/docommit', type='json', auth="user")
    def aasquality_deliveryoqc_docommit(self, labelids):
        print labelids
        values = {'success': True, 'message': '', 'oqcorderid': '0'}
        if not labelids or len(labelids) <= 0:
            values.update({'success': False, 'message': u'报检异常，请检查是否有提交了待检测的标签！'})
            return values
        labelist = request.env['aas.product.label'].browse(labelids)
        if not labelist or len(labelist) <= 0:
            values.update({'success': False, 'message': u'报检异常，请检查是否有提交了待检测的标签！'})
            return values
        productdict = {}
        for label in labelist:
            pkey = 'P'+str(label.product_id.id)
            if pkey in productdict:
                productdict[pkey]['label_lines'].append((0, 0, {
                    'label_id': label.id, 'product_id': label.product_id.id,
                    'product_lot': label.product_lot.id, 'product_qty': label.product_qty
                }))
                productdict[pkey]['product_qty'] += label.product_qty
            else:
                productdict[pkey] = {
                    'product_id': label.product_id.id, 'product_uom': label.product_uom.id,
                    'product_qty': label.product_qty,
                    'label_lines': [(0, 0, {
                        'label_id': label.id, 'product_id': label.product_id.id,
                        'product_lot': label.product_lot.id, 'product_qty': label.product_qty
                    })]
                }
        if productdict and len(productdict) > 0:
            for tkey, tvals in productdict.items():
                oqcorder = request.env['aas.quality.oqcorder'].create(tvals)
                oqcorder.action_confirm()
        return values

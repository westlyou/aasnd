# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-11-30 10:12
"""

import logging

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

class AASWMSDeliveryController(http.Controller):

    @http.route('/aaswms/delivery', type='http', auth="user")
    def aaswms_delivery(self):
        chinatoday = fields.Datetime.to_china_today()
        values = {
            'success': True, 'message': '', 'currentdate': chinatoday,
            'checker': request.env.user.name, 'deliverylist': [], 'productlist': []
        }
        timezonestarttime, timezonefinishtime = chinatoday+' 00:00:00', chinatoday+' 23:59:59'
        timestart = fields.Datetime.to_utc_string(fields.Datetime.from_string(timezonestarttime), 'Asia/Shanghai')
        timefinish = fields.Datetime.to_utc_string(fields.Datetime.from_string(timezonefinishtime), 'Asia/Shanghai')
        deliverydomain = [('pick_time', '>=', timestart), ('pick_time', '<=', timefinish)]
        deliverydomain.extend([('deliver_done', '=', True), ('delivery_type', '=', 'sales')])
        deliverylabels = request.env['aas.stock.delivery.operation'].search(deliverydomain)
        if deliverylabels and len(deliverylabels) > 0:
            deliverydict = {}
            for dlabel in deliverylabels:
                tlabel = dlabel.label_id
                pkey = 'P'+str(tlabel.product_id.id)
                if pkey not in deliverydict:
                    deliverydict[pkey] = {
                        'label_count': 1, 'product_qty': tlabel.product_qty, 'product_code': tlabel.product_code
                    }
                else:
                    deliverydict[pkey]['label_count'] += 1
                    deliverydict[pkey]['product_qty'] += tlabel.product_qty
            values['productlist'] = deliverydict.values()
        ddomain = [('delivery_type', '=', 'sales'), ('state', 'in', ['confirm', 'picking', 'pickconfirm'])]
        deliverylist = request.env['aas.stock.delivery'].search(ddomain)
        if deliverylist and len(deliverylist) > 0:
            values['deliverylist'] = [{
                'delivery_id': delivery.id, 'delivery_name': delivery.name
            } for delivery in deliverylist]
        return request.render('aas_wms.aas_delivery', values)



    @http.route('/aaswms/delivery/detail/<int:deliveryid>', type='http', auth="user")
    def aaswms_delivery_detail(self, deliveryid):
        values = {
            'success': True, 'message': '', 'delivery_id': deliveryid, 'delivery_name': '',
            'checker': request.env.user.name, 'productlist': [], 'operationlist': []
        }
        delivery = request.env['aas.stock.delivery'].browse(deliveryid)
        values['delivery_name'] = delivery.name
        deliverylines = delivery.delivery_lines
        if not deliverylines or len(deliverylines) <= 0:
            return request.render('aas_wms.aas_delivery_detail', values)
        values['productlist'] = [{
            'product_id': dline.product_id.id, 'product_code': dline.product_id.default_code,
            'delivery_qty': dline.delivery_qty, 'picking_qty': dline.picking_qty
        } for dline in deliverylines]
        optdomain = [('delivery_id', '=', deliveryid), ('deliver_done', '=', False)]
        operationlist = request.env['aas.stock.delivery.operation'].search(optdomain)
        if operationlist and len(operationlist) > 0:
            values['operationlist'] = [{
                'operation_id': tempopt.id, 'label_name': tempopt.label_id.name,
                'product_code': tempopt.product_id.default_code,
                'product_id': tempopt.product_id.id, 'product_lot': tempopt.product_lot.name,
                'product_qty': tempopt.product_qty, 'location_name': tempopt.location_id.name
            } for tempopt in operationlist]
        return request.render('aas_wms.aas_delivery_detail', values)



    @http.route('/aaswms/delivery/scanlabel', type='json', auth="user")
    def aasmes_delivery_scanlabel(self, barcode, deliveryid):
        values = {'success': True, 'message': '', 'product_id': '0', 'picking_qty': '0.0'}
        label = request.env['aas.product.label'].search([('barcode', '=', barcode)], limit=1)
        if not label:
            values.update({'success': False, 'message': u'未搜搜到此标签，请仔细检查！'})
            return values
        if label.isproduction:
            values.update({'success': False, 'message': u'产线标签，不可以扫描！'})
            return values
        if not label.oqcpass:
            values.update({'success': False, 'message': u'标签还没通过OQC检测，不可以扫描！'})
            return values
        if label.state != 'normal':
            values.update({'success': False, 'message': u'标签状态异常，请仔细检查！'})
            return values
        if label.locked:
            values.update({'success': False, 'message': u'标签锁定，标签已被%s锁定，请联系相关人员！'% label.locked_order})
            return values
        linedomain = [('delivery_id', '=', deliveryid), ('product_id', '=', label.product_id.id)]
        if request.env['aas.stock.delivery.line'].search_count(linedomain) <= 0:
            values.update({'success': False, 'message': u'扫描异常，当前标签可能不是此发货单要发的产品！'})
            return values
        optdomain = [('delivery_id', '=', deliveryid), ('label_id', '=', label.id)]
        if request.env['aas.stock.delivery.operation'].search_count(optdomain) > 0:
            values.update({'success': False, 'message': u'标签已存在，请不要重复扫描！'})
            return values
        doperation = request.env['aas.stock.delivery.operation'].create({
            'delivery_id': deliveryid, 'label_id': label.id
        })
        deliveryline = doperation.delivery_line
        values.update({'product_id': deliveryline.product_id.id, 'picking_qty': deliveryline.picking_qty})
        values['label'] = {
            'operation_id': doperation.id, 'label_name': label.name, 'product_code': label.product_code,
            'product_lot': label.product_lot.name, 'product_qty': label.product_qty,
            'location_name': label.location_id.name, 'product_id': label.product_id.id
        }
        return values


    @http.route('/aaswms/delivery/deloperation', type='json', auth="user")
    def aasmes_delivery_deloperation(self, operationid):
        values = {'success': True, 'message': '', 'product_id': '0', 'picking_qty': '0.0'}
        doperation = request.env['aas.stock.delivery.operation'].browse(operationid)
        deliverylineid = doperation.delivery_line.id
        if doperation.deliver_done:
            values.update({'success': False, 'message': u'当前记录已执行发货，不可以删除！'})
            return values
        doperation.unlink()
        deliveryline = request.env['aas.stock.delivery.line'].browse(deliverylineid)
        values.update({'product_id': deliveryline.product_id.id, 'picking_qty': deliveryline.picking_qty})
        return values


    @http.route('/aaswms/delivery/dodelivery', type='json', auth="user")
    def aasmes_delivery_dodelivery(self, deliveryid):
        values = {'success': True, 'message': ''}
        optdomain = [('delivery_id', '=', deliveryid), ('deliver_done', '=', False)]
        operationlines = request.env['aas.stock.delivery.operation'].search(optdomain)
        if not operationlines or len(operationlines) <= 0:
            values.update({'success': False, 'message': u'当前还没有任何拣货操作，不可以执行发货！'})
            return values
        delivery = request.env['aas.stock.delivery'].browse(deliveryid)
        if delivery.state == 'done':
            values.update({'success': False, 'message': u'当前发货单已经完成，请不要重复操作！'})
            return values
        if delivery.state == 'cancel':
            values.update({'success': False, 'message': u'当前发货单已经取消，请不要继续操作！'})
            return values
        delivery.action_picking_confirm()
        delivery.action_deliver_done()
        return values
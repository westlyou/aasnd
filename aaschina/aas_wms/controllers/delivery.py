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
        values = {'success': True, 'message': '', 'checker': request.env.user.name, 'deliverylist': []}
        currentdate = fields.Datetime.to_timezone_string(fields.Datetime.now(), 'Asia/Shanghai')[0:10]
        values['currentdate'] = currentdate
        timezonestarttime, timezonefinishtime = currentdate+' 00:00:00', currentdate+' 23:59:59'
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
                        'label_count': 1,
                        'product_qty': tlabel.product_qty,
                        'product_code': tlabel.product_code if not tlabel.product_id.customer_product_code else tlabel.product_id.customer_product_code
                    }
                else:
                    deliverydict[pkey]['label_count'] += 1
                    deliverydict[pkey]['product_qty'] += tlabel.product_qty
            values['deliverylist'] = deliverydict.values()
        return request.render('aas_wms.aas_delivery', values)


    @http.route('/aaswms/delivery/scanlabel', type='json', auth="user")
    def aasmes_delivery_scanlabel(self, barcode, labelids=[]):
        values = {'success': True, 'message': ''}
        label = request.env['aas.product.label'].search([('barcode', '=', barcode)], limit=1)
        if not label:
            values.update({'success': False, 'message': u'未搜搜到此标签，请仔细检查！'})
            return values
        if label.isproduction:
            values.update({'success': False, 'message': u'产线标签，不可以扫描！'})
            return values
        if str(label.id) in labelids:
            values.update({'success': False, 'message': u'标签已存在请不要重复扫描！'})
            return values
        if label.state != 'normal':
            values.update({'success': False, 'message': u'标签状态异常，请仔细检查！'})
            return values
        values.update({
            'label_id': label.id, 'label_name': label.name, 'product_qty': label.product_qty, 'product_id': label.product_id.id,
            'product_code': label.product_code if not label.product_id.customer_product_code else label.product_id.customer_product_code
        })
        return values


    @http.route('/aaswms/delivery/actiondone', type='json', auth="user")
    def aasmes_delivery_actiondone(self, labelids=[]):
        values = {'success': True, 'message': ''}
        if not labelids and len(labelids) > 0:
            values.update({'success': False, 'message': u'请先扫描需要出货的标签！'})
            return values
        labellist = request.env['aas.product.label'].browse(labelids)
        deliveryvals, productdict = {'delivery_type': 'sales', 'pick_user': request.env.user.id}, {}
        for tlabel in labellist:
            pkey = 'P-'+str(tlabel.product_id.id)
            if pkey not in productdict:
                productdict[pkey] = {
                    'product_id': tlabel.product_id.id, 'product_qty': tlabel.product_qty, 'delivery_type': 'sales'
                }
            else:
                productdict[pkey]['product_qty'] += tlabel.product_qty
        deliveryvals['delivery_lines'] = [(0, 0, dline) for dline in productdict.values()]
        delivery = request.env['aas.stock.delivery'].create(deliveryvals)
        delivery.action_confirm()
        listdict, dlinedict = {}, {}
        for dline in delivery.delivery_lines:
            pkey = 'P-'+str(dline.product_id.id)
            dlinedict[pkey] = dline.id
        for tlabel in labellist:
            pkey = 'P-'+str(tlabel.product_id.id)
            lkey = pkey+'-'+str(tlabel.product_lot.id)+'-'+str(tlabel.location_id.id)
            if lkey not in listdict:
                deliverylineid = dlinedict[pkey]
                listdict[lkey] = {
                    'product_id': tlabel.product_id.id, 'product_uom': tlabel.product_uom.id, 'delivery_line': deliverylineid,
                    'product_lot': tlabel.product_lot.id, 'location_id': tlabel.location_id.id, 'product_qty': tlabel.product_qty
                }
            else:
                listdict[lkey]['product_qty'] += tlabel.product_qty
        delivery.write({'picking_list': [(0, 0, dlist) for dlist in listdict.values()]})
        operationlist = []
        for tlabel in labellist:
            pkey = 'P-'+str(tlabel.product_id.id)
            lineid = False if pkey not in dlinedict else dlinedict[pkey]
            operationlist.append((0, 0, {'label_id': tlabel.id, 'delivery_line': lineid}))
        delivery.write({'operation_lines': operationlist})
        delivery.action_picking_confirm()
        delivery.action_deliver_done()
        return values
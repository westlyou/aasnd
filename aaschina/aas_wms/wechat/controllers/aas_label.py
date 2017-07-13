# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-13 11:05
"""

import logging
import werkzeug

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied,UserError,ValidationError

logger = logging.getLogger(__name__)


class AASLabelWechatController(http.Controller):


    @http.route('/aaswechat/wms/labellist', type='http', auth="user")
    def aas_wechat_wms_labellist(self, limit=20):
        values = {'labels': [], 'labelindex': '0'}
        label_list = request.env['aas.product.label'].search([], limit=limit)
        if label_list:
            values['labels'] = [{
                'label_id': label.id,
                'label_name': label.name,
                'product_code': label.product_code,
                'product_lot': label.product_lot.name,
                'location_name': label.location_id.name,
                'product_qty': label.product_qty} for label in label_list]
            values['labelindex'] = str(len(label_list))
        return request.render('aas_wms.wechat_wms_label_list', values)


    @http.route('/aaswechat/wms/labelmore', type='json', auth="user")
    def aas_wechat_labelmore(self, searchkey=None, labelindex=0, limit=20):
        values = {'labels': [], 'labelindex': labelindex, 'labelcount': 0}
        labeldomain = []
        if searchkey:
            labeldomain = ['|', ('product_code', 'ilike', searchkey), ('product_lot', 'ilike', searchkey)]
        label_list = request.env['aas.product.label'].search(labeldomain, offset=labelindex, limit=limit)
        if label_list:
            values['labels'] = [{
                'label_id': label.id,
                'label_name': label.name,
                'product_code': label.product_code,
                'product_lot': label.product_lot.name,
                'location_name': label.location_id.name,
                'product_qty': label.product_qty} for label in label_list]
            values['labelcount'] = len(label_list)
            values['labelindex'] = values['labelcount'] + labelindex
        return values

    @http.route('/aaswechat/wms/labelmore', type='json', auth="user")
    def aas_wechat_labelsearch(self, searchkey=None, limit=20):
        values = {'labels': [], 'labelindex': 0}
        labeldomain = []
        if searchkey:
            labeldomain = ['|', ('product_code', 'ilike', searchkey), ('product_lot', 'ilike', searchkey)]
        label_list = request.env['aas.product.label'].search(labeldomain, limit=limit)
        if label_list:
            values['labels'] = [{
                'label_id': label.id,
                'label_name': label.name,
                'product_code': label.product_code,
                'product_lot': label.product_lot.name,
                'location_name': label.location_id.name,
                'product_qty': label.product_qty} for label in label_list]
            values['labelindex'] = len(label_list)
        return values
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

    @http.route('/aasquality/oqcchecking', type='http', auth="user")
    def aasquality_oqcchecking(self):
        values = {'success': True, 'message': '', 'checker': request.env.user.name}
        return request.render('aas_quality.aas_oqcchecking', values)


    @http.route('/aasquality/oqcchecking/scanlabel', type='json', auth="user")
    def aasquality_oqcchecking_scanlabel(self, barcode):
        values = {'success': True, 'message': ''}
        label = request.env['aas.product.label'].search([('barcode', '=', barcode.upper())], limit=1)
        if not label:
            values.update({'success': False, 'message': u'标签异常，你扫描的可能不是标签条码！'})
            return values
        if label.oqcpass:
            values.update({'success': False, 'message': u'OQC已操作过，请不要重复操作！'})
            return values
        if label.isproduction:
            values.update({'success': False, 'message': u'请不要扫描生产线边库标签！'})
            return values
        if label.locked:
            values.update({'success': False, 'message': u'标签已经被%s锁定，请解锁后再继续操作'% label.locked_order})
            return values
        if label.state != 'normal':
            values.update({'success': False, 'message': u'标签状态异常，只有正常状态的标签才可以报检！'})
            return values
        values.update({
            'label_id': label.id, 'label_name': label.name, 'product_qty': label.product_qty,
            'product_id': label.product_id.id, 'product_code': label.product_id.default_code,
            'product_lot': label.product_lot.name,
            'customer_pn': '' if not label.product_id.customer_product_code else label.product_id.customer_product_code
        })
        return values


    @http.route('/aasquality/oqcchecking/docommit', type='json', auth="user")
    def aasquality_oqcchecking_docommit(self, labelids):
        print labelids
        values = {'success': True, 'message': '', 'oqcorderid': '0'}
        if not labelids or len(labelids) <= 0:
            values.update({'success': False, 'message': u'报检异常，请检查是否有提交了待检测的标签！'})
            return values
        labelist = request.env['aas.product.label'].browse(labelids)
        if not labelist or len(labelist) <= 0:
            values.update({'success': False, 'message': u'报检异常，请检查是否有提交了待检测的标签！'})
            return values
        firstlabel = labelist[0]
        temproduct, product_qty = firstlabel.product_id, 0.0
        oqcordervals = {'product_id': temproduct.id, 'product_uom': temproduct.uom_id.id}
        labellines = []
        for tlabel in labelist:
            product_qty += tlabel.product_qty
            labellines.append((0, 0, {
                'label_id': tlabel.id, 'product_id': tlabel.product_id.id,
                'product_lot': tlabel.product_lot.id, 'product_qty': tlabel.product_qty
            }))
        oqcordervals.update({'product_qty': product_qty, 'label_lines': labellines, 'state': 'confirm'})
        try:
            oqcorder = request.env['aas.quality.oqcorder'].create(oqcordervals)
            values['oqcorderid'] = oqcorder.id
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        except ValidationError, ve:
            values.update({'success': False, 'message': ve.name})
            return values
        return values

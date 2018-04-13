# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-4-13 13:16
"""

import logging
import werkzeug

from odoo import http, fields
from odoo.http import request
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

REWORKSTATEDICT = {'commit': u'不良上报', 'repair': u'返工维修', 'ipqc': u'IPQC确认', 'done': u'完成'}

class AASMESFeedmaterialController(http.Controller):

    @http.route('/aasmes/feedmaterial', type='http', auth="user")
    def aasmes_feedmaterial(self):
        loginuser = request.env.user
        values = {'success': True, 'message': '', 'checker': loginuser.name, 'meslinelist': []}
        meslinelist = request.env['aas.mes.line'].search([])
        if meslinelist and len(meslinelist) > 0:
            values['meslinelist'] = [{'mesline_id': mesline.id, 'mesline_name': mesline.name} for mesline in meslinelist]
        return request.render('aas_mes.aas_feedmaterial', values)


    @http.route('/aasmes/feedmaterial/scaning', type='json', auth="user")
    def aasmes_feedmaterial_scaning(self, meslineid, barcode):
        values = {'success': True, 'message': '', 'material': False}
        locationlist = []
        mesline = request.env['aas.mes.line'].browse(meslineid)
        plocation = mesline.location_production_id
        if plocation:
            locationlist.append((plocation.parent_left, plocation.parent_right))
        if mesline.location_material_list and len(mesline.location_material_list) > 0:
            for mmlocation in mesline.location_material_list:
                mlocation = mmlocation.location_id
                locationlist.append((mlocation.parent_left, mlocation.parent_right))
        if not locationlist or len(locationlist) <= 0:
            values.update({'success': False, 'message': u'当前产线可能还未设置库位信息！'})
            return values
        barcode = barcode.upper()
        prestr = barcode[0:2]
        if prestr == 'AT':
            container = request.env['aas.container'].search([('barcode', '=', barcode)], limit=1)
            if not container:
                values.update({'success': False, 'message': u'未搜索到容器，请仔细检查是否是有效的容器条码！'})
                return values
            if container.isempty:
                values.update({'success': False, 'message': u'当前容器空空如也，无法上料！'})
                return values
            productline = container.product_lines[0]
            values['material'] = {
                'material_code': productline.product_id.default_code,
                'material_lot': productline.product_lot.name, 'material_qty': productline.stock_qty,
                'barcode': barcode, 'label_name': '', 'container_name': container.name
            }
        else:
            label = request.env['aas.product.label'].search([('barcode', '=', barcode)], limit=1)
            if not label:
                values.update({'success': False, 'message': u'未搜索到标签，请仔细检查是否是有效的标签条码！'})
                return values
            if label.state != 'normal':
                values.update({'success': False, 'message': u'标签状态异常，可能标签已冻结，或是无效标签；请仔细检查！'})
                return values
            if label.locked:
                values.update({'success': False, 'message': u'标签已被单据%s锁定，暂时不可以投料！'% label.locked_order})
                return values
            passflag, llocation = False, label.location_id
            for tlocation in locationlist:
                if tlocation[0] <= llocation.parent_left and tlocation[1] >= llocation.parent_right:
                    passflag = True
                    break
            if not passflag:
                values.update({'success': False, 'message': u'当前标签不在产线的线边库中不可以上料！'})
                return values
            values['material'] = {
                'material_code': label.product_code, 'material_lot': label.product_lot.name,
                'material_qty': label.product_qty, 'barcode': barcode, 'label_name': label.name, 'container_name': ''
            }
        return values


    @http.route('/aasmes/feedmaterial/dofeeding', type='json', auth="user")
    def aasmes_feedmaterial_dofeeding(self, meslineid, barcodes):
        values = {'success': True, 'message': ''}
        if not barcodes or len(barcodes) <= 0:
            values.update({'success': False, 'message': u'您还未添加上料记录！'})
            return values
        mesline = request.env['aas.mes.line'].browse(meslineid)
        for barcode in barcodes:
            if barcode.startswith('AT'):
                request.env['aas.mes.feedmaterial'].action_feeding_withcontainer(mesline, barcode)
            else:
                request.env['aas.mes.feedmaterial'].action_feeding_withlabel(mesline, barcode)
        return values
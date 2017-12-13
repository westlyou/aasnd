# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-12-13 09:11
"""

import logging
import werkzeug

from odoo import http, fields
from odoo.http import request
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

class AASContainerController(http.Controller):

    @http.route('/aaswechat/mes/container', type='http', auth='user')
    def aas_wechat_mes_container(self, limit=20):
        values = {'containers': [], 'containerindex': '0'}
        containerlist = request.env['aas.container'].search([], limit=limit)
        if containerlist and len(containerlist) > 0:
            values['containers'] = [{
                'cid': container.id, 'name': container.name,
                'alias': container.alias, 'location': container.location_id.name
            } for container in containerlist]
            values['containerindex'] = len(containerlist)
        return request.render('aas_mes.wechat_mes_container', values)


    @http.route('/aaswechat/mes/containermore', type='json', auth="user")
    def aas_wechat_mes_containermore(self, searchkey=None, containerindex=0, limit=20):
        values = {'containers': [], 'containerindex': containerindex, 'containercount': 0}
        tempdomain = []
        if searchkey:
            tempdomain = ['|', ('name', 'ilike', searchkey), ('alias', 'ilike', searchkey)]
        containerlist = request.env['aas.container'].search(tempdomain, offset=containerindex, limit=limit)
        if containerlist and len(containerlist) > 0:
            values['containers'] = [{
                'cid': container.id, 'name': container.name,
                'alias': container.alias, 'location': container.location_id.name
            } for container in containerlist]
            values['containercount'] = len(containerlist)
            values['containerindex'] = values['containercount'] + containerindex
        return values


    @http.route('/aaswechat/mes/containersearch', type='json', auth="user")
    def aas_wechat_mes_containersearch(self, searchkey, limit=20):
        values = {'success': True, 'message': '', 'containers': [], 'containerindex': 0}
        tempdomain = []
        if searchkey:
            tempdomain = ['|', ('name', 'ilike', '%'+searchkey+'%'), ('alias', 'ilike', '%'+searchkey+'%')]
        containerlist = request.env['aas.container'].search(tempdomain, limit=limit)
        if containerlist and len(containerlist) > 0:
            values['containers'] = [{
                'cid': container.id, 'name': container.name,
                'alias': container.alias, 'location': container.location_id.name
            } for container in containerlist]
            values['containerindex'] = len(containerlist)
        return values


    @http.route(['/aaswechat/mes/containerdetail/<int:containerid>', '/aaswechat/mes/containerdetail/<string:barcode>'], type='http', auth="user")
    def aas_wechat_mes_containerdetail(self, containerid=None, barcode=None):
        if containerid:
            tcontainer = request.env['aas.container'].browse(containerid)
        else:
            tcontainer = request.env['aas.container'].search([('barcode', '=', barcode)], limit=1)
        values = {'cid': tcontainer.id, 'name': tcontainer.name, 'alias': tcontainer.alias, 'productlist': []}
        values['location'] = tcontainer.location_id.name
        if tcontainer.product_lines and len(tcontainer.product_lines) > 0:
            values['productlist'] = [{
                'product_code': pline.product_id.default_code,
                'product_lot': pline.product_lot.name, 'product_qty': pline.product_qty
            } for pline in tcontainer.product_lines]
        return request.render('aas_mes.wechat_mes_container_detail', values)


    @http.route('/aaswechat/mes/printcontainers', type='json', auth="user")
    def aas_wechat_mes_printcontainers(self, printerid, containerids):
        values = {'success': True, 'message': ''}
        try:
            tempvals = request.env['aas.container'].action_print_label(printerid, ids=containerids)
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        values.update(tempvals)
        printer = request.env['aas.label.printer'].browse(printerid)
        values.update({'printer': printer.name, 'printurl': printer.serverurl})
        return values


    @http.route('/aaswechat/mes/containerclean', type='json', auth="user")
    def aas_wechat_mes_containerclean(self, containerids=[]):
        values = {'success': True, 'message': ''}
        companyid = request.env.user.company_id.id
        productionlocation = request.env.ref('stock.location_production').id
        if not containerids or len(containerids) <= 0:
            return values
        containerlist = request.env['aas.container'].browse(containerids)
        if not containerlist or len(containerlist) <= 0:
            return values
        for container in containerlist:
            containerlocation = container.stock_location_id.id
            if not container.product_lines or len(container.product_lines) <= 0:
                continue
            productlines, movelines = [], []
            for pline in container.product_lines:
                productlines.append((2, pline.id, False))
                movelines.append({
                    'name': container.name, 'product_id': pline.product_id.id, 'product_uom': pline.product_id.uom_id.id,
                    'create_date': fields.Datetime.now(), 'company_id': companyid, 'restrict_lot_id': pline.product_lot.id,
                    'product_uom_qty': pline.stock_qty, 'location_id': containerlocation, 'location_dest_id': productionlocation
                })
            container.write({'product_lines': productlines})
            movelist = request.env['stock.move']
            for tmove in movelines:
                movelist |= request.env['stock.move'].create(tmove)
            movelist.action_done()
        return values


    @http.route('/aaswechat/mes/cleancontainers', type='http', auth='user')
    def aas_wechat_mes_cleancontainers(self):
        return request.render('aas_mes.wechat_mes_container_clean', {})


    @http.route('/aaswechat/mes/scancontainer', type='json', auth="user")
    def aas_wechat_mes_scancontainer(self, barcode):
        values = {'success': True, 'message': ''}
        container = request.env['aas.container'].search([('barcode', '=', barcode)], limit=1)
        if not container:
            values.update({'success': False, 'message': u'请仔细检查是否扫描有效的容器条码！'})
            return values
        values.update({
            'container_id': container.id, 'container_name': container.name, 'container_alias': container.alias,
            'container_location': container.location_id.name, 'productlist': []
        })
        if container.product_lines and len(container.product_lines) > 0:
            values['productlist'] = [{
                'product_code': cpline.product_id.default_code,
                'product_lot': cpline.product_lot.name, 'product_qty': cpline.product_qty
            } for cpline in container.product_lines]
        return values





# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-29 14:58
"""

import logging
import werkzeug

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied,UserError,ValidationError

_logger = logging.getLogger(__name__)

class AASInventoryWechatController(http.Controller):

    @http.route('/aaswechat/wms/inventorylist', type='http', auth="user")
    def aas_wechat_wms_inventorylist(self, limit=20):
        values = {'inventoryindex': '0', 'inventorylist': []}
        inventorylist = request.env['aas.stock.inventory'].search([('state', '=', 'confirm')], limit=limit)
        if inventorylist and len(inventorylist) > 0:
            values['inventorylist'] = [{
                'inventory_name': tinventory.name, 'inventory_id': tinventory.id
            } for tinventory in inventorylist]
        return request.render('aas_wms.wechat_wms_inventory_list', values)


    @http.route('/aaswechat/wms/inventorymore', type='json', auth="user")
    def aas_wechat_wms_receiptmore(self, inventoryindex=0, limit=20):
        values = {'inventorylist': [], 'inventoryindex': inventoryindex, 'inventorycount': 0}
        inventorylist = request.env['aas.stock.inventory'].search([('state', '=', 'confirm')], offset=inventoryindex, limit=limit)
        if inventorylist and len(inventorylist) > 0:
            values['inventorylist'] = [{
                'inventory_name': tinventory.name, 'inventory_id': tinventory.id
            } for tinventory in inventorylist]
            values['inventorycount'] = len(inventorylist)
            values['inventoryindex'] = inventoryindex + values['inventorycount']
        return values


    @http.route('/aaswechat/wms/inventory/<int:inventoryid>', type='http', auth="user")
    def aas_wechat_wms_inventorydetail(self, inventoryid):
        values = {'inventory_id': inventoryid, 'labelscan': 'none', 'labellist': []}
        inventory = request.env['aas.stock.inventory'].browse(inventoryid)
        values.update({
            'inventory_name': inventory.name, 'product_code': '' if not inventory.product_id else inventory.product_id.default_code,
            'location_name': '' if not inventory.location_id else inventory.location_id.name,
            'product_lot': '' if not inventory.product_lot else inventory.product_lot.name,
            'istate': inventory.state
        })
        if inventory.state=='confirm':
            values['labelscan'] = 'block'
        if inventory.inventory_labels and len(inventory.inventory_labels) > 0:
            values['labellist'] = [{
                'ilabel_id': ilabel.id, 'product_qty': ilabel.product_qty,
                'label_name': ilabel.label_id.name, 'prodcut_code': ilabel.product_id.default_code,
                'product_lot': ilabel.prodcut_lot.name, 'location_name': ilabel.location_id.name
            } for ilabel in inventory.inventory_labels]
        return request.render('aas_wms.wechat_wms_inventory_detail', values)


    @http.route('/aaswechat/wms/inventorylabelscan', type='json', auth="user")
    def aas_wechat_wms_inventorylabelscan(self, inventoryid, barcode):
        values = {'success': True, 'message': ''}
        inventory = request.env['aas.stock.inventory'].browse(inventoryid)
        if not inventory:
            values.update({'success': False, 'message': u'请仔细检查盘点单可能被删除了！'})
            return values
        label = request.env['aas.product.label'].search([('barcode', '=', barcode), ('state', 'in', ['normal', 'frozen'])], limit=1)
        if not label:
            values.update({'success': False, 'message': u'无效标签， 请仔细检查标签可能状态异常或已删除！'})
            return values
        inventorylabel = request.env['aas.stock.inventory.label'].search([('inventory_id', '=', inventoryid), ('label_id', '=', label.id)], limit=1)
        if inventorylabel:
            values.update({'success': False, 'message': u'标签已存在，请不要重复扫描！'})
            return values
        try:
            templabel = request.env['aas.stock.inventory.label'].create({'label_id': label.id, 'inventory_id': inventoryid})
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        except ValidationError, ve:
            values.update({'success': False, 'message': ve.name})
            return values
        values.update({
            'label_id': label.id, 'label_name': label.name, 'product_code': label.product_code,
            'product_lot': label.product_lot.name, 'product_qty': label.product_qty,
            'ilabel_id': templabel.id
        })
        return values


    @http.route('/aaswechat/wms/inventorylabeldel', type='json', auth="user")
    def aas_wechat_wms_inventorylabeldel(self, ilabel_id):
        values = {'success': True, 'message': ''}
        inventorylabel = request.env['aas.stock.inventory.label'].browse(ilabel_id)
        if not inventorylabel:
            values.update({'success': False, 'message': u'请仔细检查标签可能已删除了！'})
            return values
        inventorylabel.unlink()
        return values
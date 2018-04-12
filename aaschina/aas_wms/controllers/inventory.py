# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-4-12 10:56
"""

import logging

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

class AASWMSInventoryController(http.Controller):


    @http.route('/aaswms/inventory/detail/<int:inventoryid>', type='http', auth="user")
    def aaswms_inventory_detail(self, inventoryid):
        values = {
            'candel': False,
            'success': True, 'message': '', 'checker': request.env.user.name, 'name': '', 'serialnumber': '',
            'product_code': '', 'product_lot': '', 'location_name': '',  'mesline_name': '', 'inventorylist': []
        }
        inventory = request.env['aas.stock.inventory'].browse(inventoryid)
        values['inventory_id'] = inventory.id
        values.update({'name': inventory.name, 'serialnumber': inventory.serialnumber})
        if inventory.product_id:
            values['product_code'] = inventory.product_id.default_code
        if inventory.product_lot:
            values['product_lot'] = inventory.product_lot.name
        if inventory.location_id:
            values['location_name'] = inventory.location_id.name
        if inventory.mesline_id:
            values['mesline_name'] = inventory.mesline_id.name
        if inventory.inventory_labels and len(inventory.inventory_labels) > 0:
            values['inventorylist'] = [{
                'list_id': llist.id, 'product_code': llist.product_id.default_code,
                'product_lot': llist.product_lot.name, 'product_qty': llist.product_qty,
                'location_name': llist.location_id.name, 'label_name': llist.label_id.name,
                'container_name': llist.container_id.name
            } for llist in inventory.inventory_labels]
        if inventory.state != 'done':
            values['candel'] = True
        return request.render('aas_wms.aas_inventory', values)


    @http.route('/aaswms/inventory/scaning', type='json', auth="user")
    def aaswms_inventory_scaning(self, inventoryid, barcode):
        values = {'success': True, 'message': '', 'ilabel': False, 'candel': False}
        inventory = request.env['aas.stock.inventory'].browse(inventoryid)
        if inventory.state == 'done':
            values.update({'success': False, 'message': u'当前盘点已完成，请不要再扫描！'})
            return values
        barcode = barcode.upper()
        prestr = barcode[0:2]
        if prestr == 'AT':
            tvalues = request.env['aas.stock.inventory'].action_scan_container(inventory, barcode)
        else:
            tvalues = request.env['aas.stock.inventory'].action_scan_label(inventory, barcode)
        values.update(tvalues)
        if inventory.state != 'done':
            values['candel'] = True
        return values


    @http.route('/aaswms/inventory/scandel', type='json', auth="user")
    def aaswms_inventory_scandel(self, ilabelid):
        values = {'success': True, 'message': ''}
        ilabel = request.env['aas.stock.inventory.label'].browse(ilabelid)
        inventory = ilabel.inventory_id
        if inventory.state == 'done':
            values.update({'success': False, 'message': u'当前盘点已完成，请不要删除扫描记录！'})
            return values
        ilabel.unlink()
        return values

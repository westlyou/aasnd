# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-14 09:30
"""

import logging
import werkzeug

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessDenied,UserError,ValidationError

logger = logging.getLogger(__name__)

DELIVERYTYPEDICT = {'purchase': u'采购退货', 'manufacture': u'生产领料', 'sales': u'销售发货', 'sundry': u'杂项出库'}
DELIVERYSTATEDICT = {'draft': u'草稿', 'confirm': u'确认', 'picking': u'拣货', 'pickconfirm': u'待确认发货', 'done': u'完成', 'cancel': u'取消'}

def get_current_time(record, timestr):
    if not timestr:
        return ''
    temptime = fields.Datetime.from_string(timestr)
    return fields.Datetime.to_string(fields.Datetime.context_timestamp(record, temptime))

class AASDeliveryWechatController(http.Controller):

    @http.route('/aaswechat/wms/deliverylinelist', type='http', auth='user')
    def aas_wechat_wms_deliverylinelist(self, limit=20):
        values = {'success': True, 'message': '', 'deliverylines': [], 'lineindex': '0'}
        linesdomain = [('delivery_type', '!=', 'purhase'), ('company_id', '=', request.env.user.company_id.id)]
        linesdomain.append(('state', 'in', ['confirm', 'picking', 'pickconfirm']))
        deliverylines = request.env['aas.stock.delivery.line'].search(linesdomain, limit=limit)
        if deliverylines and len(deliverylines):
            values['deliverylines'] = [{
                'line_id': dline.id, 'delivery_name': dline.delivery_id.name, 'product_code': dline.product_id.default_code,
                'delivery_type': DELIVERYTYPEDICT[dline.delivery_type], 'product_qty': dline.product_qty - dline.delivery_qty
            } for dline in deliverylines]
            values['lineindex'] = len(deliverylines)
        return request.render('aas_wms.wechat_wms_delivery_line_list', values)


    @http.route('/aaswechat/wms/deliverylinemore', type='json', auth="user")
    def aas_wechat_wms_deliverylinemore(self, lineindex=0, product_code=None, limit=20):
        values = {'deliverylines': [], 'lineindex': lineindex, 'linecount': 0}
        linesdomain = [('delivery_type', '!=', 'purhase'), ('company_id', '=', request.env.user.company_id.id)]
        linesdomain.append(('state', 'in', ['confirm', 'picking', 'pickconfirm']))
        if product_code:
            linesdomain.append(('product_id', 'ilike', product_code))
        deliverylines = request.env['aas.stock.delivery.line'].search(linesdomain, offset=lineindex, limit=limit)
        if deliverylines and len(deliverylines):
            values['deliverylines'] = [{
                'line_id': dline.id, 'delivery_name': dline.delivery_id.name, 'product_code': dline.product_id.default_code,
                'delivery_type': DELIVERYTYPEDICT[dline.delivery_type], 'product_qty': dline.product_qty - dline.delivery_qty
            } for dline in deliverylines]
            values['linecount'] = len(deliverylines)
            values['lineindex'] = values['linecount'] + lineindex
        return values



    @http.route('/aaswechat/wms/deliverylinesearch', type='json', auth="user")
    def aas_wechat_wms_deliverylinesearch(self, product_code, limit=20):
        values = {'deliverylines': [], 'lineindex': '0'}
        linesdomain = [('delivery_type', '!=', 'purhase'), ('company_id', '=', request.env.user.company_id.id)]
        linesdomain.extend([('state', 'in', ['confirm', 'picking', 'pickconfirm']), ('product_id', 'ilike', product_code)])
        deliverylines = request.env['aas.stock.delivery.line'].search(linesdomain, limit=limit)
        if deliverylines and len(deliverylines):
            values['deliverylines'] = [{
                'line_id': dline.id, 'delivery_name': dline.delivery_id.name, 'product_code': dline.product_id.default_code,
                'delivery_type': DELIVERYTYPEDICT[dline.delivery_type], 'product_qty': dline.product_qty - dline.delivery_qty
            } for dline in deliverylines]
            values['lineindex'] = len(deliverylines)
        return values


    @http.route('/aaswechat/wms/deliveryline/<int:deliverylineid>', type='http', auth='user')
    def aas_wechat_wms_deliverylinedetail(self, deliverylineid):
        values = {'success': True, 'message': '', 'pickinglist': [], 'operationlist': []}
        deliveryline = request.env['aas.stock.delivery.line'].browse(deliverylineid)
        values.update({
            'deliverylineid': deliveryline.id, 'delivery_name': deliveryline.delivery_id.name,
            'product_code': deliveryline.product_id.default_code, 'product_uom': deliveryline.product_uom.name,
            'delivery_type': DELIVERYTYPEDICT[deliveryline.delivery_type], 'state_name': DELIVERYSTATEDICT[deliveryline.state],
            'product_qty': deliveryline.product_qty, 'delivery_qty': deliveryline.delivery_qty, 'picking_qty': deliveryline.picking_qty,
            'labelscan': 'none', 'pickconfirm': 'none', 'picklist': 'none'
        })
        if deliveryline.pickable:
            values.update({'labelscan': 'block', 'pickconfirm': 'block', 'picklist': 'block'})
        if deliveryline.picking_list and len(deliveryline.picking_list) > 0:
            values['pickinglines'] = [{
                'product_code': pline.product_id.default_code, 'product_lot': pline.product_lot.name,
                'product_qty': pline.product_qty, 'location_name': pline.location_id.name
            } for pline in deliveryline.picking_list]
        if deliveryline.operation_lines and len(deliveryline.operation_lines) > 0:
            values['operationlist'] = [{
                'operation_id': oline.id, 'deliver_done': oline.deliver_done, 'location_name': oline.location_id.name,
                'label_id': oline.label_id.id, 'label_name': oline.label_id.name, 'product_qty': oline.product_qty,
                'product_code': oline.product_id.default_code, 'product_lot': oline.product_lot.name
            } for oline in deliveryline.operation_lines]
        return request.render('aas_wms.wechat_wms_delivery_line_detail', values)


    @http.route('/aaswechat/wms/deliverypickinglist', type='json', auth="user")
    def aas_wechat_wms_deliverypickinglist(self, delivery_id=None, line_id=None):
        values = {'success': True, 'message': ''}
        if delivery_id:
            delivery = request.env['aas.stock.delivery'].browse(delivery_id)
            delivery.action_picking_list()
        if line_id:
            deliveryline = request.env['aas.stock.delivery.line'].browse(line_id)
            deliveryline.action_picking_list()
        return values


    @http.route('/aaswechat/wms/deliverylabelscan', type='json', auth="user")
    def aas_wechat_wms_deliverylabelscan(self, barcode, delivery_id=None, line_id=None):
        values = {'success': True, 'message': ''}
        if not delivery_id and not line_id:
            values.update({'success': False, 'message': u'异常出错，请检查请求参数设置！'})
            return values
        if line_id:
            deliveryline = request.env['aas.stock.delivery.line'].browse(line_id)
            delivery_id = deliveryline.delivery_id.id
        label = request.env['aas.product.label'].search([('barcode', '=', barcode)], limit=1)
        pickingdomain = [('delivery_id', '=', delivery_id), ('product_id', '=', label.product_id.id)]
        pickingdomain.extend([('product_lot', '=', label.product_lot.id), ('location_id', '=', label.location_id.id)])
        pickinglistcount = request.env['aas.stock.picking.list'].search_count(pickingdomain)
        if pickinglistcount <= 0:
            values.update({'success': False, 'message': u'您添加的的标签可能不在拣货清单之中，或许您该重新计算一下拣货清单！'})
            return values
        if not label:
            values.update({'success': False, 'message': u'标签可能已删除！'})
            return values
        if label.state!='normal':
            values.update({'success': False, 'message': u'标签状态异常不可以用于发货！'})
            return values
        if label.locked:
            values.update({'success': False, 'message': u'标签已被%s锁定不可以用于发货！'% label.locked_order})
            return values
        operationvals = {'label_id': label.id, 'delivery_id': delivery_id}
        if line_id:
            operationvals['delivery_line'] = line_id
        toperation = request.env['aas.stock.delivery.operation'].with_context({'no_check': True}).create(operationvals)
        values.update({
            'operation_id': toperation.id, 'delivery_line': toperation.delivery_line.id,
            'picking_qty': toperation.delivery_line.picking_qty, 'label_name': label.name, 'product_code': label.product_code,
            'product_qty': label.product_qty, 'product_lot': label.product_lot.name, 'location_name': label.location_id.name
        })
        return values

    @http.route('/aaswechat/wms/deliverydeloperation', type='json', auth="user")
    def aas_wechat_wms_deliverydeloperation(self, operation_id):
        values = {'success': True, 'message': ''}
        toperation = request.env['aas.stock.delivery.operation'].browse(operation_id)
        if not toperation:
            values.update({'success': False, 'message': u'拣货作业可能已经删除！'})
            return values
        delivery_line = toperation.delivery_line
        if delivery_line.picking_confirm:
            values.update({'success': False, 'message': u'拣货作业已确认正在等待执行完成，不可以删除！'})
            return values
        if toperation.deliver_done:
            values.update({'success': False, 'message': u'当前的拣货作业已经完成了发货操作，不可以删除！'})
            return values
        toperation.unlink()
        values.update({'line_id': delivery_line.id, 'picking_qty': delivery_line.picking_qty})
        return values


    @http.route('/aaswechat/wms/deliverypickconfirm', type='json', auth="user")
    def aas_wechat_wms_deliverypickconfirm(self, delivery_id=None, line_id=None):
        values = {'success': True, 'message': ''}
        if delivery_id:
            try:
                delivery = request.env['aas.stock.delivery'].browse(delivery_id)
                delivery.action_picking_confirm()
            except UserError, ue:
                values.update({'success': False, 'message': ue.name})
                return values
        if line_id:
            try:
                deliveryline = request.env['aas.stock.delivery.line'].browse(line_id)
                deliveryline.action_picking_confirm()
            except UserError, ue:
                values.update({'success': False, 'message': ue.name})
                return values
        return values


    @http.route('/aaswechat/wms/deliverypickdone', type='json', auth="user")
    def aas_wechat_wms_deliverypickdone(self, delivery_id):
        values = {'success': True, 'message': ''}
        delivery = request.env['aas.stock.delivery'].browse(delivery_id)
        try:
            delivery.action_deliver_done()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        return values



    @http.route('/aaswechat/wms/deliverylist', type='http', auth='user')
    def aas_wechat_wms_deliverylist(self, limit=20):
        values = {'success': True, 'message': '', 'deliverylines': [], 'deliveryindex': '0'}
        deliverydomain = [('delivery_type', '!=', 'purhase'), ('company_id', '=', request.env.user.company_id.id)]
        deliverydomain.append(('state', 'in', ['confirm', 'picking', 'pickconfirm']))
        deliverylist = request.env['aas.stock.delivery'].search(deliverydomain, limit=limit)
        if deliverylist and len(deliverylist):
            values['deliverylist'] = [{
                'delivery_id': dlist.id, 'delivery_name': dlist.name,
                'state_name': DELIVERYSTATEDICT[dlist.state], 'delivery_type': DELIVERYTYPEDICT[dlist.delivery_type]
            } for dlist in deliverylist]
            values['deliveryindex'] = len(deliverylist)
        return request.render('aas_wms.wechat_wms_delivery_list', values)


    @http.route('/aaswechat/wms/deliverymore', type='json', auth="user")
    def aas_wechat_wms_deliverymore(self, deliveryindex=0, limit=20):
        values = {'deliverylines': [], 'deliveryindex': deliveryindex, 'deliverycount': 0}
        deliverydomain = [('delivery_type', '!=', 'purhase'), ('company_id', '=', request.env.user.company_id.id)]
        deliverydomain.append(('state', 'in', ['confirm', 'picking', 'pickconfirm']))
        deliverylist = request.env['aas.stock.delivery'].search(deliverydomain, limit=limit)
        if deliverylist and len(deliverylist):
            values['deliverylist'] = [{
                'delivery_id': dlist.id, 'delivery_name': dlist.name,
                'state_name': DELIVERYSTATEDICT[dlist.state], 'delivery_type': DELIVERYTYPEDICT[dlist.delivery_type]
            } for dlist in deliverylist]
            values['deliverycount'] = len(deliverylist)
            values['deliveryindex'] = values['deliverycount'] + deliveryindex
        return values


    @http.route('/aaswechat/wms/deliverydetail/<int:deliveryid>', type='http', auth='user')
    def aas_wechat_wms_deliverydetail(self, deliveryid):
        values = {'success': True, 'message': '', 'linelist': [], 'pickinglist': [], 'operationlist': []}
        delivery = request.env['aas.stock.delivery'].browse(deliveryid)
        values.update({'deliveryid': delivery.id, 'delivery_name': delivery.name, 'delivery_type': DELIVERYTYPEDICT[delivery.delivery_type]})
        values.update({'state_name': DELIVERYSTATEDICT[delivery.state], 'partner_name': '' if not delivery.partner_id else delivery.partner_id.name})
        values.update({'order_user': delivery.order_user.name, 'order_time': get_current_time(delivery, delivery.order_time)})
        values.update({'location_name': '' if not delivery.location_id else delivery.location_id.name})
        values.update({'labelscan': 'none', 'pickconfirm': 'none', 'picklist': 'none', 'pickdone': 'none'})
        pickable = False
        if delivery.delivery_lines and len(delivery.delivery_lines) > 0:
            deliverylines = []
            for dline in delivery.delivery_lines:
                if dline.pickable:
                    pickable = True
                deliverylines.append({
                    'line_id': dline.id,
                    'product_code': dline.product_id.default_code, 'product_qty': dline.product_qty,
                    'delivery_qty': dline.delivery_qty, 'picking_qty': dline.picking_qty
                })
            values['linelist'] = deliverylines
        if pickable:
            values.update({'labelscan': 'block', 'pickconfirm': 'block', 'picklist': 'block'})
        if delivery.picking_confirm:
            values['pickdone'] = 'block'
        if delivery.picking_list and len(delivery.picking_list) > 0:
            values['pickinglist'] = [{
                'product_code': plist.product_id.default_code, 'product_qty': plist.product_qty,
                'product_lot': plist.product_lot.name, 'location_name': plist.location_id.name
            } for plist in delivery.picking_list]
        if delivery.operation_lines and len(delivery.operation_lines) > 0:
            values['operationlist'] = [{
                'label_name': oline.label_id.name, 'product_code': oline.product_id.default_code,
                'product_qty': oline.product_qty, 'product_lot': oline.product_lot.name,
                'deliver_done': oline.deliver_done, 'operation_id': oline.id
            } for oline in delivery.operation_lines]
        return request.render('aas_wms.wechat_wms_delivery_detail', values)


    @http.route('/aaswechat/wms/deliverypurchase', type='http', auth='user')
    def aas_wechat_wms_deliverypurchase(self):
        values = {'success': True, 'message': ''}
        return request.render('aas_wms.wechat_wms_delivery_purchase', values)


    @http.route('/aaswechat/wms/deliverypurchaselabelscan', type='json', auth="user")
    def aas_wechat_wms_deliverypurchaselabelscan(self, barcode):
        values = {'success': True, 'message': ''}
        label = request.env['aas.product.label'].search([('barcode', '=', barcode)], limit=1)
        if not label:
            values.update({'success': False, 'message': u'标签可能已删除！'})
            return values
        if label.state!='normal':
            values.update({'success': False, 'message': u'标签状态异常不可以用于发货！'})
            return values
        if label.locked:
            values.update({'success': False, 'message': u'标签已被%s锁定不可以用于发货！'% label.locked_order})
            return values
        if not label.origin_order or not label.partner_id:
            values.update({'success': False, 'message': u'请仔细检查当前标签是否是采购收货进来的！'})
            return values
        values.update({
            'label_id': label.id, 'label_name': label.name,
            'product_code': label.product_code, 'product_qty': label.product_qty, 'product_lot': label.product_lot.name,
            'origin_order': label.origin_order, 'partner_id': label.partner_id.id, 'partner_name': label.partner_id.name
        })
        return values


    @http.route('/aaswechat/wms/deliverypurchasedone', type='json', auth="user")
    def aas_wechat_wms_deliverypurchasedone(self, partnerid, purchaseorder, labelids):
        values = {'success': True, 'message': ''}
        deliveryvals = {
            'partner_id': partnerid, 'state': 'picking', 'delivery_type': 'purchase',
            'origin_order': purchaseorder, 'pick_user': request.env.user.id
        }
        supplier_location = request.env.ref('stock.stock_location_suppliers')
        deliveryvals['location_id'] = supplier_location.id
        labellist = request.env['aas.product.label'].browse(labelids)
        dlinesdict, operationlines = {}, []
        for tlabel in labellist:
            pkey = 'P'+str(tlabel.product_id.id)
            if pkey in dlinesdict:
                dlinesdict[pkey]['product_qty'] += tlabel.product_qty
            else:
                dlinesdict[pkey] = {
                    'product_id': tlabel.product_id.id, 'product_uom': tlabel.product_uom.id, 'product_qty': tlabel.product_qty,
                    'state': 'picking', 'delivery_type': 'purchase', 'picking_confirm': True
                }
            operationlines.append((0, 0, {'label_id': tlabel.id}))
        deliveryvals['delivery_lines'] = [(0, 0, dval) for dkey, dval in dlinesdict.items()]
        try:
            delivery = request.env['aas.stock.delivery'].create(deliveryvals)
            delivery.write({'operation_lines': operationlines})
            delivery.action_deliver_done()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        return values


    @http.route('/aaswechat/wms/deliverysaleslist', type='http', auth='user')
    def aas_wechat_wms_deliverysaleslist(self, limit=20):
        values = {'success': True, 'message': '', 'salesindex': 0, 'deliverysales': []}
        salesdomain = [('aas_delivery_id', '=', False)]
        deliverysales = request.env['aas.stock.sale.delivery'].search(salesdomain, limit=limit)
        if deliverysales and len(deliverysales):
            values['deliverysales'] = [{
                'sales_id': dsales.id, 'sales_name': dsales.name, 'partner_name': '' if not dsales.partner_id else dsales.partner_id.name
            } for dsales in deliverysales]
            values['salesindex'] = len(deliverysales)
        return request.render('aas_wms.wechat_wms_delivery_sales_list', values)


    @http.route('/aaswechat/wms/deliverysalesmore', type='json', auth="user")
    def aas_wechat_wms_deliverysalesmore(self, salesindex=0, limit=20):
        values = {'deliverysales': [], 'salesindex': salesindex, 'salescount': 0}
        salesdomain = [('aas_delivery_id', '=', False)]
        deliverysales = request.env['aas.stock.sale.delivery'].search(salesdomain, offset=salesindex, limit=limit)
        if deliverysales and len(deliverysales):
            values['deliverysales'] = [{
                'sales_id': dsales.id, 'sales_name': dsales.name, 'partner_name': '' if not dsales.partner_id else dsales.partner_id.name
            } for dsales in deliverysales]
            values['salescount'] = len(deliverysales)
            values['salesindex'] = salesindex + values['salescount']
        return values


    @http.route('/aaswechat/wms/deliverysalesimport', type='http', auth='user')
    def aas_wechat_wms_deliverysalesimport(self):
        values = {'success': True, 'message': ''}
        return request.render('aas_wms.wechat_wms_delivery_sales_import', values)


    @http.route('/aaswechat/wms/deliverysalesimportdone', type='json', auth="user")
    def aas_wechat_wms_deliverysalesimportdone(self, order_name):
        values = {'success': True, 'message': ''}
        try:
            tempvals = request.env['aas.stock.sale.delivery'].action_import_order(order_name)
            values.update(tempvals)
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        return values


    @http.route('/aaswechat/wms/deliverysalesdetail/<int:salesid>', type='http', auth='user')
    def aas_wechat_wms_deliverysalesdetail(self, salesid):
        values = {'success': True, 'message': '', 'saleslines': []}
        deliverysales = request.env['aas.stock.sale.delivery'].browse(salesid)
        values.update({
            'sales_name': deliverysales.name, 'shipment_date': get_current_time(deliverysales, deliverysales.shipment_date),
            'sales_id': deliverysales.id, 'partner_name': '' if not deliverysales.partner_id else deliverysales.partner_id.name
        })
        if deliverysales.delivery_lines and len(deliverysales.delivery_lines) > 0:
            values['saleslines'] = [{
                'product_code': dline.product_id.default_code, 'product_qty': dline.product_qty
            } for dline in deliverysales.delivery_lines]
        return request.render('aas_wms.wechat_wms_delivery_sales_detail', values)


    @http.route('/aaswechat/wms/deliverysalesdone', type='json', auth="user")
    def aas_wechat_wms_deliverysalesdone(self, salesid):
        values = {'success': True, 'message': ''}
        deliverysales = request.env['aas.stock.sale.delivery'].browse(salesid)
        try:
            deliverysales.action_build_delivery()
            values['delivery_id'] = deliverysales.aas_delivery_id.id
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        return values
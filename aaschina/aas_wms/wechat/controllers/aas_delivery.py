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
from odoo.exceptions import AccessDenied, UserError, ValidationError

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
            linesdomain.append(('product_id', 'ilike', '%'+product_code+'%'))
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
        values = {'success': True, 'message': '' ,'deliverylines': [], 'lineindex': '0'}
        linesdomain = [('delivery_type', '!=', 'purhase'), ('company_id', '=', request.env.user.company_id.id)]
        linesdomain.extend([('state', 'in', ['confirm', 'picking', 'pickconfirm']), ('product_code', 'ilike', '%'+product_code+'%')])
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
        values = {'success': True, 'message': '', 'pickinglist': [], 'operationlist': [], 'label_count': 0}
        deliveryline = request.env['aas.stock.delivery.line'].browse(deliverylineid)
        values.update({
            'deliveryid': deliveryline.delivery_id.id,
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
        values['label_count'] = request.env['aas.stock.delivery.operation'].search_count([('delivery_line', '=', deliverylineid), ('deliver_done', '=', False)])
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
        values = {'success': True, 'message': '', 'label_count': 0}
        if not delivery_id and not line_id:
            values.update({'success': False, 'message': u'异常出错，请检查请求参数设置！'})
            return values
        product_ids = []
        if line_id:
            deliveryline = request.env['aas.stock.delivery.line'].browse(line_id)
            delivery_id = deliveryline.delivery_id.id
            product_ids.append(deliveryline.product_id.id)
        else:
            deliveryproducts = request.env['aas.stock.delivery.line'].search_read([('delivery_id', '=', delivery_id)], fields=['product_id'])
            product_ids.extend([dproduct['product_id'][0] for dproduct in deliveryproducts])
        label = request.env['aas.product.label'].search([('barcode', '=', barcode), ('product_id', 'in', product_ids)], limit=1)
        if not label:
            values.update({'success': False, 'message': u'扫描异常，未查询到此标签！'})
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
        tempdelivery = request.env['aas.stock.delivery'].browse(delivery_id)
        if tempdelivery.delivery_type != 'purchase':
            pickingdomain = [('product_id', '=', label.product_id.id), ('product_lot', '=', label.product_lot.id)]
            pickingdomain.extend([('location_id', '=', label.location_id.id), ('delivery_id', '=', delivery_id)])
            if request.env['aas.stock.picking.list'].search_count(pickingdomain) <= 0:
                values.update({'success': False, 'message': u'标签%s不在拣货清单中，请检查！！'% label.name})
                return values
        operationvals = {'label_id': label.id, 'delivery_id': delivery_id}
        if line_id:
            operationvals['delivery_line'] = line_id
        try:
            toperation = request.env['aas.stock.delivery.operation'].create(operationvals)
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        except ValidationError, ve:
            values.update({'success': False, 'message': ve.name})
            return values
        values.update({
            'operation_id': toperation.id, 'delivery_line': toperation.delivery_line.id,
            'picking_qty': toperation.delivery_line.picking_qty, 'label_name': label.name, 'product_code': label.product_code,
            'product_qty': label.product_qty, 'product_lot': label.product_lot.name, 'location_name': label.location_id.name
        })
        if line_id:
            values['label_count'] = request.env['aas.stock.delivery.operation'].search_count([('delivery_line', '=', line_id), ('deliver_done', '=', False)])
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
        try:
            toperation.unlink()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        except ValidationError, ve:
            values.update({'success': False, 'message': ve.name})
            return values
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
        if delivery.delivery_type == 'manufacture':
            values['pickconfirm']
        if delivery.picking_confirm and delivery.delivery_type != 'manufacture':
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
        if label.state != 'normal':
            values.update({'success': False, 'message': u'标签状态异常不可以用于发货！'})
            return values
        if label.locked:
            values.update({'success': False, 'message': u'标签已被%s锁定不可以用于发货！'% label.locked_order})
            return values
        if label.partner_id:
            partnerid, partnername = label.partner_id.id, label.partner_id.name
        else:
            partnerid, partnername = False, False
        if not label.origin_order or not label.partner_id:
            values.update({'success': False, 'message': u'请仔细检查当前标签是否是采购收货进来的！'})
            return values
        values.update({
            'label_id': label.id, 'label_name': label.name,
            'product_code': label.product_code, 'product_qty': label.product_qty, 'product_lot': label.product_lot.name,
            'origin_order': label.origin_order, 'partner_id': partnerid, 'partner_name': partnername
        })
        return values


    @http.route('/aaswechat/wms/deliverypurchasedone', type='json', auth="user")
    def aas_wechat_wms_deliverypurchasedone(self, partnerid, purchaseorder, labelids):
        values = {'success': True, 'message': ''}
        deliveryvals = {
            'partner_id': partnerid, 'delivery_type': 'purchase',
            'origin_order': purchaseorder, 'pick_user': request.env.user.id
        }
        supplier_location = request.env.ref('stock.stock_location_suppliers')
        deliveryvals['location_id'] = supplier_location.id
        labellist = request.env['aas.product.label'].browse(labelids)
        dlinesdict = {}
        for tlabel in labellist:
            pkey = 'P'+str(tlabel.product_id.id)
            if pkey in dlinesdict:
                dlinesdict[pkey]['product_qty'] += tlabel.product_qty
            else:
                dlinesdict[pkey] = {
                    'product_id': tlabel.product_id.id, 'product_uom': tlabel.product_uom.id, 'product_qty': tlabel.product_qty
                }
        deliveryvals['delivery_lines'] = [(0, 0, dval) for dkey, dval in dlinesdict.items()]
        try:
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



    @http.route('/aaswechat/wms/deliverylocation/<string:barcode>/<string:deliverylineidstr>', type='http', auth='user')
    def aas_wechat_wms_deliverylocation(self, barcode, deliverylineidstr):
        values = {'success': True, 'message': '', 'labellist': [], 'deliveryid': '0', 'dlineid': '0'}
        stocklocation = request.env['stock.location'].search([('barcode', '=', barcode)], limit=1)
        if not stocklocation:
            values.update({'success': False, 'message': u'请仔细检查系统是否存在此库位！'})
            return request.render('aas_wms.wechat_wms_message', values)
        values.update({'location_id': stocklocation.id, 'location_name': stocklocation.name})
        tempids = deliverylineidstr.split('-')
        deliveryid, dlineid = int(tempids[0]), int(tempids[1])
        values.update({'delivery_name': '', 'product_code': ''})
        if deliveryid:
            values['deliveryid'] = deliveryid
            delivery = request.env['aas.stock.delivery'].browse(deliveryid)
            operationlist = delivery.operation_lines
            values.update({'deliveryid': deliveryid, 'delivery_name': delivery.name})
            picklist = request.env['aas.stock.picking.list'].search([('delivery_id', '=', deliveryid), ('location_id', '=', stocklocation.id)])
        else:
            deliveryline = request.env['aas.stock.delivery.line'].browse(dlineid)
            operationlist = deliveryline.operation_lines
            values.update({'dlineid': dlineid, 'product_code': deliveryline.product_id.default_code})
            picklist = request.env['aas.stock.picking.list'].search([('delivery_line', '=', dlineid), ('location_id', '=', stocklocation.id)])
        if not picklist or len(picklist) <= 0:
            values.update({'success': False, 'message': u'当前可能还未生成拣货清单，或者扫描的库位不在拣货清单列表中！'})
            return request.render('aas_wms.wechat_wms_message', values)
        tlabelids = []
        if operationlist and len(operationlist) > 0:
            tlabelids = [toperation.label_id.id for toperation in operationlist]
        tempdomain = [('state', '=', 'normal'), ('qualified', '=', True), ('stocked', '=', True)]
        tempdomain.extend([('locked', '=', False), ('parent_id', '=', False), ('location_id', '=', stocklocation.id)])
        for tlist in picklist:
            labeldomain = [('product_id', '=', tlist.product_id.id), ('product_lot', '=', tlist.product_lot.id)]
            labeldomain += tempdomain
            labelist = request.env['aas.product.label'].search(labeldomain)
            if labelist and len(labelist) > 0:
                for tlabel in labelist:
                    if tlabel.id in tlabelids:
                        continue
                    values['labellist'].append({
                        'label_id': tlabel.id, 'label_name': tlabel.name, 'product_code': tlabel.product_code,
                        'product_lot': tlabel.product_lotname, 'product_qty': tlabel.product_qty
                    })
        if not values['labellist'] or len(values['labellist']) <= 0:
            values.update({'success': False, 'message': u'未搜索到符合条件的标签！'})
            return request.render('aas_wms.wechat_wms_message', values)
        return request.render('aas_wms.wechat_wms_deliverylocation', values)


    @http.route('/aaswechat/wms/deliverylocationdone', type='json', auth="user")
    def aas_wechat_wms_deliverylocationdone(self, deliveryids, labelids):
        values = {'success': True, 'message': ''}
        labelist = request.env['aas.product.label'].browse(labelids)
        if not labelist or len(labelist) <= 0:
            return values
        tempids = deliveryids.split('-')
        deliveryid, dlineid = int(tempids[0]), int(tempids[1])
        productlinedict = {}
        if deliveryid:
            delivery = request.env['aas.stock.delivery'].browse(deliveryid)
        else:
            deliveryline = request.env['aas.stock.delivery.line'].browse(dlineid)
            delivery = deliveryline.delivery_id
            productlinedict[deliveryline.product_id.id] = deliveryline.id
        for tlabel in labelist:
            if tlabel.product_id.id not in productlinedict:
                tdeliveryline = request.env['aas.stock.delivery.line'].search([('delivery_id', '=', delivery.id), ('product_id', '=', tlabel.product_id.id)], limit=1)
                productlinedict[tlabel.product_id.id] = tdeliveryline.id
            try:
                request.env['aas.stock.delivery.operation'].create({
                    'label_id': tlabel.id, 'delivery_id': delivery.id, 'delivery_line': productlinedict[tlabel.product_id.id]
                })
            except UserError, ue:
                values.update({'success': False, 'message': ue.name})
                return values
            except ValidationError, ve:
                values.update({'success': False, 'message': ve.name})
                return values
        return values
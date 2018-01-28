# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-13 11:05
"""

import logging
import werkzeug

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessDenied,UserError,ValidationError

logger = logging.getLogger(__name__)

LABELSTATEDICT = {'draft': u'草稿', 'normal': u'正常', 'frozen': u'冻结', 'over': u'消亡'}

def get_current_time(record, timestr):
    if not timestr:
        return ''
    temptime = fields.Datetime.from_string(timestr)
    return fields.Datetime.to_string(fields.Datetime.context_timestamp(record, temptime))

class AASLabelWechatController(http.Controller):


    @http.route('/aaswechat/wms/labellist', type='http', auth="user")
    def aas_wechat_wms_labellist(self, limit=20):
        values = {'labels': [], 'labelindex': '0'}
        label_list = request.env['aas.product.label'].search([('isproduction', '=', False)], limit=limit)
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
        labeldomain = [('isproduction', '=', False)]
        if searchkey:
            labeldomain = ['&', ('isproduction', '=', False)]
            labeldomain += ['|', ('product_code', 'ilike', searchkey), ('product_lotname', 'ilike', searchkey)]
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

    @http.route('/aaswechat/wms/labelsearch', type='json', auth="user")
    def aas_wechat_labelsearch(self, searchkey, limit=20):
        values = {'success': True, 'message': '', 'labels': [], 'labelindex': 0}
        labeldomain = []
        if searchkey:
            labeldomain = ['|', ('product_code', 'ilike', '%'+searchkey+'%'), ('product_lotname', 'ilike', '%'+searchkey+'%')]
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


    @http.route(['/aaswechat/wms/labeldetail/<int:labelid>', '/aaswechat/wms/labeldetail/<string:labelname>'], type='http', auth="user")
    def aas_wechat_wms_labeldetail(self, labelid=None, labelname=None):
        if labelid:
            label = request.env['aas.product.label'].browse(labelid)
        else:
            label = request.env['aas.product.label'].search([('name', '=', labelname)], limit=1)
        values = {'label_id': label.id, 'label_name': label.name, 'product_code': label.product_code, 'product_qty': label.product_qty}
        values.update({'label_state': label.state, 'state_name': LABELSTATEDICT[label.state], 'label_location': label.location_id.name})
        values.update({'datecode': label.date_code, 'partner_name': label.partner_id and label.partner_id.name})
        values.update({'qualified': u'合格' if label.qualified else u'不合格', 'locked_order': label.locked_order, 'product_lot': label.product_lot.name})
        values.update({'onshelf_time': get_current_time(label, label.onshelf_time), 'offshelf_time': get_current_time(label, label.offshelf_time)})
        stock_date, warranty_date = get_current_time(label, label.stock_date), get_current_time(label, label.warranty_date)
        if stock_date:
            values['stock_date'] = stock_date[0:10]
        if warranty_date:
            values['warranty_date'] = warranty_date[0:10]
        values.update({'product_id': label.product_id.id, 'origin_order': label.origin_order})
        values.update({'journal_lines': [], 'split_lines': [], 'child_lines': []})
        if label.journal_lines and len(label.journal_lines) > 0:
            values['journal_lines'] = [{
                'locationsrc': '' if not jline.location_src_id else jline.location_src_id.name,
                'locationdest': '' if not jline.location_dest_id else jline.location_dest_id.name,
                'journal_qty': jline.journal_qty, 'balance_qty': jline.balance_qty
            } for jline in label.journal_lines]
        if label.child_lines and len(label.child_lines) > 0:
            values['child_lines'] = [{
                'label_id': cline.id, 'label_name': cline.name, 'product_code': cline.product_code,
                'product_lot': cline.product_lot.name, 'product_qty': cline.product_qty
            } for cline in label.child_lines]
        if label.origin_lines and len(label.origin_lines) > 0:
            values['split_lines'] = [{
                'label_id': sline.id, 'label_name': sline.name, 'product_code': sline.product_code,
                'product_lot': sline.product_lot.name, 'product_qty': sline.product_qty
            } for sline in label.origin_lines]
        values.update({'actionsplit': 'none', 'actionfrozen': 'none', 'actionunfrozen': 'none'})
        loginuser = request.env.user
        if (loginuser._is_superuser() or loginuser._is_admin()) and not label.locked:
            values.update({
                'actionsplit': 'block',
                'actionfrozen': 'block' if label.state == 'normal' else 'none',
                'actionunfrozen': 'block' if label.state == 'frozen' else 'none'
            })
        elif loginuser.has_group('stock.group_stock_user') and not label.locked:
            values.update({'actionsplit': 'block'})
        elif loginuser.has_group('aas_quality.group_aas_quality_user') and not label.locked:
            values.update({
                'actionfrozen': 'block' if label.state == 'normal' else 'none',
                'actionunfrozen': 'block' if label.state == 'frozen' else 'none'
            })
        return request.render('aas_wms.wechat_wms_label_detail', values)


    @http.route('/aaswechat/wms/printlabels', type='json', auth="user")
    def aas_wechat_printlabels(self, printerid, labelids=[]):
        values = {'success': True, 'message': ''}
        try:
            tempvals = request.env['aas.product.label'].action_print_label(printerid, ids=labelids)
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        values.update(tempvals)
        printer = request.env['aas.label.printer'].browse(printerid)
        values.update({'printer': printer.name, 'printurl': printer.serverurl})
        return values


    @http.route('/aaswechat/wms/labelsplit/<int:labelid>', type='http', auth="user")
    def aas_wechat_wms_labelsplit(self, labelid):
        label = request.env['aas.product.label'].browse(labelid)
        values = {'label_id': label.id, 'label_name': label.name, 'product_code': label.product_code}
        values.update({'product_lot': label.product_lot.name, 'product_qty': label.product_qty})
        return request.render('aas_wms.wechat_wms_label_split', values)


    @http.route('/aaswechat/wms/labelsplitdone', type='json', auth="user")
    def aas_wechat_wms_labelsplitdone(self, labelid, label_qty, label_count=0):
        values = {'success': True, 'message': ''}
        label = request.env['aas.product.label'].browse(labelid)
        try:
            label.action_dosplit(label_qty, label_count)
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        values['labelid'] = labelid
        return values


    @http.route('/aaswechat/wms/frozenlabels', type='json', auth="user")
    def aas_wechat_frozenlabels(self, labelids):
        values = {'success': True, 'message': ''}
        labels = request.env['aas.product.label'].browse(labelids)
        labels.action_frozen()
        return values


    @http.route('/aaswechat/wms/unfrozenlabels', type='json', auth="user")
    def aas_wechat_unfrozenlabels(self, labelids):
        values = {'success': True, 'message': ''}
        labels = request.env['aas.product.label'].browse(labelids)
        labels.action_unfreeze()
        return values


    @http.route('/aaswechat/wms/labelmerge', type='http', auth="user")
    def aas_wechat_wms_labelmerge(self):
        values = request.params.copy()
        return request.render('aas_wms.wechat_wms_label_merge', values)


    @http.route('/aaswechat/wms/labelmergelocation', type='json', auth="user")
    def aas_wechat_labelmergelocation(self, barcode):
        values = {'success': True, 'message': ''}
        location = request.env['stock.location'].search([('barcode', '=', barcode)], limit=1)
        values.update({'location_id': location.id, 'location_name': location.name})
        return values


    @http.route('/aaswechat/wms/labelmergelabel', type='json', auth="user")
    def aas_wechat_labelmergelocation(self, barcode):
        values = {'success': True, 'message': ''}
        label = request.env['aas.product.label'].search([('barcode', '=', barcode)], limit=1)
        if label.state != 'normal':
            values.update({'success': False, 'message': u'标签状态异常不可以用于合并！'})
            return values
        if label.stocked:
            values.update({'success': False, 'message': u'无效标签不可以合并！'})
            return values
        if label.locked:
            values.update({'success': False, 'message': u'标签被单据%s锁定，暂时不可以操作！'% label.locked_order})
            return values
        values.update({'label_id': label.id, 'label_name': label.name, 'product_id': label.product_id.id})
        values.update({'product_code': label.product_code, 'lot_id': label.product_lot.id, 'lot_name': label.product_lot.name})
        values.update({'product_qty': label.product_qty, 'location_name': label.location_id.name})
        return values


    @http.route('/aaswechat/wms/labelmergedone', type='json', auth="user")
    def aas_wechat_labelmergedone(self, labelids, locationid):
        values = {'success': True, 'message': ''}
        try:
            labels = request.env['aas.product.label'].browse(labelids)
            location = request.env['stock.location'].browse(locationid)
            templabel = request.env['aas.product.label'].action_merge_labels(labels, location)
            values['labelid'] = templabel.id
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        return values



    @http.route('/aaswechat/wms/product/stocklist/<int:productid>', type='http', auth="user")
    def aas_wechat_wms_product_stocklist(self, productid):
        values = {'product_id': productid, 'stock_qty': 0.0, 'lotlist': []}
        product = request.env['product.product'].browse(productid)
        values['product_code'] = product.default_code
        labeldomain = [('product_id', '=', productid), ('stocked', '=', True), ('state', 'in', ['normal', 'frozen'])]
        labeldomain += [('isproduction', '=', False), ('parent_id', '=', False)]
        labelist = request.env['aas.product.label'].search(labeldomain)
        if labelist and len(labelist) > 0:
            lotdict = {}
            for tlabel in labelist:
                values['stock_qty'] += tlabel.product_qty
                lkey = 'L-'+str(tlabel.product_lot.id)+'-'+str(tlabel.location_id.id)
                if lkey not in lotdict:
                    lotdict[lkey] = {
                        'product_qty': tlabel.product_qty,
                        'lot_id': tlabel.product_lot.id, 'lot_name': tlabel.product_lot.name,
                        'location_id': tlabel.location_id.id, 'location_name': tlabel.location_id.name
                    }
                else:
                    lotdict[lkey]['product_qty'] += tlabel.product_qty
            values['lotlist'] = lotdict.values()
        return request.render('aas_wms.wechat_wms_product_stock_list', values)


    @http.route('/aaswechat/wms/product/stocklabels/<string:locationlot>', type='http', auth="user")
    def aas_wechat_wms_product_stocklabels(self, locationlot):
        values = {'stock_qty': 0.0, 'labelist': []}
        params = locationlot.split('-')
        location_id, lot_id = int(params[0]), int(params[1])
        productlot = request.env['stock.production.lot'].browse(lot_id)
        location = request.env['stock.location'].browse(location_id)
        product = productlot.product_id
        values.update({
            'product_id': product.id, 'product_code': product.default_code,
            'location_id': location_id, 'location_name': location.name,
            'lot_id': productlot.id, 'lot_name': productlot.name
        })
        labeldomain = [('product_id', '=', product.id), ('stocked', '=', True), ('state', 'in', ['normal', 'frozen'])]
        labeldomain += [('isproduction', '=', False), ('parent_id', '=', False)]
        labeldomain += [('location_id', '=', location_id), ('product_lot', '=', lot_id)]
        labelist = request.env['aas.product.label'].search(labeldomain)
        if labelist and len(labelist) > 0:
            for tlabel in labelist:
                values['stock_qty'] += tlabel.product_qty
                values['labelist'].append({
                    'label_id': tlabel.id, 'label_name': tlabel.name, 'product_qty': tlabel.product_qty
                })
        return request.render('aas_wms.wechat_wms_product_stock_labels', values)


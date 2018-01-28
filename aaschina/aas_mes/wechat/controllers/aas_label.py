# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-1-28 10:51
"""

import logging

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

LABELSTATEDICT = {'draft': u'草稿', 'normal': u'正常', 'frozen': u'冻结', 'over': u'消亡'}

class AASLabelWechatController(http.Controller):

    @http.route('/aaswechat/mes/labelist', type='http', auth='user')
    def aas_wechat_mes_labelist(self, limit=20):
        values = {'success': True, 'message': '', 'labelist': [], 'labelindex': 0}
        labeldomain = [('isproduction', '=', True)]
        labelist = request.env['aas.product.label'].search(labeldomain, limit=limit)
        if labelist and len(labelist) > 0:
            values['labelist'] = [{
                'label_id': tlabel.id,
                'label_name': tlabel.name, 'product_qty': tlabel.product_qty,
                'product_code': tlabel.product_code, 'product_lot': tlabel.product_lot.name
            } for tlabel in labelist]
            values['labelindex'] = len(labelist)
        return request.render('aas_mes.wechat_mes_labelist', values)


    @http.route('/aaswechat/mes/labelmore', type='json', auth="user")
    def aas_wechat_mes_labelmore(self, searchkey=None, labelindex=0, limit=20):
        values = {'success': True, 'message': '', 'labelist': [], 'labelindex': labelindex, 'labelcount': 0}
        labeldomain = [('isproduction', '=', True)]
        if searchkey:
            labeldomain = ['&', ('isproduction', '=', True)]
            labeldomain += ['|', ('product_code', 'ilike', searchkey), ('product_lotname', 'ilike', searchkey)]
        labelist = request.env['aas.product.label'].search(labeldomain, offset=labelindex, limit=limit)
        if labelist and len(labelist) > 0:
            values['labelist'] = [{
                'label_id': tlabel.id,
                'label_name': tlabel.name, 'product_qty': tlabel.product_qty,
                'product_code': tlabel.product_code, 'product_lot': tlabel.product_lot.name
            } for tlabel in labelist]
            values['labelcount'] = len(labelist)
            values['labelindex'] = labelindex + values['labelcount']
        return values


    @http.route('/aaswechat/mes/labelsearch', type='json', auth="user")
    def aas_wechat_mes_labelsearch(self, searchkey, limit=20):
        values = {'success': True, 'message': '', 'labelist': [], 'labelindex': 0}
        labeldomain = []
        if searchkey:
            labeldomain = ['|', ('product_code', 'ilike', '%'+searchkey+'%'), ('product_lotname', 'ilike', '%'+searchkey+'%')]
        label_list = request.env['aas.product.label'].search(labeldomain, limit=limit)
        if label_list:
            values['labelist'] = [{
                'label_id': label.id,
                'label_name': label.name, 'product_code': label.product_code,
                'product_lot': label.product_lot.name, 'product_qty': label.product_qty
            } for label in label_list]
            values['labelindex'] = len(label_list)
        return values



    @http.route(['/aaswechat/mes/labeldetail/<int:labelid>', '/aaswechat/mes/labeldetail/<string:labelname>'],
                type='http', auth="user")
    def aas_wechat_mes_labeldetail(self, labelid=None, labelname=None):
        if labelid:
            label = request.env['aas.product.label'].browse(labelid)
        else:
            label = request.env['aas.product.label'].search([('name', '=', labelname)], limit=1)
        values = {
            'label_id': label.id, 'label_name': label.name, 'product_code': label.product_code,
            'product_qty': label.product_qty, 'label_state': label.state, 'state_name': LABELSTATEDICT[label.state],
            'label_location': label.location_id.name, 'datecode': label.date_code,
            'partner_name': '' if not label.partner_id else label.partner_id.name,
            'qualified': u'合格' if label.qualified else u'不合格', 'locked_order': label.locked_order,
            'product_lot': label.product_lot.name, 'onshelf_time': fields.Datetime.to_china_string(label.onshelf_time),
            'offshelf_time': fields.Datetime.to_china_string(label.offshelf_time), 'stock_date': '',
            'product_id': label.product_id.id, 'origin_order': label.origin_order, 'warranty_date': '',
            'journal_lines': [], 'split_lines': [], 'child_lines': [], 'actionsplit': 'none'
        }
        stock_date = fields.Datetime.to_china_string(label.stock_date)
        warranty_date = fields.Datetime.to_china_string(label.warranty_date)
        if stock_date:
            values['stock_date'] = stock_date[0:10]
        if warranty_date:
            values['warranty_date'] = warranty_date[0:10]
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
        loginuser = request.env.user
        if (loginuser._is_superuser() or loginuser._is_admin()) and not label.locked:
            values['actionsplit'] = 'block'
        elif loginuser.has_group('aas_mes.group_aas_manufacture_user') and not label.locked:
            values.update({'actionsplit': 'block'})
        return request.render('aas_mes.wechat_mes_label_detail', values)


    @http.route('/aaswechat/mes/printlabels', type='json', auth="user")
    def aas_wechat_mes_printlabels(self, printerid, labelids=[]):
        values = {'success': True, 'message': ''}
        try:
            tempvals = request.env['aas.product.label'].action_print_label(printerid, ids=labelids)
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        values.update(tempvals)
        return values


    @http.route('/aaswechat/mes/labelsplit/<int:labelid>', type='http', auth="user")
    def aas_wechat_mes_labelsplit(self, labelid):
        label = request.env['aas.product.label'].browse(labelid)
        values = {
            'label_id': label.id, 'label_name': label.name, 'product_code': label.product_code,
            'product_lot': label.product_lot.name, 'product_qty': label.product_qty
        }
        return request.render('aas_mes.wechat_mes_label_split', values)


    @http.route('/aaswechat/mes/labelsplitdone', type='json', auth="user")
    def aas_wechat_mes_labelsplitdone(self, labelid, label_qty):
        values = {'success': True, 'message': ''}
        label = request.env['aas.product.label'].browse(labelid)
        try:
            label.action_dosplit(label_qty, 1)
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        values['labelid'] = labelid
        return values


    @http.route('/aaswechat/mes/labelsplitlist/<int:labelid>', type='http', auth="user")
    def aas_wechat_mes_labelsplit_list(self, labelid):
        label = request.env['aas.product.label'].browse(labelid)
        values = {
            'label_id': label.id,
            'product_code': label.product_code, 'location_name': label.location_id.name,
            'product_lot': label.product_lot.name, 'product_qty': label.product_qty, 'labelist': []
        }
        values['labelist'] = [{'label_name': label.name, 'product_qty': label.product_qty}]
        if label.origin_lines and len(label.origin_lines) > 0:
            for oline in label.origin_lines:
                values['product_qty'] += oline.product_qty
                values['labelist'].append({
                    'label_name': oline.name, 'product_qty': oline.product_qty
                })
        return request.render('aas_mes.wechat_mes_label_splitlist', values)


    @http.route('/aaswechat/mes/printsplitlabels', type='json', auth="user")
    def aas_wechat_mes_printlabels(self, printerid, labelid):
        values = {'success': True, 'message': ''}
        label = request.env['aas.product.label'].browse(labelid)
        labelids = [label.id]
        if label.origin_lines and len(label.origin_lines) > 0:
            labelids += [tlabel.id for tlabel in label.origin_lines]
        try:
            tempvals = request.env['aas.product.label'].action_print_label(printerid, ids=labelids)
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        values.update(tempvals)
        return values

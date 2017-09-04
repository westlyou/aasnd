# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-9 18:16
"""

import logging
import werkzeug

from odoo import http, fields
from odoo.http import request
from odoo.tools.float_utils import float_compare
from odoo.exceptions import AccessDenied,UserError,ValidationError

logger = logging.getLogger(__name__)

RECEIPTTYPEDICT = {'purchase': u'采购收货', 'manufacture': u'成品入库', 'manreturn': u'生产退料', 'sundry': u'杂项入库'}
RECEIPTSTATEDICT = {'draft': u'草稿', 'confirm': u'确认', 'tocheck': u'待检', 'checked': u'已检', 'receipt': u'收货', 'done': u'完成', 'cancel': u'取消'}

def get_current_time(record, timestr):
    if not timestr:
        return ''
    temptime = fields.Datetime.from_string(timestr)
    return fields.Datetime.to_string(fields.Datetime.context_timestamp(record, temptime))


class AASReceiptWechatController(http.Controller):

    ######################################## 收货明细单上架操作 #########################################

    @http.route('/aaswechat/wms/receiptlinelist', type='http', auth='user')
    def aas_wechat_wms_receiptlinelist(self, limit=20):
        values = {'success': True, 'message': '', 'receiptlines': [], 'lineindex': '0'}
        linesdomain = ['&', '|']
        linesdomain.extend(['&', ('receipt_type', '=', 'purchase'), ('state', 'in', ['checked', 'receipt'])])
        linesdomain.extend(['&', ('receipt_type', '!=', 'purchase'), ('state', 'in', ['confirm', 'receipt'])])
        linesdomain.extend([('company_id', '=', request.env.user.company_id.id)])
        receiptlines = request.env['aas.stock.receipt.line'].search(linesdomain, limit=limit)
        if receiptlines and len(receiptlines) > 0:
            values['receiptlines'] = [{
                'line_id': rline.id, 'receipt_name': rline.receipt_id.name, 'product_code': rline.product_id.default_code,
                'location_name': '' if not rline.push_location else rline.push_location.name, 'receipt_type': RECEIPTTYPEDICT[rline.receipt_type]
            } for rline in receiptlines]
            values['lineindex'] = len(receiptlines)
        return request.render('aas_wms.wechat_wms_receipt_line_list', values)


    @http.route('/aaswechat/wms/receiptlinemore', type='json', auth="user")
    def aas_wechat_wms_receiptlinemore(self, lineindex=0, product_code=None, limit=20):
        values = {'success': True, 'message': '', 'receiptlines': [], 'lineindex': lineindex, 'linecount': 0}
        linesdomain = ['&', '|']
        linesdomain.extend(['&', ('receipt_type', '=', 'purchase'), ('state', 'in', ['checked', 'receipt'])])
        linesdomain.extend(['&', ('receipt_type', '!=', 'purchase'), ('state', 'in', ['confirm', 'receipt'])])
        if not product_code:
            linesdomain.extend([('company_id', '=', request.env.user.company_id.id)])
        else:
            linesdomain.extend(['&', ('company_id', '=', request.env.user.company_id.id), ('product_code', 'ilike', '%'+product_code+'%')])
        receiptlines = request.env['aas.stock.receipt.line'].search(linesdomain, offset=lineindex, limit=limit)
        if receiptlines and len(receiptlines) > 0:
            values['receiptlines'] = [{
                'line_id': rline.id, 'receipt_name': rline.receipt_id.name, 'product_code': rline.product_id.default_code,
                'location_name': '' if not rline.push_location else rline.push_location.name, 'receipt_type': RECEIPTTYPEDICT[rline.receipt_type]
            } for rline in receiptlines]
            values['linecount'] = len(receiptlines)
            values['lineindex'] = values['linecount'] + lineindex
        return values



    @http.route('/aaswechat/wms/receiptlinesearch', type='json', auth="user")
    def aas_wechat_wms_receiptlinesearch(self, product_code, limit=20):
        values = {'success': True, 'message': '', 'receiptlines': [], 'lineindex': '0'}
        linesdomain = ['&', '|']
        linesdomain.extend(['&', ('receipt_type', '=', 'purchase'), ('state', 'in', ['checked', 'receipt'])])
        linesdomain.extend(['&', ('receipt_type', '!=', 'purchase'), ('state', 'in', ['confirm', 'receipt'])])
        linesdomain.extend(['&', ('company_id', '=', request.env.user.company_id.id), ('product_code', 'ilike', '%'+product_code+'%')])
        receiptlines = request.env['aas.stock.receipt.line'].search(linesdomain, limit=limit)
        if receiptlines and len(receiptlines) > 0:
            values['receiptlines'] = [{
                'line_id': rline.id, 'receipt_name': rline.receipt_id.name, 'product_code': rline.product_id.default_code,
                'location_name': '' if not rline.push_location else rline.push_location.name, 'receipt_type': RECEIPTTYPEDICT[rline.receipt_type]
            } for rline in receiptlines]
            values['lineindex'] = len(receiptlines)
        return values

    @http.route('/aaswechat/wms/receiptline/<int:receiptlineid>', type='http', auth='user')
    def aas_wechat_wms_receiptlinedetail(self, receiptlineid):
        values = {'success': True, 'message': '', 'labellist': [], 'operationlist': []}
        receiptline = request.env['aas.stock.receipt.line'].browse(receiptlineid)
        values.update({
            'receiptlineid': receiptlineid, 'receipt_name': receiptline.receipt_id.name, 'product_code': receiptline.product_id.default_code,
            'product_uom': receiptline.product_uom.name, 'origin_order': receiptline.origin_order, 'receipt_type': receiptline.receipt_type,
            'type_name': RECEIPTTYPEDICT[receiptline.receipt_type], 'state': receiptline.state, 'state_name': RECEIPTSTATEDICT[receiptline.state],
            'push_location_id': '0' if not receiptline.push_location else receiptline.push_location.id,
            'push_location_name': '' if not receiptline.push_location else receiptline.push_location.name,
            'product_qty': receiptline.product_qty, 'receipt_qty': receiptline.receipt_qty, 'doing_qty': receiptline.doing_qty,
            'labelscan': 'none', 'pushall': 'none', 'pushdone': 'none'
        })
        if (receiptline.receipt_type=='purchase' and receiptline.state in ['checked', 'receipt']) or (receiptline.receipt_type!='purchase' and receiptline.state in ['confirm', 'receipt']):
            values.update({'labelscan': 'block', 'pushall': 'block'})
        if float_compare(receiptline.doing_qty, 0.0, precision_rounding=0.000001) > 0:
            values.update({'pushdone': 'block'})
        if receiptline.label_list and len(receiptline.label_list) > 0:
            values['labellist'] = [{
                'label_name': llist.label_id.name,
                'product_lot': llist.product_lot.name, 'product_qty': llist.label_id.product_qty,
                'qualified': llist.label_id.qualified, 'product_code': llist.product_id.default_code
            } for llist in receiptline.label_list]
        if receiptline.operation_list and len(receiptline.operation_list) > 0:
            values['operationlist'] = [{
                'label_id': roperation.rlabel_id.label_id.id, 'operation_id': roperation.id,
                'roperation_id': roperation.id, 'label_name': roperation.rlabel_id.label_id.name, 'push_onshelf': roperation.push_onshelf,
                'product_code': roperation.product_id.default_code,'product_lot': roperation.product_lot.name, 'product_qty': roperation.product_qty
            } for roperation in receiptline.operation_list]
        return request.render('aas_wms.wechat_wms_receipt_line_detail', values)



    @http.route('/aaswechat/wms/receiptlinelocationscan', type='json', auth="user")
    def aas_wechat_wms_receiptlinelocationscan(self, lineid, barcode):
        values = {'success': True, 'message': ''}
        receiptline = request.env['aas.stock.receipt.line'].browse(lineid)
        if not receiptline:
            values.update({'success': False, 'message': u'请仔细检查收货明细可能被删除了！'})
            return values
        push_location = request.env['stock.location'].search([('barcode', '=', barcode)], limit=1)
        if not push_location:
            values.update({'success': False, 'message': u'无效库位， 请仔细检查是否库位已删除！'})
            return values
        receiptline.write({'push_location': push_location.id})
        values.update({'location_id': push_location.id, 'location_name': push_location.name})
        return values


    @http.route('/aaswechat/wms/receiptlinelabelscan', type='json', auth="user")
    def aas_wechat_wms_receiptlinelabelscan(self, lineid, barcode):
        values = {'success': True, 'message': ''}
        receiptline = request.env['aas.stock.receipt.line'].browse(lineid)
        if not receiptline:
            values.update({'success': False, 'message': u'请仔细检查收货明细可能被删除了！'})
            return values
        label = request.env['aas.product.label'].search([('barcode', '=', barcode), ('product_id', '=', receiptline.product_id.id)], limit=1)
        if not label:
            values.update({'success': False, 'message': u'无效标签， 请仔细检查是否标签已删除！'})
            return values
        receiptlabel = request.env['aas.stock.receipt.label'].search([('line_id', '=', lineid), ('label_id', '=', label.id)], limit=1)
        if not receiptlabel:
            values.update({'success': False, 'message': u'无效标签， 当前标签不在上架范围内！'})
            return values
        receiptoperation = request.env['aas.stock.receipt.operation'].search([('line_id', '=', lineid), ('rlabel_id', '=', receiptlabel.id)], limit=1)
        if receiptoperation:
            values.update({'success': False, 'message': u'标签已作业，请不要重复操作！'})
            return values
        if label.qualified and receiptline.push_location.mrblocation:
            values.update({'success': False, 'message': u'合格品请不要放在MRB库位上！'})
            return values
        elif not label.qualified and not receiptline.push_location.mrblocation:
            values.update({'success': False, 'message': u'不合格品请放在MRB库位上！'})
            return values
        try:
            tempoperation = request.env['aas.stock.receipt.operation'].create({
                'rlabel_id': receiptlabel.id, 'location_id': receiptline.push_location.id
            })
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        values.update({
            'label_id': label.id, 'label_name': label.name, 'product_code': label.product_code,
            'product_lot': label.product_lot.name, 'product_qty': label.product_qty,
            'operation_id': tempoperation.id, 'doing_qty': receiptline.doing_qty
        })
        return values


    @http.route('/aaswechat/wms/receiptlineoperationdel', type='json', auth="user")
    def aas_wechat_wms_receiptlineoperationdel(self, operation_id):
        values = {'success': True, 'message': ''}
        receiptoperation = request.env['aas.stock.receipt.operation'].browse(operation_id)
        if not receiptoperation:
            values.update({'success': False, 'message': u'请仔细检查收货明细可能已删除了！'})
            return values
        receiptline = receiptoperation.line_id
        receiptoperation.unlink()
        values.update({'doing_qty': receiptline.doing_qty})
        return values


    @http.route('/aaswechat/wms/receiptlinepushall', type='json', auth="user")
    def aas_wechat_wms_receiptlinepushall(self, lineid):
        values = {'success': True, 'message': ''}
        receiptline = request.env['aas.stock.receipt.line'].browse(lineid)
        try:
            receiptline.action_push_all()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        return values


    @http.route('/aaswechat/wms/receiptlinepushdone', type='json', auth="user")
    def aas_wechat_wms_receiptlinepushdone(self, lineid):
        values = {'success': True, 'message': ''}
        receiptline = request.env['aas.stock.receipt.line'].browse(lineid)
        try:
            receiptline.action_push_done()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        return values


    ######################################## 收货单操作 #########################################

    @http.route('/aaswechat/wms/receiptlist/<string:receipttype>', type='http', auth="user")
    def aas_wechat_wms_receiptlist(self, receipttype='all', limit=20):
        values = {'receipts': [], 'receipttype': receipttype, 'list_name': u'收货列表', 'receiptindex': '0'}
        search_domain = [('state', 'in', ['confirm', 'receipt'])]
        if receipttype == 'purchase':
            search_domain = [('state', 'in', ['draft', 'confirm', 'tocheck', 'checked', 'receipt'])]
        if receipttype != 'all':
            search_domain.append(('receipt_type', '=', receipttype))
            values['list_name'] = RECEIPTTYPEDICT[receipttype]
        search_domain.append(('company_id', '=', request.env.user.company_id.id))
        receipt_list = request.env['aas.stock.receipt'].search(search_domain, limit=limit)
        if receipt_list:
            values['receipts'] = [{
                'receipt_id': receipt.id, 'receipt_name': receipt.name, 'receipt_state': RECEIPTSTATEDICT[receipt.state]
            } for receipt in receipt_list]
            values['receiptindex'] = len(receipt_list)
        return request.render('aas_wms.wechat_wms_receipt_list', values)

    @http.route('/aaswechat/wms/receiptlistsearch', type='json', auth="user")
    def aas_wechat_wms_receipt_product_search(self, product_code=None, receipt_type='all', limit=20):
        values = {'success': True, 'message': '', 'receiptindex': '0'}
        search_domain = [('state', 'in', ['confirm', 'receipt'])]
        if receipt_type=='purchase':
            search_domain = [('state', 'in', ['draft', 'confirm', 'tocheck', 'checked', 'receipt'])]
        if receipt_type!='all':
            search_domain.append(('receipt_type', '=', receipt_type))
        search_domain.append(('product_code', 'ilike', '%s'+product_code+'%s'))
        search_domain.append(('company_id', '=', request.env.user.company_id.id))
        receipt_line_list = request.env['aas.stock.receipt.line'].search(search_domain)
        if not receipt_line_list or len(receipt_line_list) <= 0:
            values['success'], values['message'] = False, u'未搜索到你需要的收货单！'
            return values
        receiptids = list(set([rline.receipt_id.id for rline in receipt_line_list]))
        receipts = request.env['aas.stock.receipt'].search([('id', 'in', receiptids)], limit=limit)
        values['receipts'] = [{
            'receipt_id': receipt.id, 'receipt_name': receipt.name, 'receipt_state': RECEIPTSTATEDICT[receipt.state]
        } for receipt in receipts]
        values['receiptindex'] = len(receipts)
        return values


    @http.route('/aaswechat/wms/receiptmore', type='json', auth="user")
    def aas_wechat_wms_receiptmore(self, receipttype='all', product_code=None, receiptindex=0, limit=20):
        values = {'success': True, 'message': '', 'receipts': [], 'receiptindex': receiptindex, 'receipttype': receipttype, 'receiptcount': 0}
        search_domain = [('state', 'in', ['confirm', 'receipt'])]
        if receipttype=='purchase':
            search_domain = [('state', 'in', ['draft', 'confirm', 'tocheck', 'checked', 'receipt'])]
        if receipttype!='all':
            search_domain.append(('receipt_type', '=', receipttype))
        search_domain.append(('company_id', '=', request.env.user.company_id.id))
        if product_code:
            search_domain.append(('product_code', 'ilike', '%'+product_code+'%'))
            receiptlines = request.env['aas.stock.receipt.line'].search(search_domain)
            if not receiptlines or len(receiptlines) <= 0:
                receipts = []
            receiptids = list(set([rline.receipt_id.id for rline in receiptlines]))
            receipts = request.env['aas.stock.receipt'].search([('id', 'in', receiptids)], offset=receiptindex, limit=limit)
        else:
            receipts = request.env['aas.stock.receipt'].search(search_domain, offset=receiptindex, limit=limit)
        if receipts and len(receipts) > 0:
            values['receipts'] = [{
                'receipt_id': receipt.id, 'receipt_name': receipt.name, 'receipt_state': RECEIPTSTATEDICT[receipt.state]
            } for receipt in receipts]
            values['receiptcount'] = len(receipts)
            values['receiptindex'] = values['receiptcount'] + receiptindex
        return values


    @http.route('/aaswechat/wms/receiptdetail/<int:receiptid>', type='http', auth="user")
    def aas_wechat_wms_receiptdetail(self, receiptid):
        receipt = request.env['aas.stock.receipt'].browse(receiptid)
        values = {'receipt_id': receipt.id, 'receipt_name': receipt.name}
        values.update({'order_user': receipt.order_user.name, 'order_time': get_current_time(receipt, receipt.order_time)})
        values.update({'receipt_type': receipt.receipt_type, 'receipt_type_name': RECEIPTTYPEDICT[receipt.receipt_type]})
        values.update({'receipt_state': receipt.state, 'receipt_state_name': RECEIPTSTATEDICT[receipt.state]})
        values.update({'receiptconfirm': 'none', 'commitcheck': 'none', 'printlabel': 'none'})
        if receipt.receipt_type == 'purchase':
            if receipt.state == 'draft':
                values['receiptconfirm'] = 'block'
            elif receipt.state == 'confirm':
                values['commitcheck'] = 'block'
            values['printlabel'] = 'block'
        if receipt.receipt_lines:
            values['receipt_lines'] = [{
                'line_id': rline.id,
                'product_id': rline.product_id.id,
                'product_code': rline.product_id.default_code,
                'product_qty': rline.product_qty,
                'receipt_qty': str(rline.receipt_qty),
                'doing_qty': str(rline.doing_qty),
                'label_related': rline.label_related
            } for rline in receipt.receipt_lines]
        if receipt.label_lines:
            values['label_lines'] = [{
                'list_id': rlabel.id,
                'label_name': rlabel.label_id.name,
                'product_code': rlabel.label_id.product_code,
                'product_lot': rlabel.product_lot.name,
                'location_name': rlabel.label_id.location_id.name,
                'product_qty': rlabel.product_qty,
                'qualified_qty': rlabel.qualified_qty,
                'concession_qty': rlabel.concession_qty,
                'unqualified_qty': rlabel.unqualified_qty,
                'label_qualified': rlabel.label_id.qualified} for rlabel in receipt.label_lines]
        if receipt.operation_lines:
            values['operation_lines'] = [{
                'operation_id': roperation.id,
                'label_name': roperation.rlabel_id.label_id.name,
                'product_code': roperation.product_id.default_code,
                'product_qty': roperation.product_qty,
                'location_id': roperation.location_id.id,
                'location_name': roperation.location_id.name,
                'push_onshelf': roperation.push_onshelf} for roperation in receipt.operation_lines]
        return request.render('aas_wms.wechat_wms_receipt_detail', values)


    @http.route('/aaswechat/wms/receiptconfirm', type='json', auth="user")
    def aas_wechat_wms_receiptconfirm(self, receiptid=None):
        values = {'success': True, 'message': ''}
        receipt = request.env['aas.stock.receipt'].browse(receiptid)
        try:
            receipt.action_confirm()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        return values


    @http.route('/aaswechat/wms/receiptcommitcheck', type='json', auth="user")
    def aas_wechat_wms_receipt_commit_check(self, receiptid):
        values = {'success': True, 'message': ''}
        receipt = request.env['aas.stock.receipt'].browse(receiptid)
        try:
            receipt.action_commit_checking()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        return values


    @http.route('/aaswechat/wms/receiptprintlabels', type='json', auth="user")
    def aas_wechat_wms_receipt_print_labels(self, receiptid, printerid):
        values = {'success': True, 'message': ''}
        try:
            tempvals = request.env['aas.stock.receipt'].action_print_label(printerid, ids=[receiptid])
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        values.update(tempvals)
        printer = request.env['aas.label.printer'].browse(printerid)
        values.update({'printer': printer.name, 'printurl': printer.serverurl})
        return values


    @http.route('/aaswechat/wms/receipt/lotlist/<int:lineid>', type='http', auth='user')
    def aas_wechat_wms_receipt_lotlist(self, lineid):
        receiptline = request.env['aas.stock.receipt.line'].browse(lineid)
        values = {'linedid': lineid, 'product_id': receiptline.product_id.id}
        values.update({'product_qty': receiptline.product_qty, 'origin_order': receiptline.origin_order})
        values.update({'product_code': receiptline.product_id.default_code, 'need_warranty': receiptline.product_id.need_warranty})
        return request.render('aas_wms.wechat_wms_receipt_lotlist', values)


    @http.route('/aaswechat/wms/receipt/lotlistdone', type='json', auth="user")
    def aas_wechat_wms_receipt_lotlistdone(self, lineid, lot_line_list=[]):
        values = {'success': True, 'message': '', 'lineid': lineid}
        line = request.env['aas.stock.receipt.line'].browse(lineid)
        if line.label_related:
            values['success'], values['message'] = True, u"标签已生成，请不要重复操作！"
            return values
        try:
            receiptwizard = request.env['aas.stock.receipt.product.wizard'].create({
                'receipt_id': line.receipt_id.id, 'line_id': lineid, 'product_id': line.product_id.id,
                'product_uom': line.product_uom.id, 'product_qty': line.product_qty, 'need_warranty': line.product_id.need_warranty,
                'receipt_locked': True, 'origin_order': line.origin_order,
                'lot_lines': [(0, 0, lotval) for lotval in lot_line_list]
            })
            receiptwizard.action_check_lots()
            for lline in receiptwizard.lot_lines:
                lline.action_split_lot()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        values.update({'receiptwizardid': receiptwizard.id})
        return values


    @http.route('/aaswechat/wms/receipt/labellist/<int:wizardid>', type='http', auth="user")
    def aas_wechat_wms_receipt_labellist(self, wizardid=None):
        receiptwizard = request.env['aas.stock.receipt.product.wizard'].browse(wizardid)
        values = {'wizardid': wizardid, 'product_code': receiptwizard.product_id.default_code}
        values.update({'product_qty': receiptwizard.product_qty, 'need_warranty': receiptwizard.need_warranty})
        values.update({'origin_order': receiptwizard.origin_order, 'label_count': len(receiptwizard.label_lines)})
        values['labellines'] = [{
            'lot_name': lline.lot_name, 'label_qty': lline.label_qty, 'warranty_date': lline.warranty_date
        } for lline in receiptwizard.label_lines]
        return request.render('aas_wms.wechat_wms_receipt_labellist', values)


    @http.route('/aaswechat/wms/receipt/labellistdone', type='json', auth="user")
    def aas_wechat_wms_receipt_labellistdone(self, wizardid, label_line_list=[]):
        values = {'success': True, 'message': ''}
        receiptwizard = request.env['aas.stock.receipt.product.wizard'].browse(wizardid)
        values['receiptid'] = receiptwizard.receipt_id.id
        if receiptwizard.label_lines and len(receiptwizard.label_lines) > 0:
            receiptwizard.label_lines.unlink()
        try:
            receiptwizard.write({'label_lines': [(0, 0, labelval) for labelval in label_line_list]})
            receiptwizard.action_done_labels()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        return values
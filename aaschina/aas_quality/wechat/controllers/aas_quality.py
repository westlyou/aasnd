# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-1-3 21:37
"""

import logging
import werkzeug

from odoo import http, fields
from odoo.http import request
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

ORDER_STATE_DICT = {'draft': u'草稿', 'tocheck': u"待检", 'checking': u'检测中', 'done': u'完成', 'cancel': u'取消'}

class AASWechatQualityOrderController(http.Controller):

    @http.route('/aaswechat/quality/orderlist', type='http', auth="user", methods=['GET', 'POST'])
    def aas_wechat_quality_orderlist(self):
        values = {'orderlist': [], 'orderindex': '0'}
        search_domain = [('state', 'in', ['tocheck', 'checking'])]
        orderlist = request.env['aas.quality.order'].search(search_domain, limit=20)
        if orderlist and len(orderlist) > 0:
            values['orderlist'] = [{
                'order_id': qorder.id, 'order_name': qorder.name, 'order_state': ORDER_STATE_DICT[qorder.state],
                'product_code': qorder.product_id.default_code, 'product_qty': qorder.product_qty
            } for qorder in orderlist]
            values['orderindex'] = len(orderlist)
        return request.render('aas_quality.wechat_quality_order_list', values)


    @http.route('/aaswechat/quality/ordermore', type='json', auth="user")
    def aas_wechat_quality_ordermore(self, orderindex=0, limit=20):
        values = {'orderlist': [], 'orderindex': orderindex, 'ordercount': 0}
        search_domain = [('state', 'in', ['tocheck', 'checking'])]
        orderlist = request.env['aas.quality.order'].search(search_domain, offset=orderindex, limit=limit)
        if orderlist and len(orderlist) > 0:
            values['orderlist'] = [{
                'order_id': qorder.id, 'order_name': qorder.name, 'order_state': ORDER_STATE_DICT[qorder.state],
                'product_code': qorder.product_id.default_code, 'product_qty': qorder.product_qty
            } for qorder in orderlist]
            values['ordercount'] = len(orderlist)
            values['orderindex'] = values['ordercount'] + orderindex
        return values



    @http.route('/aaswechat/quality/orderdetail/<int:orderid>', type='http', auth="user")
    def aas_wechat_quality_orderdetail(self, orderid):
        qorder = request.env['aas.quality.order'].browse(orderid)
        values = {
            'order_id': qorder.id, 'order_name': qorder.name,
            'order_state': qorder.state, 'state_name': ORDER_STATE_DICT[qorder.state],
            'product_qty': qorder.product_qty, 'qualified_qty': qorder.qualified_qty,
            'concession_qty': qorder.concession_qty, 'unqualified_qty': qorder.unqualified_qty,
            'commit_user': qorder.commit_user.name, 'product_code': qorder.product_id.default_code,
            'commit_time': fields.Datetime.to_china_string(qorder.commit_time),
            'check_user': '' if not qorder.check_user else qorder.check_user.name,
            'check_time': fields.Datetime.to_china_string(qorder.check_time),
            'actionscan': 'block', 'actiondone': 'block', 'allqualified': 'block', 'allunqualified': 'block'
        }
        if qorder.state == 'done':
            values.update({
                'actionscan': 'none', 'actiondone': 'none', 'allqualified': 'none', 'allunqualified': 'none'
            })
        values['labellist'], values['operationlist'], values['rejectlist'] = [], [], []
        if qorder.label_lines and len(qorder.label_lines) > 0:
            values['labellist'] = [{
                'line_id': lline.id, 'label_id': lline.label_id.id, 'checked': lline.label_checked,
                'label_name': lline.label_id.name, 'product_code': lline.label_id.product_code,
                'product_lot': lline.label_id.product_lot.name, 'product_qty': lline.label_id.product_qty
            } for lline in qorder.label_lines]
        if qorder.operation_lines and len(qorder.operation_lines) > 0:
            values['operationlist'] = [{
                'line_id': toperation.id, 'label_name': toperation.qlabel_id.label_id.name,
                'product_code': toperation.product_id.default_code, 'product_lot': toperation.product_lot.name,
                'product_qty': toperation.product_qty, 'concession_qty': toperation.concession_qty,
                'unqualified_qty': toperation.unqualified_qty, 'qualified_qty': toperation.qualified_qty
            } for toperation in qorder.operation_lines]
        if qorder.rejection_lines and len(qorder.rejection_lines) > 0:
            values['rejectlist'] = [{
                'line_id': rline.id, 'label_name': rline.label_id.name, 'product_qty': rline.product_qty,
                'product_code': rline.product_id.default_code, 'product_lot': rline.product_lot.name
            } for rline in qorder.rejection_lines]
        return request.render('aas_quality.wechat_quality_order_detail', values)


    @http.route('/aaswechat/quality/actionallqualified', type='json', auth="user")
    def aas_wechat_quality_actionallqualified(self, orderid):
        values = {'success': True, 'message': ''}
        qorder = request.env['aas.quality.order'].browse(orderid)
        if qorder.state == 'done':
            values.update({'success': False, 'message': u'质检已经完成，请不要重复操作！'})
            return values
        qorder.action_all_qualified()
        return values


    @http.route('/aaswechat/quality/actionallunqualified', type='json', auth="user")
    def aas_wechat_quality_actionallunqualified(self, orderid):
        values = {'success': True, 'message': ''}
        qorder = request.env['aas.quality.order'].browse(orderid)
        if qorder.state == 'done':
            values.update({'success': False, 'message': u'质检已经完成，请不要重复操作！'})
            return values
        qorder.action_all_unqualified()
        return values

    @http.route('/aaswechat/quality/operationdel', type='json', auth="user")
    def aas_wechat_quality_operationdel(self, lineid):
        values = {'success': True, 'message': ''}
        toperation = request.env['aas.quality.operation'].browse(lineid)
        if not toperation:
            values.update({'success': False, 'message': u'操作记录可能已删除，请不要重复操作！'})
            return values
        toperation.unlink()
        return values


    @http.route('/aaswechat/quality/orderlabelscan', type='json', auth="user")
    def aas_wechat_quality_orderlabelscan(self, orderid, barcode):
        values = {'success': True, 'message': ''}
        qorder = request.env['aas.quality.order'].browse(orderid)
        if qorder.state == 'done':
            values.update({'success': False, 'message': u'质检已经完成，请不要重复操作！'})
            return values
        label = request.env['aas.product.label'].search([('barcode', '=', barcode)], limit=1)
        if not label:
            values.update({'success': False, 'message': u'请仔细检查，未搜索到相应标签！'})
            return values
        labeldomain = [('order_id', '=', orderid), ('label_id', '=', label.id)]
        qlabel = request.env['aas.quality.label'].search(labeldomain, limit=1)
        if not qlabel:
            values.update({'success': False, 'message': u'请仔细检查，当前标签不在检测清单中！'})
            return values
        if qlabel.label_checked:
            values.update({'success': False, 'message': u'请仔细检查，当前标签已检测请不要重复操作！'})
            return values
        values['rlabelid'] = qlabel.id
        return values


    @http.route('/aaswechat/quality/actionchecking', type='json', auth="user")
    def aas_wechat_quality_actionchecking(self, orderid):
        values = {'success': True, 'message': '', 'action': 'none'}
        qorder = request.env['aas.quality.order'].browse(orderid)
        if qorder.state == 'done':
            values.update({'success': False, 'message': u'质检已经完成，请不要重复操作！'})
            return values
        uncheckdomain = [('order_id', '=', orderid), ('label_checked', '=', False)]
        if request.env['aas.quality.label'].search_count(uncheckdomain) > 0:
            values.update({
                'action': 'check', 'message': u'您还有部分标签未检测，如果确认完成检测这些标签将默认全部合格！'
            })
        unqualifiedomain = [('order_id', '=', orderid), ('partqualified', '=', True)]
        if request.env['aas.quality.operation'].search_count(unqualifiedomain) > 0:
            values.update({
                'action': 'split', 'message': u'您有部分标签不合格，如果确认将进行不合格拆分重新打包！'
            })
        return values


    @http.route('/aaswechat/quality/actiondone', type='json', auth="user")
    def aas_wechat_quality_actiondone(self, orderid):
        values = {'success': True, 'message': ''}
        qorder = request.env['aas.quality.order'].browse(orderid)
        if qorder.state == 'done':
            values.update({'success': False, 'message': u'质检已经完成，请不要重复操作！'})
            return values
        unqualifiedomain = [('order_id', '=', orderid), ('partqualified', '=', True)]
        if request.env['aas.quality.operation'].search_count(unqualifiedomain) > 0:
            values.update({
                'success': False, 'message': u'您有部分标签不合格,还未拆分处理！'
            })
            return values
        uncheckdomain = [('order_id', '=', orderid), ('label_checked', '=', False)]
        unchecklist = request.env['aas.quality.label'].search(uncheckdomain)
        if unchecklist and len(unchecklist) > 0:
            qorder.write({'operation_lines': [{'qlabel_id': tlabel.id} for tlabel in unchecklist]})
        qorder.action_quality_done()
        return values



    @http.route('/aaswechat/quality/checkdetermine/<int:determineid>', type='http', auth="user", methods=['GET', 'POST'])
    def aas_wechat_quality_checkdetermine(self, determineid):
        values = {'success': True, 'message': ''}
        qualitylabel = request.env['aas.quality.label'].browse(determineid)
        values.update({
            'order_name': qualitylabel.order_id.name, 'qlabel_id': qualitylabel.id,
            'label_name': qualitylabel.label_id.name, 'product_code': qualitylabel.product_id.default_code,
            'product_lot': qualitylabel.product_lot.name, 'product_qty': qualitylabel.product_qty
        })
        return request.render('aas_quality.wechat_quality_checkdetermine', values)


    @http.route('/aaswechat/quality/actiondodetermine', type='json', auth="user")
    def aas_wechat_quality_actiondodetermine(self, qlabelid, concession_qty=0.0, unqualified_qty=0.0):
        values = {'success': True, 'message': ''}
        qlabel = request.env['aas.quality.label'].browse(qlabelid)
        if not qlabel:
            values.update({'success': False, 'message': u'当前标签不在检测清单中！'})
            return values
        values['orderid'] = qlabel.order_id.id
        operationvals = {'order_id': qlabel.order_id.id, 'qlabel_id': qlabelid}
        if concession_qty:
            if float_compare(concession_qty, qlabel.product_qty, precision_rounding=0.000001) > 0.0:
                values.update({'success': False, 'message': u'让步数量不可以大于报检数量！'})
                return values
            if float_compare(concession_qty, 0.0, precision_rounding=0.000001) < 0.0:
                values.update({'success': False, 'message': u'让步数量不可以小于0！'})
                return values
            operationvals['concession_qty'] = concession_qty
        if unqualified_qty:
            if float_compare(unqualified_qty, qlabel.product_qty, precision_rounding=0.000001) > 0.0:
                values.update({'success': False, 'message': u'不合格数量不可以大于报检数量！'})
                return values
            if float_compare(unqualified_qty, 0.0, precision_rounding=0.000001) < 0.0:
                values.update({'success': False, 'message': u'不合格数量不可以小于0！'})
                return values
            operationvals['unqualified_qty'] = unqualified_qty
        if concession_qty and unqualified_qty:
            total_qty = concession_qty + unqualified_qty
            if float_compare(total_qty, qlabel.product_qty, precision_rounding=0.000001) > 0.0:
                values.update({'success': False, 'message': u'让步数量和不合格数量总和不可以大于报检数量！'})
            return values
        try:
            request.env['aas.quality.operation'].create(operationvals)
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        except ValidationError, ve:
            values.update({'success': False, 'message': ve.name})
            return values
        return values



    @http.route('/aaswechat/quality/splitunqualified/<int:orderid>', type='http', auth="user", methods=['GET', 'POST'])
    def aas_wechat_quality_splitunqualified(self, orderid):
        values = {'success': True, 'message': ''}
        qorder = request.env['aas.quality.order'].browse(orderid)
        values.update({
            'order_id': orderid, 'product_code': qorder.product_id.default_code,
            'order_name': qorder.name, 'wizardid': '0', 'lotlist': []
        })
        operationdomain = [('order_id', '=', orderid), ('partqualified', '=', True)]
        operationlist = request.env['aas.quality.operation'].search(operationdomain)
        if operationlist and len(operationlist) > 0:
            productdict, tempqty = {}, 0.0
            for toperation in operationlist:
                tkey = 'P-'+str(toperation.product_id.id)+'-'+str(toperation.product_lot.id)
                if not toperation.commit_model:
                    tkey += '-0'
                else:
                    tkey += '-'+toperation.commit_model
                if not toperation.commit_id:
                    tkey += '-0'
                else:
                    tkey += '-'+str(toperation.commit_id)
                if tkey in productdict:
                    productdict[tkey]['product_qty'] += toperation.unqualified_qty
                else:
                    productdict[tkey] = {
                        'product_id': toperation.product_id.id, 'product_lot': toperation.product_lot.id,
                        'product_qty': toperation.unqualified_qty,
                        'commit_id': False if not toperation.commit_id else toperation.commit_id,
                        'commit_model': False if not toperation.commit_model else toperation.commit_model,
                        'commit_order': False if not toperation.commit_order else toperation.commit_order,
                        'origin_order': False if not toperation.origin_order else toperation.origin_order
                    }
                tempqty += toperation.unqualified_qty
            tempwizard = request.env['aas.quality.rejection.wizard'].create({
                'quality_id': orderid, 'product_id': qorder.product_id.id, 'product_uom': qorder.product_id.uom_id.id,
                'product_qty': tempqty, 'partner_id': False if not qorder.partner_id else qorder.partner_id.id,
                'plot_lines': [(0, 0, {
                    'product_lot': pline['product_lot'], 'product_qty': pline['product_qty'],
                    'origin_order': pline['origin_order'], 'commit_id': pline['commit_id'],
                    'commit_model': pline['commit_model'], 'commit_order': pline['commit_order']
                }) for pline in productdict.values()]
            })
            values.update({
                'wizardid': tempwizard.id, 'lotlist': [{
                    'lineid': pline.id, 'product_lot': pline.product_lot.name, 'product_qty': pline.product_qty,
                    'origin_order': False if not pline.origin_order else pline.origin_order
                } for pline in tempwizard.plot_lines]
            })
        return request.render('aas_quality.wechat_quality_splitunqualified', values)



    @http.route('/aaswechat/quality/actiondosplit', type='json', auth="user")
    def aas_wechat_quality_actiondosplit(self, wizardid, lotlines=[]):
        values = {'success': True, 'message': ''}
        tempwizard = request.env['aas.quality.rejection.wizard'].browse(wizardid)
        if not tempwizard:
            values.update({'success': False, 'message': u'请刷新页面，拆分信息可能已清理！'})
            return values
        values['orderid'] = tempwizard.quality_id.id
        if not lotlines or len(lotlines) <= 0:
            values.update({'success': False, 'message': u'请仔细检查还未设置拆分明细！'})
            return values
        tempwizard.write({'plot_lines': [(1, lline['lineid'], {'label_qty': lline['label_qty']}) for lline in lotlines]})
        try:
            tempwizard.action_dolabels()
            tempwizard.action_done()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        except ValidationError, ve:
            values.update({'success': False, 'message': ve.name})
            return values
        return values



    @http.route('/aaswechat/quality/rejectionlist/<int:orderid>', type='http', auth="user", methods=['GET', 'POST'])
    def aas_wechat_quality_rejectionlist(self, orderid):
        values = {'success': True, 'message': '', 'order_id': orderid, 'labelids': ''}
        qorder = request.env['aas.quality.order'].browse(orderid)
        values.update({'product_code': qorder.product_id.default_code, 'order_name': qorder.name, 'labelist': []})
        templabels = request.env['aas.quality.rejection'].search([('order_id', '=', orderid)])
        if templabels and len(templabels) > 0:
            labelids, labelist = [], []
            for tlabel in templabels:
                label = tlabel.label_id
                labelids.append(str(label.id))
                labelist.append({
                    'label_id': label.id, 'label_name': label.name, 'product_code': label.product_code,
                    'product_lot': label.product_lot.name, 'product_qty': label.product_qty
                })
            values['labelids'] = ','.join(labelids)
            values['labelist'] = labelist
        return request.render('aas_quality.wechat_quality_rejectionlist', values)

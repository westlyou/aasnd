# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-10-7 16:14
"""

import logging
import werkzeug

from odoo import http
from odoo.http import request
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

class AASFeedmaterialWechatController(http.Controller):

    @http.route('/aaswechat/mes/linefeeding', type='http', auth='user')
    def aas_wechat_mes_linefeeding(self):
        values = {'success': True, 'message': '', 'meslineid': '0', 'mesline_name': '', 'materialist': []}
        loginuser = request.env.user
        feeddomain = [('lineuser_id', '=', loginuser.id), ('mesrole', '=', 'feeder')]
        linefeeder = request.env['aas.mes.lineusers'].search(feeddomain, limit=1)
        if not linefeeder:
            values.update({'success': False, 'message': u'当前登录用户可能还不是上料员，请仔细检查！'})
            return request.render('aas_mes.wechat_mes_message', values)
        mesline = linefeeder.mesline_id
        values.update({'meslineid': mesline.id, 'mesline_name': mesline.name})
        workstations = request.env['aas.mes.line.workstation'].search([('mesline_id', '=', mesline.id)], order='sequence')
        if not workstations or len(workstations) <= 0:
            values.update({'success': False, 'message': u'产线%s还未设置工位，请先设置工位，再进行上料操作！'})
            return request.render('aas_mes.wechat_mes_message', values)
        feedinglist = request.env['aas.mes.feedmaterial'].search([('mesline_id', '=', mesline.id)])
        if not feedinglist or len(feedinglist) <= 0:
            return values
        materialdict, todelfeedlist = {}, request.env['aas.mes.feedmaterial']
        for feedmaterial in feedinglist:
            mkey = 'material_'+str(feedmaterial.material_id.id)
            fkey = 'F-'+str(mesline.id)+'-'+str(feedmaterial.material_id.id)+'-'+str(feedmaterial.material_lot.id)
            if fkey not in materialdict:
                materialdict[mkey] = {
                    'tmaterial_id': mkey,
                    'material_code': feedmaterial.material_id.default_code, 'material_qty': feedmaterial.material_qty
                }
            else:
                todelfeedlist |= feedmaterial
        values['materialist'] = materialdict.values()
        if todelfeedlist and len(todelfeedlist) > 0:
            todelfeedlist.unlink()
        return request.render('aas_mes.wechat_mes_linefeeding', values)


    @http.route('/aaswechat/mes/feeding/materialscan', type='json', auth="user")
    def aas_wechat_mes_feeding_materialscan(self, barcode):
        values = {
            'success': True, 'message': '', 'tips': '', 'material_code': '', 'material_qty': 0.0, 'tmaterial_id': ''
        }
        loginuser = request.env.user
        feeddomain = [('lineuser_id', '=', loginuser.id), ('mesrole', '=', 'feeder')]
        linefeeder = request.env['aas.mes.lineusers'].search(feeddomain, limit=1)
        if not linefeeder:
            values.update({'success': False, 'message': u'当前登录用户可能还不是上料员，请仔细检查！'})
            return values
        mesline = linefeeder.mesline_id
        materiallabel = request.env['aas.product.label'].search([('barcode', '=', barcode)], limit=1)
        if not materiallabel:
            values.update({'success': False, 'message': u'未获取当前物料的标签信息，请仔细检查！'})
            return values
        if materiallabel.state != 'normal':
            values.update({'success': False, 'message': u'标签状态异常不可以投料，请仔细检查！'})
            return values
        tvalues = request.env['aas.mes.feedmaterial'].action_feeding_withlabel(mesline, barcode)
        if not tvalues.get('success', False):
            values.update({'success': False, 'message': tvalues.get('message', '')})
            return values
        product = materiallabel.product_id
        values.update({'material_code': product.default_code, 'tmaterial_id': 'material_'+str(product.id)})
        tempdomain = [('mesline_id', '=', mesline.id), ('material_id', '=', product.id)]
        tempfeedlist = request.env['aas.mes.feedmaterial'].search(tempdomain)
        if tempfeedlist and len(tempfeedlist) > 0:
            values['material_qty'] = sum([tempfeeding.material_qty for tempfeeding in tempfeedlist])
        if values.get('success', False):
            values['tips'] = u'%s上料成功，已上料%s'% (values['material_code'], values['material_qty'])
        return values


    @http.route('/aaswechat/mes/feeding/containerscan', type='json', auth="user")
    def aas_wechat_mes_feeding_containerscan(self, barcode):
        values = {
            'success': True, 'message': '', 'materiallist': [], 'tips': '',
            'material_code': '', 'material_qty': 0.0, 'tmaterial_id': ''
        }
        loginuser = request.env.user
        feeddomain = [('lineuser_id', '=', loginuser.id), ('mesrole', '=', 'feeder')]
        linefeeder = request.env['aas.mes.lineusers'].search(feeddomain, limit=1)
        if not linefeeder:
            values.update({'success': False, 'message': u'当前登录用户可能还不是上料员，请仔细检查！'})
            return values
        mesline = linefeeder.mesline_id
        materialcontainer = request.env['aas.container'].search([('barcode', '=', barcode)], limit=1)
        if not materialcontainer:
            values.update({'success': False, 'message': u'未获取当前容器信息，请仔细检查！'})
            return values
        if materialcontainer.isempty:
            values.update({'success': False, 'message': u'当前容器空空如也，没有物料可以使用！'})
            return values
        tempmaterial = materialcontainer.product_lines[0]
        product_id, product_code = tempmaterial.product_id.id, tempmaterial.product_id.default_code
        values.update({'material_code': product_code, 'tmaterial_id': 'material_'+str(product_id)})
        tvalues = request.env['aas.mes.feedmaterial'].action_feeding_withcontainer(mesline, barcode)
        if not tvalues.get('success', False):
            values.update({'success': False, 'message': tvalues.get('message', '')})
            return values
        feedomain = [('material_id', '=', product_id), ('mesline_id', '=', mesline.id)]
        feedinglist = request.env['aas.mes.feedmaterial'].search(feedomain)
        if feedinglist and len(feedinglist) > 0:
            values['material_qty'] = sum([feeding.material_qty for feeding in feedinglist])
        if values.get('success', False):
            values['tips'] = u'%s上料成功，已上料%s'% (values['material_code'], values['material_qty'])
        return values


    @http.route('/aaswechat/mes/feeding/refreshstock', type='json', auth="user")
    def aas_wechat_mes_feeding_refreshstock(self, meslineid):
        values = {'success': True, 'message': ''}
        feedinglist = request.env['aas.mes.feedmaterial'].search([('mesline_id', '=', meslineid)])
        if feedinglist and len(feedinglist) > 0:
            feedinglist, todelfeedinglist = [], request.env['aas.mes.feedmaterial']
            for feeding in feedinglist:
                fkey = 'F-'+str(feeding.material_id.id)+'-'+str(feeding.material_lot.id)
                if fkey in feedinglist:
                    todelfeedinglist |= feeding
                else:
                    feeding.action_refresh_stock()
            if todelfeedinglist and len(todelfeedinglist) > 0:
                todelfeedinglist.unlink()
        return values


    @http.route('/aaswechat/mes/feeding/materialdetail/<int:meslineid>/<int:materialid>', type='http', auth='user')
    def aas_wechat_mes_feeding_materialdetail(self, meslineid, materialid):
        values = {
            'success': True, 'message': '', 'mesline_name': '',
            'product_qty': 0.0, 'product_code': '', 'feedinglist': []
        }
        feeddomain = [('mesline_id', '=', meslineid), ('material_id', '=', materialid)]
        feedinglist = request.env['aas.mes.feedmaterial'].search(feeddomain)
        if feedinglist and len(feedinglist) > 0:
            tempfeeding = feedinglist[0]
            values.update({
                'mesline_name': tempfeeding.mesline_id.name,'product_code': tempfeeding.material_id.default_code
            })
            for feeding in feedinglist:
                values['feedinglist'].append({
                    'material_lot': feeding.material_lot.name, 'material_qty': feeding.material_qty
                })
                values['product_qty'] += feeding.material_qty
        return request.render('aas_mes.wechat_mes_linefeeding_materialdetail', values)
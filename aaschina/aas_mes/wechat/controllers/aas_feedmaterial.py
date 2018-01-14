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
        values = {'success': True, 'message': '', 'meslineid': '0', 'mesline_name': ''}
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
        workstationlist = []
        for wkstation in workstations:
            workstation = wkstation.workstation_id
            stationvals = {
                'workstation_id': workstation.id, 'workstation_name': workstation.name,
                'workstation_code': workstation.code, 'materiallist': []
            }
            feedomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
            materiallist = request.env['aas.mes.feedmaterial'].search(feedomain)
            if materiallist and len(materiallist) > 0:
                productdict = {}
                for tmaterial in materiallist:
                    productid = tmaterial.material_id.id
                    meslineid, workstationid = tmaterial.mesline_id.id, tmaterial.workstation_id.id
                    pkey = 'P'+str(productid)
                    if pkey in productdict:
                        productdict[pkey]['material_qty'] += tmaterial.material_qty
                    else:
                        productdict[pkey] = {
                            'material_qty': tmaterial.material_qty,
                            'material_code': tmaterial.material_id.default_code,
                            'mwmaterialid': str(meslineid)+'-'+str(workstationid)+'-'+str(productid)
                        }
                stationvals['materiallist'] = productdict.values()
            workstationlist.append(stationvals)
        values['workstationlist'] = workstationlist
        return request.render('aas_mes.wechat_mes_linefeeding', values)


    @http.route('/aaswechat/mes/feeding/materialscan', type='json', auth="user")
    def aas_wechat_mes_feeding_materialscan(self, barcode, workstationid):
        values = {
            'success': True, 'message': '', 'tips': '',
            'material_code': '', 'material_qty': 0.0, 'mwmterialid': '', 'workstation_id': '0'
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
        workstation = request.env['aas.mes.workstation'].browse(workstationid)
        if not workstation:
            values.update({'success': False, 'message': u'未搜索到相应工位，请仔细检查！'})
            return values
        tvalues = request.env['aas.mes.feedmaterial'].action_feeding_withlabel(mesline, workstation, barcode)
        if not tvalues.get('success', False):
            values.update({'success': False, 'message': tvalues.get('message', '')})
            return values
        values['workstation_id'] = workstation.id
        values['material_code'] = materiallabel.product_id.default_code
        values['mwmterialid'] = str(mesline.id)+'-'+str(workstation.id)+'-'+str(materiallabel.product_id.id)
        feedomain = [('material_id', '=', materiallabel.product_id.id)]
        feedomain += [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        feedinglist = request.env['aas.mes.feedmaterial'].search(feedomain)
        if feedinglist and len(feedinglist) > 0:
            values['material_qty'] = sum([feeding.material_qty for feeding in feedinglist])
        if values.get('success', False):
            values['tips'] = u'%s上料成功，已上料%s'% (values['material_code'], values['material_qty'])
        return values


    @http.route('/aaswechat/mes/feeding/containerscan', type='json', auth="user")
    def aas_wechat_mes_feeding_containerscan(self, barcode, workstationid):
        values = {
            'success': True, 'message': '', 'materiallist': [], 'tips': '',
            'material_code': '', 'material_qty': 0.0, 'mwmterialid': '', 'workstation_id': '0'
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
        workstation = request.env['aas.mes.workstation'].browse(workstationid)
        if not workstation:
            values.update({'success': False, 'message': u'未搜索到相应工位，请仔细检查！'})
            return values
        tvalues = request.env['aas.mes.feedmaterial'].action_feeding_withcontainer(mesline, workstation, barcode)
        if not tvalues.get('success', False):
            values.update({'success': False, 'message': tvalues.get('message', '')})
            return values
        tempmaterial = materialcontainer.product_lines[0]
        product_id, product_code = tempmaterial.product_id.id, tempmaterial.product_id.default_code
        values.update({
            'material_code': product_code, 'workstation_id': workstation.id,
            'mwmterialid': str(mesline.id)+'-'+str(workstation.id)+'-'+str(product_id)
        })
        feedomain = [('material_id', '=', product_id)]
        feedomain += [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        feedinglist = request.env['aas.mes.feedmaterial'].search(feedomain)
        if feedinglist and len(feedinglist) > 0:
            values['material_qty'] = sum([feeding.material_qty for feeding in feedinglist])
        if values.get('success', False):
            values['tips'] = u'%s上料成功，已上料%s'% (values['material_code'], values['material_qty'])
        return values


    @http.route('/aaswechat/mes/feeding/materialdel', type='json', auth="user")
    def aas_wechat_mes_feeding_materialdel(self, feeding_id):
        values = {'success': True, 'message': ''}
        try:
            request.env['aas.mes.feedmaterial'].browse(feeding_id).unlink()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        except ValidationError, ve:
            values.update({'success': False, 'message': ve.name})
            return values
        return values


    @http.route('/aaswechat/mes/feeding/refreshstock', type='json', auth="user")
    def aas_wechat_mes_feeding_refreshstock(self, meslineid):
        values = {'success': True, 'message': ''}
        feedinglist = request.env['aas.mes.feedmaterial'].search([('mesline_id', '=', meslineid)])
        if feedinglist and len(feedinglist) > 0:
            for feeding in feedinglist:
                feeding.action_refresh_stock()
        return values


    @http.route('/aaswechat/mes/feeding/materialdetail/<string:mwmaterialid>', type='http', auth='user')
    def aas_wechat_mes_feeding_materialdetail(self, mwmaterialid):
        values = {
            'success': True, 'message': '', 'mesline_name': '',
            'workstation_name': '', 'product_code': '', 'materialotlist': []
        }
        tempids = mwmaterialid.split('-')
        meslineid, workstationid, materialid = int(tempids[0]), int(tempids[1]), int(tempids[2])
        feeddomain = [('material_id', '=', materialid)]
        feeddomain += [('mesline_id', '=', meslineid), ('workstation_id', '=', workstationid)]
        feedinglist = request.env['aas.mes.feedmaterial'].search(feeddomain)
        if feedinglist and len(feedinglist) > 0:
            tempfeed = feedinglist[0]
            values.update({
                'mesline_name': tempfeed.mesline_id.name,
                'workstation_name': tempfeed.workstation_id.name, 'product_code': tempfeed.material_id.default_code
            })
            values['materialotlist'] = [{
                'lot_name': feeding.material_lot.name, 'lot_qty': feeding.material_qty
            } for feeding in feedinglist]
        return request.render('aas_mes.wechat_mes_linefeeding_materialdetail', values)
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
        values = {'success': True, 'message': '', 'meslineid': '0'}
        loginuser = request.env.user
        feeddomain = [('lineuser_id', '=', loginuser.id), ('mesrole', '=', 'feeder')]
        linefeeder = request.env['aas.mes.lineusers'].search(feeddomain, limit=1)
        if not linefeeder:
            values.update({'success': False, 'message': u'当前登录用户可能还不是上料员，请仔细检查！'})
            return request.render('aas_mes.wechat_mes_message', values)
        mesline = linefeeder.mesline_id
        values['meslineid'] = mesline.id
        workstations = request.env['aas.mes.line.workstation'].search([('mesline_id', '=', mesline.id)], order='sequence')
        if not workstations or len(workstations) <= 0:
            values.update({'success': False, 'message': u'产线%s还未设置工位，请先设置工位，再进行上料操作！'})
            return request.render('aas_mes.wechat_mes_message', values)
        workstationlist = []
        for wkstation in workstations:
            workstation = wkstation.workstation_id
            stationvals = {
                'workstation_id': workstation.id, 'workstation_name': workstation.name, 'workstation_code': workstation.code, 'materiallist': []
            }
            materiallist = request.env['aas.mes.feedmaterial'].search([('workstation_id', '=', workstation.id)])
            if materiallist and len(materiallist) > 0:
                stationvals['materiallist'] = [{
                    'feeding_id': feedmaterial.id, 'material_code': feedmaterial.material_id.default_code,
                    'material_lot': feedmaterial.material_lot.name, 'material_qty': feedmaterial.material_qty
                } for feedmaterial in materiallist]
            workstationlist.append(stationvals)
        values['workstationlist'] = workstationlist
        return request.render('aas_mes.wechat_mes_linefeeding', values)


    @http.route('/aasmes/mes/feeding/materialscan', type='json', auth="user")
    def aas_wechat_mes_feeding_materialscan(self, barcode, workstationid):
        values = {'success': True, 'message': ''}
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
        material, mlot = materiallabel.product_id, materiallabel.product_lot
        locationids = [mesline.location_production_id.id]
        for mteriallocation in mesline.location_material_list:
            locationids.append(mteriallocation.location_id.id)
        locationlist = request.env['stock.location'].search([('id', 'child_of', locationids)])
        if materiallabel.location_id.id not in locationlist.ids:
            values.update({'success': False, 'message': u'请不要扫描非[%s]产线的物料！'% mesline.name})
            return values
        materialdomain = [('material_id', '=', material.id), ('material_lot', '=', mlot.id)]
        materialdomain.extend([('workstation_id', '=', workstationid), ('mesline_id', '=', mesline.id)])
        tempfeedmaterial = request.env['aas.mes.feedmaterial'].search(materialdomain, limit=1)
        if tempfeedmaterial:
            values.update({'success': False, 'message': u'当前[%s]批次的原料[%s]已经上过料，请不要重复操作！'% (mlot.name, material.default_code)})
            return values
        feedmaterial = request.env['aas.mes.feedmaterial'].create({
            'material_id': material.id, 'material_lot': mlot.id, 'workstation_id': workstationid, 'mesline_id': mesline.id
        })
        values.update({
            'feeding_id': feedmaterial.id, 'material_code': materiallabel.product_code,
            'material_lot': materiallabel.product_lotname, 'material_qty': feedmaterial.material_qty
        })
        return values

    @http.route('/aasmes/mes/feeding/containerscan', type='json', auth="user")
    def aas_wechat_mes_feeding_containerscan(self, barcode, workstationid):
        values = {'success': True, 'message': '', 'materiallist': []}
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
        workstation = request.env['aas.mes.workstation'].browse(workstationid)
        if not workstation:
            values.update({'success': False, 'message': u'未搜索到相应工位，请仔细检查！'})
            return values
        locationids = [mesline.location_production_id.id]
        for mteriallocation in mesline.location_material_list:
            locationids.append(mteriallocation.location_id.id)
        locationlist = request.env['stock.location'].search([('id', 'child_of', locationids)])
        if materialcontainer.stock_location_id.id not in locationlist.ids:
            # 容器不在当前产线自动调拨
            materiallocation = mesline.location_material_list[0].location_id
            materialcontainer.write({'location_id': materiallocation.id})
        productdict = {}
        if materialcontainer.product_lines and len(materialcontainer.product_lines) > 0:
            for pline in materialcontainer.product_lines:
                if float_compare(pline.stock_qty, 0.0, precision_rounding=0.000001) > 0.0:
                    pkey = 'P-'+str(pline.product_id.id)+'-'+str(pline.product_lot.id)
                    if pkey not in productdict:
                        productdict[pkey] = {
                            'product_id': pline.product_id.id,  'product_lot': pline.product_lot.id, 'product_qty': pline.stock_qty
                        }
                    else:
                        productdict[pkey]['product_qty'] += pline.stock_qty
        else:
            values.update({'success': False, 'message': u'容器中空空如也，请仔细检查！'})
            return values
        if productdict and len(productdict) > 0:
            materiallist = []
            for pkey, pval in productdict.items():
                tempdomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
                tempdomain.extend([('material_id', '=', pval['product_id']), ('material_lot', '=', pval['product_lot'])])
                tempfeed = request.env['aas.mes.feedmaterial'].search(tempdomain, limit=1)
                if not tempfeed:
                    tempfeed = request.env['aas.mes.feedmaterial'].create({
                        'mesline_id': mesline.id, 'workstation_id': workstation.id,
                        'material_id': pval['product_id'], 'material_lot': pval['product_lot']
                    })
                    tempfeed.action_refresh_stock()
                    materiallist.append({
                        'feeding_id': tempfeed.id,
                        'material_code': tempfeed.material_id.default_code,
                        'material_lot': tempfeed.material_lot.name,
                        'material_qty': tempfeed.material_qty
                    })
            values['materiallist'] = materiallist
        return values


    @http.route('/aasmes/mes/feeding/materialdel', type='json', auth="user")
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


    @http.route('/aasmes/mes/feeding/refreshstock', type='json', auth="user")
    def aas_wechat_mes_feeding_refreshstock(self, meslineid):
        values = {'success': True, 'message': ''}
        feedinglist = request.env['aas.mes.feedmaterial'].search([('mesline_id', '=', meslineid)])
        if feedinglist and len(feedinglist) > 0:
            for feeding in feedinglist:
                feeding.action_refresh_stock()
        return values
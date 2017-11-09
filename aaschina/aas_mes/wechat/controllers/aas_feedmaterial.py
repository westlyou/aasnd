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
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

class AASFeedmaterialWechatController(http.Controller):

    @http.route('/aaswechat/mes/linefeeding', type='http', auth='user')
    def aas_wechat_mes_linefeeding(self):
        values = {'success': True, 'message': ''}
        loginuser = request.env.user
        feeddomain = [('lineuser_id', '=', loginuser.id), ('mesrole', '=', 'feeder')]
        linefeeder = request.env['aas.mes.lineusers'].search(feeddomain, limit=1)
        if not linefeeder:
            values.update({'success': False, 'message': u'当前登录用户可能还不是上料员，请仔细检查！'})
            return request.render('aas_mes.wechat_mes_message', values)
        mesline = linefeeder.mesline_id
        workstations = request.env['aas.mes.line.workstation'].search([('mesline_id', '=', mesline.id)], order='sequence')
        if not workstations or len(workstations) <= 0:
            values.update({'success': False, 'message': u'产线%s还未设置工位，请先设置工位，再进行上料操作！'})
            return request.render('aas_mes.wechat_mes_message', values)
        workstationlist = []
        for wkstation in workstations:
            stationvals = {
                'workstation_id': wkstation.id, 'workstation_name': wkstation.name,
                'workstation_code': wkstation.code, 'materiallist': []
            }
            materiallist = request.env['aas.mes.feedmaterial'].search([('workstation_id', '=', wkstation.id)])
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
            return request.render('aas_mes.wechat_mes_message', values)
        mesline = linefeeder.mesline_id.id
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
        materialdomain.append(('workstation_id', '=', workstationid))
        tempfeedmaterial = request.env['aas.mes.feedmaterial'].search(materialdomain, limit=1)
        if tempfeedmaterial:
            values.update({'success': False, 'message': u'当前[%s]批次的原料[%s]已经上过料，请不要重复操作！'% (mlot.name, material.default_code)})
            return values
        feedmaterial = request.env['aas.mes.feedmaterial'].create({
            'material_id': material.id, 'material_lot': mlot.id, 'workstation_id': workstationid
        })
        values.update({
            'feeding_id': feedmaterial.id, 'material_code': materiallabel.product_code,
            'material_lot': materiallabel.product_lotname, 'material_qty': feedmaterial.material_qty
        })
        return values
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


    @http.route('/aaswechat/mes/feeding/materialscan', type='json', auth="user")
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
        return request.env['aas.mes.feedmaterial'].action_feeding_withlabel(mesline, workstation, barcode)


    @http.route('/aaswechat/mes/feeding/containerscan', type='json', auth="user")
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
        return request.env['aas.mes.feedmaterial'].action_feeding_withcontainer(mesline, workstation, barcode)


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
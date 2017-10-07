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
from odoo.exceptions import AccessDenied,UserError,ValidationError

logger = logging.getLogger(__name__)

class AASFeedmaterialWechatController(http.Controller):

    @http.route('/aaswechat/mes/workstationfeeding/<string:barcode>', type='http', auth='user')
    def aas_wechat_mes_workstationfeeding(self, barcode):
        values = {'success': True, 'message': '', 'materiallist': []}
        workstation = request.env['aas.mes.workstation'].search([('barcode', '=', barcode)], limit=1)
        if not workstation:
            values.update({'success': False, 'message': u'工位异常，请仔细检查是否存在此工位！'})
            return request.render('aas_mes.wechat_mes_workstationfeeding', values)
        feedmaterials = request.env['aas.mes.feedmaterial'].search([('workstation_id', '=', workstation.id)])
        if feedmaterials and len(feedmaterials) > 0:
            materiallist = []
            for feedmaterial in feedmaterials:
                feedmaterial.action_refresh_stock()
                materiallist.append({
                    'feedmaterialid': feedmaterial.id, 'material_code': feedmaterial.material_id.default_code,
                    'material_lot': feedmaterial.material_lot.name, 'material_qty': feedmaterial.material_qty
                })
            values['materiallist'] = materiallist
        values.update({
            'workstation_name': workstation.name, 'workstation_code': workstation.code,
            'mesline_name': workstation.mesline_id.name
        })
        return request.render('aas_mes.wechat_mes_workstationfeeding', values)
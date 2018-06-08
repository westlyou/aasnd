# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-6-7 17:18
"""

import logging
import werkzeug

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied,UserError,ValidationError

logger = logging.getLogger(__name__)

class AASFinalinspectionWechatController(http.Controller):

    @http.route('/aaswechat/mes/finalinspection/<string:barcode>', type='http', auth='user')
    def aas_wechat_mes_finalinspection(self, barcode):
        finalvals = request.env['aas.mes.finalinspection'].action_scanning(barcode)
        if not finalvals.get('success', False):
            return request.render('aas_mes.wechat_mes_message', finalvals)
        return request.render('aas_mes.wechat_mes_finalinspection', finalvals)


    @http.route('/aaswechat/mes/finalinspection/scanemployee', type='json', auth="user")
    def aas_wechat_finalinspection_scanemployee(self, barcode):
        return request.env['aas.hr.employee'].action_scanning(barcode)


    @http.route('/aaswechat/mesline/badmodelist', type='json', auth="user")
    def aas_wechat_mesline_badmodelist(self, meslineid):
        values = {'success': True, 'message': '', 'badmodelist': []}
        badmodelist, badmodeids = [], []
        workstationlist = request.env['aas.mes.line.workstation'].search([('mesline_id', '=', meslineid)])
        if workstationlist and len(workstationlist) > 0:
            for tworkstation in workstationlist:
                workstation = tworkstation.workstation_id
                if not workstation.badmode_lines or len(workstation.badmode_lines) <= 0:
                    continue
                for badline in workstation.badmode_lines:
                    badmode = badline.badmode_id
                    if badmode.id in badmodeids:
                        continue
                    badmodeids.append(badmode.id)
                    badmodelist.append({'value': str(badmode.id), 'text': badmode.name+'['+badmode.code+']'})
        commonbadmodes = request.env['aas.mes.badmode'].search([('universal', '=', True)])
        if commonbadmodes and len(commonbadmodes) > 0:
            for badmode in commonbadmodes:
                if badmode.id in badmodeids:
                    continue
                badmodeids.append(badmode.id)
                badmodelist.append({'value': str(badmode.id), 'text': badmode.name+'['+badmode.code+']'})
        values['badmodelist'] = badmodelist
        return values


    @http.route('/aaswechat/mes/finalinspection/done', type='json', auth="user")
    def aas_wechat_mes_finalinspection_done(self, workorderid, employeeid, labelid=0, containerid=0, badmodelines=[]):
        return request.env['aas.mes.finalinspection'].action_finalinspect(workorderid, employeeid,
                                                                          labelid, containerid, badmodelines)

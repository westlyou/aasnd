# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-4-28 22:36
"""

import logging
import werkzeug

from odoo import http, fields
from odoo.http import request
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

class AASAtteandanceWechatController(http.Controller):

    @http.route('/aaswechat/mes/attendance', type='http', auth='user')
    def aas_wechat_mes_attendance(self):
        values = {'success': True, 'message': ''}
        return request.render('aas_mes.wechat_mes_attendance', values)



    @http.route('/aaswechat/mes/attendance/scanning', type='json', auth="user")
    def aas_wechat_mes_attendance_scanning(self, barcode, meslineid, workstationid=None, equipmentid=None):
        values = {'success': True, 'message': ''}
        employee = request.env['aas.hr.employee'].search([('barcode', '=', barcode)], limit=1)
        if not employee:
            values.update({'success': False, 'message': u"请仔细检查是否扫描了有效的员工卡！"})
            return values
        mesline = request.env['aas.mes.line'].browse(meslineid)
        workstation, equipment = False, False
        if workstationid:
            workstation = request.env['aas.mes.workstation'].browse(workstationid)
        if equipmentid:
            equipment = request.env['aas.equipment.equipment'].browse(equipmentid)
        values = request.env['aas.mes.attendance'].action_scanning(employee, mesline,
                                                                   workstation=workstation, equipment=equipment)
        return values


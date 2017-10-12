# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-10-12 14:34
"""

import logging
import werkzeug

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessDenied,UserError,ValidationError

logger = logging.getLogger(__name__)


class AASMESSerialnumberController(http.Controller):

    @http.route('/aasmes/serialnumber', type='http', auth="user")
    def aasmes_serialnumber(self):
        login = request.env.user
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', login.id)], limit=1)
        currenttime = fields.Datetime.to_timezone_time(fields.Datetime.now(), 'Asia/Shanghai')
        isocalendar = currenttime.isocalendar()
        values = {'year': str(isocalendar[0])[2:], 'week': str(100+isocalendar[1])[1:], 'weekday': str(isocalendar[2])}
        values.update({'extend': '0', 'type': ''})
        workorder = lineuser.mesline_id.workorder_id


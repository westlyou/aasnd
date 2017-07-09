# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-7 22:57
"""

import logging
from odoo import http
from odoo.http import request

logger = logging.getLogger(__name__)


class AASBaseController(http.Controller):

    @http.route('/aas/base/labelprinters', type='json', auth="user")
    def action_loading_labelprinter(self, model):
        records = []
        printers = request.env['aas.label.printer'].search([])
        if printers and len(printers) > 0:
            records = [{'pid': str(printer.id), 'pname': printer.name} for printer in printers]
        return records

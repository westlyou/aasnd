# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-10-13 14:14
"""

import logging

from odoo import http
from odoo.http import request

logger = logging.getLogger(__name__)

class AASMESController(http.Controller):

    @http.route('/aasmes/printerlist', type='json', auth="user")
    def aasmes_printerlist(self, q=None, page=1):
        logger.info('dafsadfadfa')
        values = {'items': [], 'total_count': 0}
        search_domain = []
        if q:
            search_domain.append(('name', 'ilike', q))
        printers = request.env['aas.label.printer'].search(search_domain)
        if printers:
            values['items'] = [{'id': sprinter.id, 'text': sprinter.name} for sprinter in printers]
            values['total_count'] = len(printers)
        return values

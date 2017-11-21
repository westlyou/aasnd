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
    def aasmes_printerlist(self, q=None, page=1, limit=30):
        values = {'items': [], 'total_count': 0}
        search_domain = []
        if q:
            search_domain.append(('name', 'ilike', q))
        printers = request.env['aas.label.printer'].search(search_domain, offset=(page-1)*limit)
        if printers and len(printers) > 0:
            values['items'] = [{'id': sprinter.id, 'text': sprinter.name} for sprinter in printers]
        values['total_count'] = request.env['aas.label.printer'].search_count(search_domain)
        return values


    @http.route('/aasmes/badmodelist', type='json', auth="user")
    def aasmes_badmodelist(self, q=None, page=1, limit=30):
        values = {'items': [], 'total_count': 0}
        search_domain = []
        if q:
            search_domain.append(('name', 'ilike', q))
        badmodelist = request.env['aas.mes.badmode'].search(search_domain, offset=(page-1)*limit)
        if badmodelist and len(badmodelist) > 0:
            values['items'] = [{'id': badmode.id, 'text': badmode.name} for badmode in badmodelist]
        values['total_count'] = request.env['aas.mes.badmode'].search_count(search_domain)
        return values


    @http.route('/aasmes/workstationlist', type='json', auth="user")
    def aasmes_workstationlist(self, q=None, page=1, limit=30):
        values = {'items': [], 'total_count': 0}
        search_domain = []
        if q:
            search_domain.append(('name', 'ilike', q))
        workstationlist = request.env['aas.mes.workstation'].search(search_domain, offset=(page-1)*limit)
        if workstationlist and len(workstationlist) > 0:
            values['items'] = [{'id': workstation.id, 'text': workstation.name} for workstation in workstationlist]
        values['total_count'] = request.env['aas.mes.workstation'].search_count(search_domain)
        return values

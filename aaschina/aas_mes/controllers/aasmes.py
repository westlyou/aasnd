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
            search_domain += ['|', ('name', 'ilike', q), ('code', 'ilike', q)]
        badmodelist = request.env['aas.mes.badmode'].search(search_domain, offset=(page-1)*limit)
        if badmodelist and len(badmodelist) > 0:
            values['items'] = [{'id': badmode.id, 'text': badmode.name+'['+badmode.code+']'} for badmode in badmodelist]
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


    @http.route('/aasmes/loadproductlist', type='json', auth="user")
    def aasmes_loadproductlist(self, q=None, page=1, limit=20):
        values = {'items': [], 'total_count': 0}
        search_domain = []
        if q:
            search_domain.append(('default_code', 'ilike', '%'+q+'%'))
        productlist = request.env['product.product'].search(search_domain, offset=(page-1)*limit)
        if productlist and len(productlist) > 0:
            values['items'] = [{'id': tproduct.id, 'text': tproduct.default_code} for tproduct in productlist]
        values['total_count'] = request.env['product.product'].search_count(search_domain)
        return values


    @http.route('/aasmes/meslines', type='json', auth="user")
    def aas_meslines(self):
        values = {'success': True, 'message': '', 'meslines': []}
        meslines = request.env['aas.mes.line'].search([])
        if meslines and len(meslines) > 0:
            values['meslines'] = [{'value': str(mesline.id), 'text': mesline.name} for mesline in meslines]
        return values

    @http.route('/aasmes/mesline/workstations', type='json', auth="user")
    def aas_mesline_workstations(self, meslineid):
        values = {'success': True, 'message': '', 'workstations': []}
        mesline = request.env['aas.mes.line'].browse(meslineid)
        if mesline.workstation_lines and len(mesline.workstation_lines) > 0:
            values['workstations'] = [{
                'value': str(mstation.workstation_id.id), 'text': mstation.workstation_id.name
            } for mstation in mesline.workstation_lines]
        return values


    @http.route('/aasmes/equipmentlist', type='json', auth="user")
    def aas_equipmentlist(self, meslineid=None, workstationid=None):
        values = {'success': True, 'message': '', 'equipments': []}
        tempdomain = []
        if meslineid:
            tempdomain.append(('mesline_id', '=', meslineid))
        if workstationid:
            tempdomain.append(('workstation_id', '=', workstationid))
        if not tempdomain or len(tempdomain) <= 0:
            values.update({'success': False, 'message': u'请先设置好产线或工位！'})
            return values
        equipmentlist = request.env['aas.equipment.equipment'].search(tempdomain)
        if equipmentlist and len(equipmentlist) > 0:
            values['equipments'] = [{
                'value': str(equipment.id), 'text': equipment.code
            } for equipment in equipmentlist]
        return values





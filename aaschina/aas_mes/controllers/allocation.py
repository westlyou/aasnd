# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-11-20 10:15
"""

import logging

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

class AASMESAllocationController(http.Controller):

    @http.route('/aasmes/allocation', type='http', auth="user")
    def aasmes_allocation(self):
        values = {'success': True, 'message': '', 'mesline_id': '0', 'mesline_name': '', 'showmeslines': 'none'}
        login = request.env.user
        values['checker'] = login.name
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', login.id)], limit=1)
        if lineuser and lineuser.mesline_id:
            values.update({'mesline_id': lineuser.mesline_id.id, 'mesline_name': lineuser.mesline_id.name})
        else:
            values['showmeslines'] = 'block'
        meslines = request.env['aas.mes.line'].search([])
        values['meslines'] = [{'mesline_id': mesline.id, 'mesline_name': mesline.name} for mesline in meslines]
        return request.render('aas_mes.aas_allocation', values)


    @http.route('/aasmes/allocation/scanemployee', type='json', auth="user")
    def aasmes_allocation_scanemployee(self, barcode):
        values = {'success': True, 'message': ''}
        employee = request.env['aas.hr.employee'].search([('barcode', '=', barcode)], limit=1)
        if not employee:
            values.update({'success': False, 'message': u'未搜索到此员工，请仔细检查是否扫描了无效条码！'})
            return values
        values.update({'employee_id': employee.id, 'employee_name': employee.name})
        return values

    @http.route('/aasmes/allocation/scanlabel', type='json', auth="user")
    def aasmes_allocation_scanlabel(self, barcode, meslineid):
        values = {'success': True, 'message': ''}
        mesline = request.env['aas.mes.line'].browse(meslineid)
        if not mesline.location_production_id or (not mesline.location_material_list or len(mesline.location_material_list) <= 0):
            values.update({'success': False, 'message': u'产线%s未设置成品或原料库位！'% mesline.name})
            return values
        locationids = [malocation.location_id.id for malocation in mesline.location_material_list]
        locationids.append(mesline.location_production_id.id)
        locationids = request.env['stock.location'].search([('id', 'child_of', locationids)]).ids
        label = request.env['aas.product.label'].search([('barcode', '=', barcode)], limit=1)
        if not label.isproduction:
            values.update({'success': False, 'message': u'非产线标签，不可以扫描！'})
            return values
        if label.location_id.id in locationids:
            values.update({'success': False, 'message': u'标签已经在产线%s，请不要扫描！'% mesline.name})
            return values
        values.update({
            'label_id': label.id, 'label_name': label.name, 'product_code': label.product_code,
            'product_uom': label.product_uom.name, 'product_lot': label.product_lot.name, 'product_qty': label.product_qty
        })
        return values


    @http.route('/aasmes/allocation/scancontainer', type='json', auth="user")
    def aasmes_allocation_scancontainer(self, barcode, meslineid):
        values = {'success': True, 'message': ''}
        mesline = request.env['aas.mes.line'].browse(meslineid)
        if not mesline.location_production_id or (not mesline.location_material_list or len(mesline.location_material_list) <= 0):
            values.update({'success': False, 'message': u'产线%s未设置成品或原料库位！'% mesline.name})
            return values
        locationids = [malocation.location_id.id for malocation in mesline.location_material_list]
        locationids.append(mesline.location_production_id.id)
        locationids = request.env['stock.location'].search([('id', 'child_of', locationids)]).ids
        container = request.env['aas.container'].search([('barcode', '=', barcode)], limit=1)
        if container.isempty:
            values.update({'success': False, 'message': u'容器%s是一个空容器，请不要调拨一个空容器！'% container.name})
            return values
        if container.location_id.id in locationids:
            values.update({'success': False, 'message': u'容器%s已经在产线%s线边库中，无需再调拨！'% (container.name, mesline.name)})
            return values
        values.update({'container_id': container.id, 'container_name': container.name})
        prdocutline = container.product_lines[0]
        values.update({
            'product_code': prdocutline.product_id.default_code, 'product_uom': prdocutline.product_id.uom_id.name,
            'product_lot': prdocutline.product_lot.name, 'product_qty': prdocutline.product_qty
        })
        return values


    @http.route('/aasmes/allocation/doallocate', type='json', auth="user")
    def aasmes_allocation_doallocate(self, meslineid, operatorid, containerids=[], labelids=[]):
        values = {'success': True, 'message': ''}
        try:
            allocateresult = request.env['aas.mes.allocation'].action_allocation(meslineid, operatorid, containerids, labelids)
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        except ValidationError, ve:
            values.update({'success': False, 'message': ve.name})
            return values
        values.update(allocateresult)
        return values

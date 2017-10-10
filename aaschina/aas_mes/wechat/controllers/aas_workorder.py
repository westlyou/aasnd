# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-10-10 10:03
"""

import logging
import werkzeug

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError, ValidationError

from . import get_china_time

logger = logging.getLogger(__name__)

class AASWorkorderWechatController(http.Controller):

    @http.route('/aaswechat/mes/workorderscan', type='json', auth="user")
    def aas_wechat_mes_workorderscan(self, barcode):
        values = {'success': True, 'message': ''}
        workorder = request.env['aas.mes.workorder'].search([('barcode', '=', barcode)], limit=1)
        if not workorder:
            values.update({'success': False, 'message': u'当前工单可能已经不存在了，请仔细检查！'})
            return values
        if workorder.state == 'draft':
            values.update({'success': False, 'message': u'工单还未投放，请联系相关人员处理！'})
            return values
        if workorder.state == 'done':
            values.update({'success': False, 'message': u'工单已完成，相关信息请登录系统查询！'})
            return values
        if not workorder.workticket_lines or len(workorder.workticket_lines) <= 0:
            values.update({'success': False, 'message': u'如果是非工位式生产的工单请不要在此处操作，请仔细检查！'})
            return values
        workcenter = workorder.workcenter_id
        if not workcenter:
            values.update({'success': False, 'message': u'工票异常，工单可能还未生成待处理工票！'})
            return values
        values.update({'workticketid': workcenter.id, 'start': True})
        if workcenter.state != 'waiting':
            values['start'] = False
        return values


    @http.route('/aaswechat/mes/workticket/start/<int:workticketid>', type='http', auth='user')
    def aas_wechat_mes_workticketstart(self, workticketid):
        values = {'success': True, 'message': ''}
        workticket = request.env['aas.mes.workticket'].browse(workticketid)
        if not workticket:
            values.update({'success': False, 'message': u'工票异常，可能已经被删除！'})
            return request.render('aas_mes.wechat_mes_message', values)
        if workticket.state in ['producing', 'pause']:
            return http.redirect_with_hash('/aaswechat/mes/workticket/finish/'+str(workticketid))
        if workticket.state == 'done':
            values.update({'success': False, 'message': u'工票已完工，不可以再操作！'})
            return request.render('aas_mes.wechat_mes_message', values)
        values.update({
            'workticket_id': workticketid, 'workticket_name': workticket.name,
            'sequence': workticket.sequence, 'workcenter_name': workticket.workcenter_name,
            'product_code': workticket.product_id.default_code, 'input_qty': workticket.input_qty,
            'mesline_name': workticket.mesline_name
        })
        return request.render('aas_mes.wechat_mes_workticketstart', values)


    @http.route('/aaswechat/mes/workticket/startdone', type='json', auth="user")
    def aas_wechat_mes_workticket_startdone(self, workticketid):
        values = {'success': True, 'message': '', 'workticket_id': workticketid}
        workticket = request.env['aas.mes.workticket'].browse(workticketid)
        if not workticket:
            values.update({'success': False, 'message': u'工票异常，可能已经被删除！'})
            return values
        workstation = workticket.workcenter_id.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'工序%s还未设置工位信息，无法提取员工信息，请联系相关人员设置工位！'% workticket.workcenter_name})
            return values
        if not workstation.employee_lines or len(workstation.employee_lines) <= 0:
            values.update({'success': False, 'message': u'工位%s还没有员工信息，请先刷卡上岗再操作工单！'% workstation.name})
            return values
        try:
            workticket.action_doing_start()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        except ValidationError, ve:
            values.update({'success': False, 'message': ve.name})
            return values
        return values



    @http.route('/aaswechat/mes/workticket/finish/<int:workticketid>', type='http', auth='user')
    def aas_wechat_mes_workticketfinish(self, workticketid):
        values = {'success': True, 'message': ''}
        workticket = request.env['aas.mes.workticket'].browse(workticketid)
        if not workticket:
            values.update({'success': False, 'message': u'工票异常，可能已经被删除！'})
            return request.render('aas_mes.wechat_mes_message', values)
        if workticket.state == 'waiting':
            return http.redirect_with_hash('/aaswechat/mes/workticket/start/'+str(workticketid))
        if workticket.state == 'done':
            values.update({'success': False, 'message': u'工票已完工，不可以再操作！'})
        values.update({
            'workticket_id': workticketid, 'workticket_name': workticket.name,
            'sequence': workticket.sequence, 'workcenter_name': workticket.workcenter_name,
            'product_code': workticket.product_id.default_code, 'input_qty': workticket.input_qty,
            'mesline_name': workticket.mesline_name, 'time_start': get_china_time(workticket.time_start),
            'workstation_name': '', 'employeelist': [], 'equipmentlist': []
        })
        if workticket.workcenter_id.workstation_id:
            workstation = workticket.workcenter_id.workstation_id
            values['workstation_name'] = workstation.name
            if workstation.employee_lines and len(workstation.employee_lines) > 0:
                values['employeelist'] = [{
                    'employee_name': temployee.name, 'employee_code': temployee.code
                } for temployee in workstation.employee_lines]
            if workstation.equipment_lines and len(workstation.equipment_lines) > 0:
                values['equipmentlist'] = [{
                    'equipment_name': tequipment.name, 'equipment_code': tequipment.code
                } for tequipment in workstation.equipment_lines]
        return request.render('aas_mes.wechat_mes_workticketfinish', values)


    @http.route('/aaswechat/mes/workticket/badmodelist', type='json', auth="user")
    def aas_wechat_mes_workticket_badmodelist(self, workticketid):
        values = {'success': True, 'message': ''}
        workticket = request.env['aas.mes.workticket'].browse(workticketid);
        badmode_lines = workticket.workcenter_id.badmode_lines
        if not badmode_lines or len(badmode_lines) <= 0:
            values.update({'success': False, 'message': u'工序%s还未设置不良模式，请联系工艺设置！'% workticket.workcenter_id.name})
            return values
        values['badmodelist'] = [{
            'value': str(badmode.badmode_id.id), 'text': badmode.badmode_id.name
        } for badmode in badmode_lines]
        return values


    @http.route('/aaswechat/mes/workticket/startdone', type='json', auth="user")
    def aas_wechat_mes_workticket_startdone(self, workticketid, badmode_lines=[]):
        values = {'success': True, 'message': '', 'workticket_id': workticketid}
        workticket = request.env['aas.mes.workticket'].browse(workticketid)
        if not workticket:
            values.update({'success': False, 'message': u'工票异常，可能已经被删除！'})
            return values
        workstation = workticket.workcenter_id.workstation_id
        if not workstation:
            values.update({'success': False, 'message': u'工序%s还未设置工位信息，无法提取员工信息，请联系相关人员设置工位！'% workticket.workcenter_name})
            return values
        if not workstation.employee_lines or len(workstation.employee_lines) <= 0:
            values.update({'success': False, 'message': u'工位%s还没有员工信息，请先刷卡上岗再操作工单！'% workstation.name})
            return values
        try:
            if badmode_lines and len(badmode_lines) > 0:
                workticket.write({'badmode_lines': [(0, 0, badmode) for badmode in badmode_lines]})
            workticket.action_doing_finish()
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        except ValidationError, ve:
            values.update({'success': False, 'message': ve.name})
            return values
        return values

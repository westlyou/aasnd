# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-10-15 23:18
"""


from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

class AASEBSProduction(models.Model):
    _name = 'aas.ebs.production'
    _description = 'AAS EBS Mainorder'
    _order = 'id desc'
    _auto = False
    _log_access = False

    name = fields.Char(string=u'主工单号')
    product_id = fields.Integer(string=u'产品')
    product_qty = fields.Float(string=u'数量')
    date_released = fields.Datetime(string=u'创建日期')
    scheduled_start_date = fields.Datetime(string=u'计划开始日期')
    scheduled_completion_date = fields.Datetime(string=u'计划完成日期')

    creation_date = fields.Datetime(string=u'创建日期')
    created_by = fields.Integer(string='created_by')
    last_update_date = fields.Datetime(string=u'修改日期')
    last_updated_by = fields.Integer(string='last_updated_by')


class AASMESMainorder(models.Model):
    _inherit = 'aas.mes.mainorder'

    @api.model
    def action_import_order(self, order_number):
        values = {'success': True, 'message': ''}
        tempmainorder = self.env['aas.mes.mainorder'].search([('name', '=', order_number)], limit=1)
        if tempmainorder:
            values.update({'success': False, 'message': u'工单%s已经导入或已经生成，不可以重复操作！'% order_number})
            return values
        ebsproduction = self.env['aas.ebs.production'].search([('name', '=', order_number)], limit=1)
        if not ebsproduction:
            values.update({'success': False, 'message': u'工单%s不存在，请不要操作！'% order_number})
            return values
        product = self.env['product.product'].browse(ebsproduction.product_id)
        if not product:
            values.update({'success': False, 'message': u'导入工单的产品不存在，请仔细检查！'})
            return values
        mainordervals = {
            'name': ebsproduction.name,
            'product_id': ebsproduction.product_id,
            'product_uom': product.uom_id.id,
            'product_qty': ebsproduction.product_qty,
            'actual_qty': ebsproduction.product_qty,
            'imported': True,
            'split_unit_qty': product.split_qty
        }
        tempbom = self.env['aas.mes.bom'].search([('product_id', '=', product.id), ('active', '=', True)], limit=1)
        if tempbom:
            mainordervals['aas_bom_id'] = tempbom.id
            if tempbom.routing_id:
                mainordervals['routing_id'] = tempbom.routing_id.id
        if product.product_yield:
            values['actual_qty'] = ebsproduction.product_qty / product.product_yield
        if product.split_qty:
            values['split_unit_qty'] = product.split_qty
        mainorder = self.env['aas.mes.mainorder'].create(mainordervals)
        values['mainorder_id'] = mainorder.id
        return values
# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-9-22 15:56
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

# 生产追溯
class AASMESTracing(models.Model):
    _name = 'aas.mes.tracing'
    _description = 'AAS MES Tracing'
    _rec_name = 'product_code'
    _order = 'date_finish desc,date_start asc'

    mainorder_id = fields.Many2one(comodel_name='aas.mes.mainorder', string=u'主工单', index=True)
    mainorder_name = fields.Char(string=u'主工单名称')
    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'子工单', ondelete='cascade', index=True)
    workorder_name = fields.Char(string=u'子工单')
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='restrict', index=True)
    workcenter_name = fields.Char(string=u'工序名称')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'生产线', ondelete='restrict', index=True)
    mesline_name = fields.Char(string=u'生产线名称')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict', index=True)
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_code = fields.Char(string=u'产品编码')
    date_code = fields.Char(string='DateCode')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'成品批次', ondelete='restrict', index=True)
    product_lot_name = fields.Char(string=u'成品批次名称')
    date_start = fields.Datetime(string=u'开始时间', copy=False)
    date_finish = fields.Datetime(string=u'结束时间', copy=False)
    materiallist = fields.Text(string=u'原料信息')
    equipmentlist = fields.Text(string=u'设备信息')
    employeelist = fields.Text(string=u'员工信息')
    serialnumbers = fields.Text(string=u'序列号信息')
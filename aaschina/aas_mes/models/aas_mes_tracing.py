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
    mainorder_name = fields.Char(string=u'主工单名称', index=True)
    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'子工单', ondelete='cascade', index=True)
    workorder_name = fields.Char(string=u'子工单', index=True)
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='restrict', index=True)
    workcenter_name = fields.Char(string=u'工序名称', index=True)
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict', index=True)
    workstation_name = fields.Char(string=u'工位名称', index=True)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'生产线', ondelete='restrict', index=True)
    mesline_name = fields.Char(string=u'生产线名称', index=True)
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次', ondelete='restrict')
    schedule_name = fields.Char(string=u'班次名称', copy=False)
    workdate = fields.Char(string=u'工作日', copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict', index=True)
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_code = fields.Char(string=u'产品编码', index=True)
    date_code = fields.Char(string='DateCode', index=True)
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'成品批次', ondelete='restrict', index=True)
    product_lot_name = fields.Char(string=u'成品批次名称', index=True)
    date_start = fields.Datetime(string=u'开始时间', copy=False)
    date_finish = fields.Datetime(string=u'结束时间', copy=False)
    materiallist = fields.Text(string=u'原料信息')
    equipmentlist = fields.Text(string=u'设备信息')
    employeelist = fields.Text(string=u'员工信息')
    serialnumbers = fields.Text(string=u'序列号信息')



    @api.model
    def create(self, vals):
        record = super(AASMESTracing, self).create(vals)
        record.action_after_create()
        return record

    @api.one
    def action_after_create(self):
        vals = {}
        if self.mainorder_id:
            vals['mainorder_name'] = self.mainorder_id.name
        if self.workorder_id:
            vals['workorder_name'] = self.workorder_id.name
        if self.workcenter_id:
            vals['workcenter_name'] = self.workcenter_id.name
        if self.workstation_id:
            vals['workstation_name'] = self.workstation_id.name
        if self.mesline_id:
            vals['mesline_name'] = self.mesline_id.name
            if self.mesline_id.workdate:
                vals['workdate'] = self.mesline_id.workdate
        if self.schedule_id:
            vals['schedule_name'] = self.schedule_id.name
        if self.product_id:
            vals.update({'product_uom': self.product_id.uom_id.id, 'product_code': self.product_id.default_code})
        if self.product_lot:
            vals['product_lot_name'] = self.product_lot.name
        if vals and len(vals) > 0:
            self.write(vals)


 # 追溯消耗明细
class StockMove(models.Model):
    _inherit = 'stock.move'

    trace_id = fields.Many2one(comodel_name='aas.mes.tracing', string=u'追溯', ondelete='restrict')
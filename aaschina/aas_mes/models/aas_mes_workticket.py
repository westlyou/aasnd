# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-9-22 15:07
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


# 工票

TICKETSTATES = [('draft', u'草稿'), ('waiting', u'等待'), ('producing', u'生产'), ('done', u'完成')]


class AASMESWorkticket(models.Model):
    _name = 'aas.mes.workticket'
    _description = 'AAS MES Workticket'
    _order = 'workorder_id desc,seqence'

    name = fields.Char(string=u'名称', required=True, copy=False)
    barcode = fields.Char(string=u'名称', compute="_compute_barcode", store=True)
    seqence = fields.Integer(string=u'序号')
    routing_id = fields.Many2one(comodel_name='aas.mes.routing', string=u'工艺', ondelete='restrict')
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    input_qty = fields.Float(string=u'投入数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    output_qty = fields.Float(string=u'产出数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    state = fields.Selection(selection=TICKETSTATES, string=u'状态', default='draft', copy=False)
    time_wait = fields.Datetime(string=u'等待时间', copy=False)
    time_start = fields.Datetime(string=u'开工时间', copy=False)
    time_finish = fields.Datetime(string=u'完工时间', copy=False)
    workcenter_name = fields.Char(string=u'工序名称')
    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'子工单', ondelete='cascade')
    workorder_name = fields.Char(string=u'子工单')
    mainorder_id = fields.Many2one(comodel_name='aas.mes.mainorder', string=u'主工单')
    mainorder_name = fields.Char(string=u'主工单')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'生产线', ondelete='restrict')
    mesline_name = fields.Char(string=u'生产线')



    @api.depends('name')
    def _compute_barcode(self):
        for record in self:
            record.barcode = 'AR'+record.name

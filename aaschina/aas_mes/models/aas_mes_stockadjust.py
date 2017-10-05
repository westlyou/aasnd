# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-9-30 14:27
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

# 线边库库存调整
class AASMESStockadjust(models.Model):
    _name = 'aas.mes.stockadjust'
    _description = 'AAS MES Stock Adjust'

    name = fields.Char(string=u'名称', required=True, copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    adjustbefore_qty = fields.Float(string=u'调整前数量', digits=dp.get_precision('Product Unit of Measure'),
                                    default=0.0, compute="_compute_adjustbefore_qty", store=True)
    adjustafter_qty = fields.Float(string=u'调整后数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    adjust_time = fields.Datetime(string=u'调整时间', default=fields.Datetime.now, copy=False)
    adjustuser_id = fields.Many2one(comodel_name='res.users', string=u'操作人', ondelete='restrict', default= lambda self: self.env.user)
    state = fields.Selection(selection=[('draft', u'草稿'), ('done', u'完成')], string=u'状态', default='draft', copy=False)

    @api.depends('location_id', 'workstation_id')
    def _compute_adjustbefore_qty(self):
        for record in self:
            record.adjustbefore_qty = self.get_stock_qty(record)


    @api.model
    def get_stock_qty(self, record):
        stock_qty = 0.0
        domain = [('product_id', '=', record.product_id.id), ('lot_id', '=', self.product_lot.id)]
        if record.location_id:
            domain.append(('location_id', '=', record.location_id.id))
        elif record.mesline_id:
            mesline = record.mesline_id
            if not mesline.location_production_id or not mesline.location_material_list or len(mesline.location_material_list) <= 0:
                raise UserError(u'请先设置好产线的原料和成品库位信息！')
            locationids = [mesline.location_production_id.id]
            for tlocation in mesline.location_material_list:
                locationids.append(tlocation.location_id.id)
            domain.append(('location_id', 'in', locationids))
        quants = self.env['stock.qunat'].search(domain)
        if quants and len(quants) > 0:
            stock_qty = sum([quant.qty for quant in quants])
        return stock_qty

    @api.one
    @api.constrains('location_id', 'adjustafter_qty')
    def action_check_adjustment(self):
        pass




    @api.one
    def action_done(self):
        pass



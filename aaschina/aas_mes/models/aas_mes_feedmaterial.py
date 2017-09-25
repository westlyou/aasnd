# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-9-23 21:04
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


# 上料
class AASMESFeedmaterial(models.Model):
    _name = 'aas.mes.feedmaterial'
    _description = 'AAS MES Feed Material'
    _rec_name = 'product_id'
    _order = 'feed_time desc'


    product_id = fields.Many2one(comodel_name='product.product', string=u'成品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'成品单位', ondelete='restrict')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料', ondelete='restrict')
    material_uom = fields.Many2one(comodel_name='product.uom', string=u'原料单位', ondelete='restrict')
    material_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'原料批次', ondelete='restrict')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'生产线', ondelete='restrict')
    material_qty = fields.Float(string=u'现场库存', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    feed_time = fields.Datetime(string=u'上料时间', default=fields.Datetime.now, copy=False)
    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')



    @api.model
    def get_material_qty(self, record):
        material_qty = 0.0
        domain = [('product_id', '=', record.material_id.id), ('lot_id', '=', record.material_lot.id)]
        location_id = record.mesline_id.location_id
        domain.append(('location_id', 'child_of', location_id.id))
        quants = self.env['stock.quant'].search(domain)
        if quants and len(quants) > 0:
            material_qty = sum([quant.qty for quant in quants])
        record.write({'material_qty': material_qty})
        return material_qty


    @api.one
    def action_refresh_stock(self):
        self.get_material_qty(self)


    @api.model
    def create(self, vals):
        record = super(AASMESFeedmaterial, self).create(vals)
        record.action_refresh_stock()
        return record

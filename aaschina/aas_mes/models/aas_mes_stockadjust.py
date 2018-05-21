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
    _order = 'id desc'

    name = fields.Char(string=u'名称', required=True, copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    product_qty = fields.Float(string=u'调整数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    state = fields.Selection(selection=[('draft', u'草稿'), ('done', u'完成')], string=u'状态', default='draft', copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    srclocation_id = fields.Many2one(comodel_name='stock.location', string=u'源库位')
    srclocation_beforeqty = fields.Float(string=u'调整前源库位库存', digits=dp.get_precision('Product Unit of Measure'),
                                   compute='_compute_srclocation_beforeqty', store=True)
    srclocation_afterqty = fields.Float(string=u'调整后源库位库存', digits=dp.get_precision('Product Unit of Measure'),
                                   default=0.0)
    destlocation_id = fields.Many2one(comodel_name='stock.location', string=u'目标库位')
    destlocation_beforeqty = fields.Float(string=u'调整前目标库位库存', digits=dp.get_precision('Product Unit of Measure'),
                                    compute='_compute_destlocation_beforeqty', store=True)
    destlocation_afterqty = fields.Float(string=u'调整后目标库位库存', digits=dp.get_precision('Product Unit of Measure'),
                                    default=0.0)

    adjust_time = fields.Datetime(string=u'调整时间', default=fields.Datetime.now, copy=False)
    adjustuser_id = fields.Many2one('res.users', string=u'操作人', ondelete='restrict', default= lambda self: self.env.user)


    @api.depends('product_id', 'product_lot', 'srclocation_id')
    def _compute_srclocation_beforeqty(self):
        for record in self:
            if not record.product_id or not record.product_lot or not record.srclocation_id:
                record.srclocation_beforeqty = 0.0
            else:
                record.srclocation_beforeqty = self.get_stock_qty(record.product_id.id,
                                                                  record.product_lot.id, record.srclocation_id.id)


    @api.depends('product_id', 'product_lot', 'destlocation_id')
    def _compute_destlocation_beforeqty(self):
        for record in self:
            if not record.product_id or not record.product_lot or not record.destlocation_id:
                record.destlocation_beforeqty = 0.0
            else:
                record.destlocation_beforeqty = self.get_stock_qty(record.product_id.id,
                                                                   record.product_lot.id, record.destlocation_id.id)


    @api.model
    def get_stock_qty(self, productid, productlotid, srclocationid):
        stock_qty = 0.0
        domain = [('product_id', '=', productid), ('lot_id', '=', productlotid), ('location_id', '=', srclocationid)]
        quants = self.env['stock.quant'].search(domain)
        if quants and len(quants) > 0:
            stock_qty = sum([quant.qty for quant in quants])
        return stock_qty




    @api.model
    def create(self, vals):
        record = super(AASMESStockadjust, self).create(vals)
        record.write({'product_uom': record.product_id.uom_id.id})
        if not record.srclocation_id and not record.destlocation_id:
            raise UserError('源库位和目标库位必须要设置一个！')
        return record


    @api.one
    def action_done(self):
        if not self.srclocation_id and not self.destlocation_id:
            raise UserError('源库位和目标库位必须要设置一个！')
        if float_compare(self.product_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise UserError(u'调整数量必须是一个大于零的数！')
        if self.srclocation_id and float_compare(self.product_qty, self.srclocation_beforeqty, precision_rounding=0.000001) > 0.0:
            raise UserError(u'调整数量不可以大于源库位的库存数量！')
        location_inventory = self.env.ref('stock.location_inventory')
        movevals = {
            'name': self.name, 'product_id': self.product_id.id, 'product_uom': self.product_uom.id,
            'create_date': fields.Datetime.now(), 'restrict_lot_id': self.product_lot.id,
            'product_uom_qty': self.product_qty, 'company_id': self.env.user.company_id.id
        }
        adjustvals = {}
        if self.srclocation_id:
            adjustvals['srclocation_afterqty'] = self.srclocation_beforeqty - self.product_qty
            movevals['location_id'] = self.srclocation_id.id
        else:
            movevals['location_id'] = location_inventory.id
        if self.destlocation_id:
            adjustvals['destlocation_afterqty'] = self.destlocation_beforeqty + self.product_qty
            movevals['location_dest_id'] = self.destlocation_id.id
        else:
            movevals['location_dest_id'] = location_inventory.id
        if adjustvals and len(adjustvals) > 0:
            self.write(adjustvals)
        tempmove = self.env['stock.move'].create(movevals)
        tempmove.action_done()
        self.write({'state': 'done'})
        # 刷新上料信息
        feeddomain = [('material_id', '=', self.product_id.id), ('material_lot', '=', self.product_lot.id)]
        feedmateriallist = self.env['aas.mes.feedmaterial'].search(feeddomain)
        if feedmateriallist and len(feedmateriallist) > 0:
            for feedmaterial in feedmateriallist:
                feedmaterial.action_refresh_stock()


    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(u'调整记录已经执行，不可以删除！')
        return super(AASMESStockadjust, self).unlink()






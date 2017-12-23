# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-12-7 22:27
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class AASStockAdjust(models.Model):
    _name = 'aas.stock.adjust'
    _description = 'AAS Stock Adjust'

    name = fields.Char(string=u'名称', required=True, copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')
    adjustbefore_qty = fields.Float(string=u'调整前数量', digits=dp.get_precision('Product Unit of Measure'),
                                    compute="_compute_adjustbefore_qty", store=True)
    adjustafter_qty = fields.Float(string=u'调整后数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    adjust_time = fields.Datetime(string=u'调整时间', default=fields.Datetime.now, copy=False)
    adjustuser_id = fields.Many2one(comodel_name='res.users', string=u'操作人', ondelete='restrict', default= lambda self: self.env.user)
    state = fields.Selection(selection=[('draft', u'草稿'), ('done', u'完成')], string=u'状态', default='draft', copy=False)


    @api.depends('location_id')
    def _compute_adjustbefore_qty(self):
        for record in self:
            record.adjustbefore_qty = self.get_stock_qty(record)


    @api.model
    def get_stock_qty(self, record):
        stock_qty = 0.0
        if (not record.location_id) or (not record.product_id) or (not record.product_lot):
            return stock_qty
        domain = [('product_id', '=', record.product_id.id), ('lot_id', '=', record.product_lot.id)]
        domain.append(('location_id', 'child_of', record.location_id.id))
        quants = self.env['stock.quant'].search(domain)
        if quants and len(quants) > 0:
            stock_qty = sum([quant.qty for quant in quants])
        return stock_qty

    @api.model
    def create(self, vals):
        record = super(AASStockAdjust, self).create(vals)
        record.write({'product_uom': record.product_id.uom_id.id})
        return record


    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(u'调整记录已经执行，不可以删除！')
        return super(AASStockAdjust, self).unlink()


    @api.one
    def action_done(self):
        stock_qty = self.get_stock_qty(self)
        if float_compare(stock_qty, self.adjustbefore_qty, precision_rounding=0.000001) != 0.0:
            self.write({'adjustbefore_qty': stock_qty})
        inventorylocationid, templocationid = self.env.ref('stock.location_inventory').id, self.location_id.id
        balance_qty = self.adjustafter_qty - self.adjustbefore_qty
        if float_is_zero(balance_qty, precision_rounding=0.000001):
            raise UserError(u'调整前和调整后的数量不可以相同！')
        movevals = {
            'name': self.name, 'product_id': self.product_id.id, 'product_uom': self.product_uom.id,
            'create_date': fields.Datetime.now(), 'restrict_lot_id': self.product_lot.id,
            'product_uom_qty': abs(balance_qty), 'company_id': self.env.user.company_id.id
        }
        if float_compare(balance_qty, 0.0, precision_rounding=0.000001) > 0.0:
            movevals.update({'location_id': inventorylocationid, 'location_dest_id': templocationid})
        if float_compare(balance_qty, 0.0, precision_rounding=0.0000001) < 0.0:
            movevals.update({'location_id': templocationid, 'location_dest_id': inventorylocationid})
        tempmove = self.env['stock.move'].create(movevals)
        tempmove.action_done()
        self.write({'state': 'done'})
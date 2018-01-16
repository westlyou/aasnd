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
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')
    adjustbefore_qty = fields.Float(string=u'调整前数量', digits=dp.get_precision('Product Unit of Measure'),
                                    default=0.0, compute="_compute_adjustbefore_qty", store=True)
    adjustafter_qty = fields.Float(string=u'调整后数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    adjust_time = fields.Datetime(string=u'调整时间', default=fields.Datetime.now, copy=False)
    adjustuser_id = fields.Many2one(comodel_name='res.users', string=u'操作人', ondelete='restrict', default= lambda self: self.env.user)
    state = fields.Selection(selection=[('draft', u'草稿'), ('done', u'完成')], string=u'状态', default='draft', copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', default=lambda self: self.env.user.company_id)

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
        domain.append(('location_id', '=', record.location_id.id))
        quants = self.env['stock.quant'].search(domain)
        if quants and len(quants) > 0:
            stock_qty = sum([quant.qty for quant in quants])
        return stock_qty


    @api.one
    @api.constrains('location_id', 'adjustafter_qty')
    def action_check_adjustment(self):
        if self.adjustafter_qty:
            if float_compare(self.adjustafter_qty, 0.0, precision_rounding=0.000001) < 0.0:
                raise ValidationError(u'调整后的数量必须是大于等于零的数！')
            if float_is_zero(self.adjustafter_qty - self.adjustbefore_qty, precision_rounding=0.000001):
                raise ValidationError(u'调整后的数量不可以和调整前的数量相同！')
        if self.location_id:
            location_flag = False
            templeft, tempright = self.location_id.parent_left, self.location_id.parent_right
            plocation = self.mesline_id.location_production_id
            if templeft <= plocation.parent_left and tempright >= plocation.parent_right:
                location_flag = True
            for materiallocation in self.mesline_id.location_material_list:
                if location_flag:
                    break
                mlocation = materiallocation.location_id
                if templeft <= mlocation.parent_left and tempright >= mlocation.parent_right:
                    location_flag = True
            if not location_flag:
                raise ValidationError(u'您选择的库位异常，并非是的产线%s的成品和原料库位！'% self.mesline_id.name)

    @api.model
    def create(self, vals):
        record = super(AASMESStockadjust, self).create(vals)
        record.write({'product_uom': record.product_id.uom_id.id})
        return record


    @api.one
    def action_done(self):
        stock_qty = self.get_stock_qty(self)
        if float_compare(stock_qty, self.adjustbefore_qty, precision_rounding=0.000001) != 0.0:
            self.write({'adjustbefore_qty': stock_qty})
        location_inventory = self.env.ref('stock.location_inventory')
        location_mesline = self.location_id
        if not location_mesline:
            materiallocation = self.mesline_id.location_material_list[0]
            location_mesline = materiallocation.location_id
        balance_qty = self.adjustafter_qty - self.adjustbefore_qty
        movevals = {
            'name': self.name, 'product_id': self.product_id.id, 'product_uom': self.product_uom.id,
            'create_date': fields.Datetime.now(), 'restrict_lot_id': self.product_lot.id,
            'product_uom_qty': abs(balance_qty), 'company_id': self.env.user.company_id.id
        }
        if float_compare(balance_qty, 0.0, precision_rounding=0.000001) > 0.0:
            movevals.update({'location_id': location_inventory.id, 'location_dest_id': location_mesline.id})
        if float_compare(balance_qty, 0.0, precision_rounding=0.0000001) < 0.0:
            movevals.update({'location_id': location_mesline.id, 'location_dest_id': location_inventory.id})
        if float_is_zero(balance_qty, precision_rounding=0.000001):
            raise UserError(u'调整前和调整后的数量不可以相同！')
        tempmove = self.env['stock.move'].create(movevals)
        tempmove.action_done()
        self.write({'state': 'done'})
        # 刷新上料信息
        feeddomain = [('material_id', '=', self.product_id.id), ('material_lot', '=', self.product_lot.id)]
        feeddomain.append(('mesline_id', '=', self.mesline_id.id))
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






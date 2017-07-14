# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-3 21:31
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


# 标签发货，通过标签清单直接生成发货单；采购退货使用
class AASStockDeliveryLabelWizard(models.TransientModel):
    _name = 'aas.stock.delivery.label.wizard'
    _description = u'标签发货向导'
    _transient_max_hours = 1

    delivery_id = fields.Many2one(comodel_name='aas.stock.delivery', string=u'发货单', ondelete='cascade')
    origin_order = fields.Char(string=u'来源单据')

    label_lines = fields.One2many(comodel_name='aas.stock.delivery.label.line.wizard', inverse_name='wizard_id', string=u'标签明细')

    @api.one
    def action_done(self):
        if not self.label_lines or len(self.label_lines) <= 0:
            raise UserError(u'请先添加标签明细')
        dlinedict, doperations = {}, []
        for lline in self.label_lines:
            if lline.operation_id:
                continue
            doperations.append((0, 0, {'label_id': lline.label_id.id}))
            dkey = 'P'+str(lline.product_id.id)
            if dkey not in dlinedict:
                dline = self.env['aas.stock.delivery.line'].search([('delivery_id', '=', self.delivery_id.id), ('product_id', '=', lline.product_id.id)], limit=1)
                if not dline:
                   dlinedict[dkey] = {
                       'product_id': lline.product_id.id, 'product_uom': lline.product_uom.id, 'product_lot': lline.product_lot.id,
                       'product_qty': 0.0, 'delivery_type': self.delivery_id.delivery_type
                   }
        if dlinedict and len(dlinedict) > 0:
            dlines = [(0, 0, dval) for dkey, dval in dlinedict.items()]
            self.delivery_id.write({'delivery_lines': dlines})
        if doperations and len(doperations) > 0:
            self.delivery_id.write({'operation_lines': doperations})



class AASStockDeliveryLabelLineWizard(models.TransientModel):
    _name = 'aas.stock.delivery.label.line.wizard'
    _description = u'标签发货明细向导'

    wizard_id = fields.Many2one(comodel_name='aas.stock.delivery.label.wizard', string=u'标签向导', ondelete='cascade')
    operation_id = fields.Many2one(comodel_name='aas.stock.delivery.operation', string=u'作业标签', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位',  ondelete='restrict')
    origin_order = fields.Char(string=u'来源单据')

    _sql_constraints = [
        ('uniq_label', 'unique (wizard_id, label_id)', u'请不要重复添加同一个标签！')
    ]


    @api.onchange('label_id')
    def action_change_label(self):
        label = self.label_id
        if label:
            self.product_id, self.product_uom, self.product_lot = label.product_id.id, label.product_uom.id, label.product_lot.id
            self.product_qty, self.location_id, self.origin_order = label.product_qty, label.location_id.id, label.origin_order
        else:
            self.product_id, self.product_uom, self.product_lot = False, False, False
            self.product_qty, self.location_id, self.origin_order = 0.0, False, ''

    @api.model
    def action_before_create(self, vals):
        label = self.env['aas.product.label'].browse(vals.get('label_id'))
        vals.update({
            'product_id': label.product_id.id, 'product_uom': label.product_uom.id, 'product_lot': label.product_lot.id,
            'product_qty': label.product_qty, 'location_id': label.location_id.id, 'origin_order': label.origin_order
        })


    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        record = super(AASStockDeliveryLabelLineWizard, self).create(vals)
        if not record.wizard_id.origin_order and record.origin_order:
            record.wizard_id.write({'origin_order': record.origin_order})
        elif record.wizard_id.origin_order and record.origin_order and record.wizard_id.origin_order!=record.origin_order:
            if record.wizard_id.delivery_id.delivery_type=='purchase':
                raise UserError(u'不同的采购订单标签不能同时退PO!')
            else:
                raise UserError(u'标签来源不同不可以混合发货！')
        return record

    @api.multi
    def unlink(self):
        operationlines = self.env['aas.stock.delivery.operation']
        for record in self:
            if record.operation_id:
                operationlines |= record.operation_id
        result = super(AASStockDeliveryLabelLineWizard, self).unlink()
        if operationlines and len(operationlines) > 0:
            operationlines.unlink()
        return result
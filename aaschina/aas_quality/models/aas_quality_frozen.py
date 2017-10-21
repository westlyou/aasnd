# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-10-21 17:18
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


# 冻结批次
class AASQualityFrozen(models.Model):
    _name = 'aas.quality.frozen'
    _description = 'AAS Quality Frozen'

    display_name = fields.Char(string=u'名称', compute='_compute_display_name', store=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    frozen_time = fields.Datetime(string=u'冻结时间', default=fields.Datetime.now, copy=False)
    state = fields.Selection(selection=[('draft', u'草稿'), ('done', u'完成'), ], string=u'状态', default='draft', copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'操作人员', ondelete='restrict', default=lambda self:self.env.user)

    @api.depends('product_id', 'product_lot')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.product_id.default_code+'['+record.product_lot.name+']'


    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(u'请仔细检查，已经完成的操作不可以删除！')
        return super(AASQualityFrozen, self).unlink()


    @api.one
    def action_done(self):
        if self.state == 'done':
            return False
        labeldomain = [('product_id', '=', self.product_id.id), ('product_lot', '=', self.product_lot.id)]
        labeldomain.append(('state', '=', 'normal'))
        labellist = self.env['aas.product.label'].search(labeldomain)
        if labellist and len(labellist) > 0:
            labellist.write({'state': 'frozen'})
        self.write({'state': 'done', 'frozen_time': fields.Datetime.now()})


# 解冻批次
class AASQualityThaw(models.Model):
    _name = 'aas.quality.thaw'
    _description = 'AAS Quality Thaw'

    display_name = fields.Char(string=u'名称', compute='_compute_display_name', store=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    thaw_time = fields.Datetime(string=u'解冻时间', default=fields.Datetime.now, copy=False)
    state = fields.Selection(selection=[('draft', u'草稿'), ('done', u'完成'), ], string=u'状态', default='draft', copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'操作人员', ondelete='restrict', default=lambda self:self.env.user)


    @api.depends('product_id', 'product_lot')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.product_id.default_code+'['+record.product_lot.name+']'

    @api.one
    def action_done(self):
        if self.state == 'done':
            return False
        labeldomain = [('product_id', '=', self.product_id.id), ('product_lot', '=', self.product_lot.id)]
        labeldomain.append(('state', '=', 'frozen'))
        labellist = self.env['aas.product.label'].search(labeldomain)
        if labellist and len(labellist) > 0:
            labellist.write({'state': 'normal'})
        self.write({'state': 'done', 'thaw_time': fields.Datetime.now()})

    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(u'请仔细检查，已经完成的操作不可以删除！')
        return super(AASQualityThaw, self).unlink()
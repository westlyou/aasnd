# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-13 09:40
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class AASProductLabelSplitWizard(models.TransientModel):
    _name = 'aas.product.label.split.wizard'
    _description = 'AAS Product Label Split Wizard'

    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'))
    label_qty = fields.Float(string=u'每标签数量', digits=dp.get_precision('Product Unit of Measure'))
    label_count = fields.Integer(string=u'标签数量')


    @api.one
    def action_done(self):
        if float_compare(self.label_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise UserError(u'每标签数量必须是一个正数！')
        if self.label_count and self.label_count < 0:
            raise UserError(u'标签数量必须是一个正整数！')
        if float_compare(self.label_qty, self.product_qty, precision_rounding=0.000001) >= 0.0:
            raise UserError(u'每标签的数量不能大于等于标签总数量！')
        self.label_id.action_dosplit(self.label_qty, self.label_count)




class AASProductLabelMergeWizard(models.TransientModel):
    _name = 'aas.product.label.merge.wizard'
    _description = 'AAS Product Label Merge Wizard'

    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')
    merge_lines = fields.One2many(comodel_name='aas.product.label.merge.line.wizard', inverse_name='merge_id', string=u'合并明细')

    @api.onchange('product_id')
    def action_change_product_id(self):
        self.product_uom = self.product_id.uom_id.id

    @api.model
    def create(self, vals):
        product = self.env['product.product'].browse(vals.get('product_id'))
        vals['product_uom'] = product.uom_id.id
        return super(AASProductLabelMergeWizard, self).create(vals)


    @api.multi
    def action_done(self):
        self.ensure_one()
        if not self.merge_lines or len(self.merge_lines) <= 0:
            raise UserError(u'请先添加需要合并的标签！')
        if not self.location_id:
            raise UserError(u'请先设置好新标签库位！')
        labels = [mline.label_id for mline in self.merge_lines]
        templabel = self.env['aas.product.label'].action_merge_labels(labels, self.location_id)
        view_form = self.env.ref('aas_wms.view_form_aas_product_label')
        return {
            'name': u"产品标签",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.product.label',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'self',
            'res_id': templabel.id,
            'context': self.env.context
        }




class AASProductLabelMergeLineWizard(models.TransientModel):
    _name = 'aas.product.label.merge.line.wizard'
    _description = 'AAS Product Label Merge Line Wizard'

    merge_id = fields.Many2one(comodel_name='aas.product.label.merge.wizard', string=u'合并', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'))
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')


    @api.onchange('label_id')
    def action_change_label(self):
        label = self.label_id
        if label:
            self.product_id, self.product_qty = label.product_id.id, label.product_qty
            self.product_lot, self.location_id = label.product_lot.id, label.location_id.id
        else:
            self.product_id, self.product_qty = False, 0.0
            self.product_lot, self.location_id = False, False

    @api.model
    def action_before_create(self, vals):
        label = self.env['aas.product.label'].browse(vals.get('label_id'))
        vals.update({
            'product_id': label.product_id.id, 'product_lot': label.product_lot.id,
            'product_qty': label.product_qty, 'location_id': label.location_id.id
        })

    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        return super(AASProductLabelMergeLineWizard, self).create(vals)

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
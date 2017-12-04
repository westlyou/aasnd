# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-7 16:13
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


# 多收货单批量报检
class AASMultiReceiptQualityWizard(models.TransientModel):
    _name = 'aas.multi.receipt.quality.wizard'
    _description = 'AAS Multi Receipt Quality Wizard'

    partner_id = fields.Many2one(comodel_name='res.partner', string=u'业务伙伴', ondelete='cascade')
    receipt_lines = fields.One2many(comodel_name='aas.multi.receipt.quality.line.wizard', inverse_name='wizard_id', string=u'收货明细')

    @api.one
    def action_done(self):
        if not self.receipt_lines or len(self.receipt_lines) <= 0:
            raise UserError(u'请先添加待报检的采购收货单！')
        receipts = self.env['aas.stock.receipt']
        for rline in self.receipt_lines:
            receipts |= rline.receipt_id
        receipts.action_commit_checking()



class AASMultiReceiptQualityLineWizard(models.TransientModel):
    _name = 'aas.multi.receipt.quality.line.wizard'
    _description = 'AAS Multi Receipt Quality Line Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.multi.receipt.quality.wizard', string=u'向导', ondelete='cascade')
    receipt_id = fields.Many2one(comodel_name='aas.stock.receipt', string=u'收货单')
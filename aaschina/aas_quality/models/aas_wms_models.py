# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-6 12:05
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

CHECK_STATE = [('draft', u'草稿'), ('tocheck', u'待检'), ('checking', u'检测中'), ('done', u'完成'), ('cancel', u'取消')]


class AASStockReceiptLine(models.Model):
    _inherit = 'aas.stock.receipt.line'

    quality_id = fields.Many2one(comodel_name='aas.quality.order', string=u'质检单', ondelete='set null')
    quality_state = fields.Selection(selection=CHECK_STATE, string=u'质检状态', related='quality_id.state', store=True)


class AASStockReceiptLabel(models.Model):
    _inherit = 'aas.stock.receipt.label'

    qualified_qty = fields.Float(string=u'合格数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    concession_qty = fields.Float(string=u'让步数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    unqualified_qty = fields.Float(string=u'不合格数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)


class AASQualityOrder(models.Model):
    _inherit = 'aas.quality.order'

    @api.one
    def action_quality_done(self):
        super(AASQualityOrder, self).action_quality_done()
        # 更新报检收货单信息
        receiptdict = {}
        for qoperation in self.operation_lines:
            if not qoperation.commit_id or not qoperation.commit_model or qoperation.commit_model != 'aas.stock.receipt.line':
                continue
            rkey, lkey = 'R'+str(qoperation.commit_id), 'L'+str(qoperation.qlabel_id.label_id.id)
            if rkey in receiptdict:
                receiptdict[rkey][lkey] = {
                    'qualified_qty': qoperation.qualified_qty, 'concession_qty': qoperation.concession_qty, 'unqualified_qty': qoperation.unqualified_qty
                }
            else:
                receiptdict[rkey] = {
                    lkey: {'qualified_qty': qoperation.qualified_qty, 'concession_qty': qoperation.concession_qty, 'unqualified_qty': qoperation.unqualified_qty}
                }
        if self.rejection_lines and len(self.rejection_lines) > 0:
            for qrejection in self.rejection_lines:
                if not qrejection.current_label:
                    continue
                if not qrejection.commit_id or not qrejection.commit_model or qrejection.commit_model != 'aas.stock.receipt.line':
                    continue
                templabel = qrejection.label_id
                rkey, lkey = 'R'+str(qrejection.commit_id), 'L'+str(templabel.id)
                if rkey in receiptdict:
                    receiptdict[rkey][lkey] = {
                        'label_id': templabel.id, 'product_id': templabel.product_id.id, 'product_uom': templabel.product_uom.id,
                        'product_qty': 0.0, 'product_lot': templabel.product_lot.id, 'label_location': templabel.location_id.id,
                        'origin_order': templabel.origin_order, 'unqualified_qty': templabel.product_qty
                    }
                else:
                    receiptdict[rkey] = {
                        lkey: {
                            'label_id': templabel.id, 'product_id': templabel.product_id.id, 'product_uom': templabel.product_uom.id,
                            'product_qty': 0.0, 'product_lot': templabel.product_lot.id, 'label_location': templabel.location_id.id,
                            'origin_order': templabel.origin_order, 'unqualified_qty': templabel.product_qty
                        }
                    }
        if not receiptdict and len(receiptdict) <= 0:
            return
        receiptlines = self.env['aas.stock.receipt.line'].search([('quality_id', '=', self.id)])
        if not receiptlines or len(receiptlines) <= 0:
            return
        for rline in receiptlines:
            rkey = 'R'+str(rline.id)
            if rkey not in receiptdict:
                continue
            rlinedict, templabels = receiptdict[rkey], []
            for llabel in rline.label_list:
                lkey = 'L'+str(llabel.label_id.id)
                if lkey not in rlinedict:
                    continue
                templabels.append((1, llabel.id, rlinedict[lkey]))
                del rlinedict[lkey]
            if rlinedict and len(rlinedict) > 0:
                for tkey, tval in rlinedict:
                    tval.update({'receipt_id': rline.receipt_id.id})
                    templabels.append((0, 0, tval))
            rline.write({'label_list': templabels})




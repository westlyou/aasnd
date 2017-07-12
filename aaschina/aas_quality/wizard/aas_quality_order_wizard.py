# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-6 18:44
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import math
import logging

_logger = logging.getLogger(__name__)


class AASQualityRejectionWizard(models.TransientModel):
    _name = 'aas.quality.rejection.wizard'
    _description = 'AAS Quality Rejection Wizard'

    quality_id = fields.Many2one(comodel_name='aas.quality.order', string=u'质检单', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'业务伙伴', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    plot_lines = fields.One2many(comodel_name='aas.quality.rejection.lot.wizard', inverse_name='wizard_id', string=u'批次明细')
    label_lines = fields.One2many(comodel_name='aas.quality.rejection.label.wizard', inverse_name='wizard_id', string=u'标签明细')

    @api.one
    def action_check_lots(self):
        if not self.plot_lines or len(self.plot_lines) <= 0:
            raise UserError(u'您还没有添加批次拆分明细！')
        for plot in self.plot_lines:
            if float_compare(plot.label_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                raise UserError(u'批次%s拆分标签每标签的数量不能小于零'% plot.product_lot.name)
            if float_compare(plot.label_qty, plot.product_qty, precision_rounding=0.000001) > 0.0:
                raise UserError(u'批次%s拆分标签每标签的数量不能大于批次总数'% plot.product_lot.name)

    @api.multi
    def action_split_lots(self):
        """
        批次拆分
        :return:
        """
        self.ensure_one()
        self.action_check_lots()
        label_lines = []
        for plot in self.plot_lines:
            tproduct_qty, tlabel_qty = plot.product_qty, plot.label_qty
            for tindex in range(int(math.ceil(plot.product_qty / plot.label_qty))):
                if float_compare(tproduct_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                    break
                if float_compare(tproduct_qty, plot.label_qty, precision_rounding=0.000001) < 0.0:
                    tlabel_qty = tproduct_qty
                label_lines.append((0, 0, {
                    'product_lot': plot.product_lot.id, 'label_qty': tlabel_qty, 'origin_order': plot.origin_order,
                    'commit_id': plot.commit_id, 'commit_model': plot.commit_model, 'commit_order': plot.commit_order
                }))
                tproduct_qty -= tlabel_qty
        self.write({'label_lines': label_lines})
        view_form = self.env.ref('aas_quality.view_form_aas_quality_rejection_labels_wizard')
        return {
            'name': u"不合格品标签",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.quality.rejection.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context
        }

    @api.one
    def action_done(self):
        rejection_lines = []
        templocation = self.env['stock.warehouse'].get_default_warehouse().wh_input_stock_loc_id
        for tline in self.label_lines:
            tempvals = {'product_id': self.product_id.id, 'product_uom': self.product_uom.id, 'partner_id': self.partner_id and self.partner_id.id}
            tempvals.update({
                'location_id': templocation.id, 'product_lot': tline.product_lot.id, 'product_qty': tline.label_qty,
                'origin_order': tline.origin_order, 'locked': True, 'locked_order': tline.commit_order, 'stocked': True,
                'state': 'normal', 'qualified': False
            })
            templabel = self.env['aas.product.label'].create(tempvals)
            rejection_lines.append((0, 0, {
                'label_id': templabel.id, 'product_id': tempvals['product_id'], 'product_uom': tempvals['product_uom'],
                'product_lot': tempvals['product_lot'], 'product_qty': tempvals['product_qty'], 'origin_order': tempvals['origin_order'],
                'current_label': True, 'commit_id': tline.commit_id, 'commit_model': tline.commit_model, 'commit_order': tline.commit_order
            }))
        self.quality_id.write({'rejection_lines': rejection_lines})




class AASQualityRejectionLotWizard(models.TransientModel):
    _name = 'aas.quality.rejection.lot.wizard'
    _description = 'AAS Quality Rejection Lot Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.quality.rejection.wizard', string=u'向导', ondelete='cascade')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    product_qty = fields.Float(string=u'批次数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    label_qty = fields.Float(string=u'每包数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    origin_order = fields.Char(string=u'来源单据', copy=False)
    commit_id = fields.Integer(string=u'报检单据ID')
    commit_model = fields.Char(string=u'报检单据Model')
    commit_order = fields.Char(string=u'报检单据名称')



class AASQualityRejectionLabelWizard(models.TransientModel):
    _name = 'aas.quality.rejection.label.wizard'
    _description = 'AAS Quality Rejection Label Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.quality.rejection.wizard', string=u'向导', ondelete='cascade')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    label_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    origin_order = fields.Char(string=u'来源单据', copy=False)
    commit_id = fields.Integer(string=u'报检单据ID')
    commit_model = fields.Char(string=u'报检单据Model')
    commit_order = fields.Char(string=u'报检单据名称')

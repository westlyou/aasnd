# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import math
import logging
_logger = logging.getLogger(__name__)


class AASStockReceiptProductWizard(models.TransientModel):
    _name = "aas.stock.receipt.product.wizard"
    _description = u"收货明细产品向导"

    receipt_locked = fields.Boolean(string=u'锁定', default=False)
    receipt_line_id = fields.Many2one(comodel_name='aas.stock.receipt.line', string=u'收货明细', ondelete='cascade')
    receipt_product_id = fields.Many2one(comodel_name='product.product', string=u'产品')
    receipt_product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位')
    receipt_product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'))
    receipt_need_warranty = fields.Boolean(string=u'质保期', default=False)
    split_qty = fields.Float(string=u'拆分数量', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_lot_split')
    balance_qty = fields.Float(string=u'剩余数量', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_lot_split')
    wizard_lot_lines = fields.One2many(comodel_name='aas.stock.receipt.product.lot.wizard', inverse_name='product_wizard_id', string=u'批次明细')
    wizard_label_lines = fields.One2many(comodel_name='aas.stock.receipt.product.label.wizard', inverse_name='product_wizard_id', string=u'标签明细')


    @api.one
    def action_check_lots(self):
        if not self.wizard_lot_lines or len(self.wizard_lot_lines) <= 0:
            raise UserError(u'请先添加批次明细！')
        total_lot_qty = 0.0
        for lline in self.wizard_lot_lines:
            if self.receipt_need_warranty and not lline.receipt_warranty_date:
                raise UserError(u'批次%s未添加质保日期'% lline.product_lot_name)
            total_lot_qty += lline.product_lot_qty
        if float_compare(self.receipt_product_qty, total_lot_qty, precision_rounding=0.000001) != 0.0:
            raise UserError(u'拆分的批次总数必须和收货数量相同！')


    @api.depends('wizard_lot_lines.product_lot_qty', 'wizard_label_lines.product_label_qty')
    def _compute_lot_split(self):
        for record in self:
            record.split_qty, record.balance_qty = 0.0, record.receipt_product_qty
            if record.wizard_label_lines and len(record.wizard_label_lines) > 0:
                record.split_qty = sum([lline.product_label_qty for lline in record.wizard_label_lines])
                record.balance_qty = record.receipt_product_qty - record.split_qty
            elif record.wizard_lot_lines and len(record.wizard_lot_lines) > 0:
                record.split_qty = sum([lline.product_lot_qty for lline in self.wizard_lot_lines])
                record.balance_qty = record.receipt_product_qty - record.split_qty



    @api.multi
    def action_lot_lines_split(self):
        self.ensure_one()
        self.action_check_lots()
        for lline in self.wizard_lot_lines:
            lline.action_split_lot()
        view_form = self.env.ref('aas_wms.view_form_aas_stock_receipt_product_label_wizard')
        return {
            'name': u"标签清单",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.stock.receipt.product.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context
        }

    @api.one
    def action_check_labels(self):
        if not self.wizard_label_lines or len(self.wizard_label_lines) <= 0:
            raise UserError(u'请先添加标签明细！')
        total_label_qty = 0.0
        for lline in self.wizard_label_lines:
            if self.receipt_need_warranty and not lline.receipt_warranty_date:
                raise UserError(u'请仔细检查有标签未添加质保日期')
            total_label_qty += lline.product_label_qty
        if float_compare(self.receipt_product_qty, total_label_qty, precision_rounding=0.000001) != 0.0:
            raise UserError(u'拆分的标签总数必须和收货数量相同！')

    @api.model
    def get_product_lot(self, product_id, lot_name):
        product_lot = self.env['stock.production.lot'].search([('product_id', '=', product_id.id), ('name', '=', lot_name)], limit=1)
        if not product_lot:
            product_lot = self.env['stock.production.lot'].create({
                'product_id': product_id.id, 'name': lot_name, 'product_uom_id': product_id.uom_id.id, 'create_date': fields.Datetime.now()
            })
        return product_lot

    @api.multi
    def action_done_labels(self):
        self.ensure_one()
        self.action_check_labels()
        lotdict, receipt, product_id = {}, self.receipt_line_id.receipt_id, self.receipt_product_id
        if receipt.receipt_type=='purchase':
            location_id = self.env.ref('stock.stock_location_suppliers').id
        elif receipt.receipt_type=='sundry':
            location_id = self.env.ref('aas_wms.stock_location_sundry').id
        else:
            location_id = self.env['stock.warehouse'].get_default_warehouse().lot_stock_id.id
        receipt_labels = []
        for lline in self.wizard_label_lines:
            if lline.product_lot_name in lotdict:
                lot_id = lotdict[lline.product_lot_name]
            else:
                lot_id = self.get_product_lot(product_id.id, lline.product_lot_name).id
                lotdict[lline.product_lot_name] = lot_id
            label = self.action_build_label(lot_id, lline.product_label_qty, location_id, lline.receipt_warranty_date)
            receipt_labels.append((0, 0, {
                'line_id': self.receipt_line_id.id, 'label_id': label.id, 'product_id': label.product_id.id, 'product_uom': label.product_uom.id,
                'origin_order': label.origin_order, 'product_lot': lot_id, 'label_location': location_id, 'product_qty': label.product_qty
            }))
        receipt.write({'label_lines': receipt_labels, 'receipt_lines': [(1, self.receipt_line_id.id, {'label_related': True})]})


    @api.one
    def action_build_label(self, lot_id, lot_qty, location_id, warranty_date):
        receipt, receiptline = self.receipt_line_id.receipt_id, self.receipt_line_id
        labelvals = {'product_id': self.receipt_product_id.id, 'product_uom': self.receipt_product_id.uom_id.id}
        labelvals.update({'location_id': location_id, 'product_qty': lot_qty, 'product_lot': lot_id, 'state': 'draft'})
        labelvals.update({'company_id': self.env.user.company_id.id, 'origin_order': receiptline.origin_order or ""})
        labelvals.update({'locked': True, 'locked_order': receipt.name, 'partner_id': receipt.partner_id and receipt.partner_id.id})
        labelvals.update({'warranty_date': warranty_date or False})
        return self.env['aas.product.label'].create(labelvals)







class AASStockReceiptProductLotWizard(models.TransientModel):
    _name = "aas.stock.receipt.product.lot.wizard"
    _description = u"收货明细产品批次向导"
    _rec_name = "product_lot_name"

    product_wizard_id = fields.Many2one(comodel_name='aas.stock.receipt.product.wizard', string=u'收货明细产品向导', ondelete='cascade')
    product_lot_name = fields.Char(string=u"批次名称", required=True)
    product_lot_qty = fields.Float(string=u'批次数量', digits=dp.get_precision('Product Unit of Measure'), required=True)
    receipt_label_qty = fields.Float(string=u'每包装数量', digits=dp.get_precision('Product Unit of Measure'), required=True)
    receipt_warranty_date = fields.Date(string=u'质保日期')


    @api.one
    @api.constrains('product_lot_qty', 'receipt_label_qty')
    def _check_lot_qty(self):
        if self.product_lot_qty and float_compare(self.product_lot_qty, 0.0, precision_rounding=0.000001) < 0.0:
            raise ValidationError(u"批次%s数量设置无效，必须是一个正数！"% self.product_lot_name)
        if float_is_zero(self.product_lot_qty, precision_rounding=0.000001):
            raise ValidationError(u"批次%s数量设置无效，必须是一个正数！"% self.product_lot_name)
        if self.receipt_label_qty and float_compare(self.receipt_label_qty, 0.0, precision_rounding=0.000001) < 0.0:
            raise ValidationError(u"批次%s每包装数量设置无效，必须是一个正数！"% self.product_lot_name)
        if float_is_zero(self.receipt_label_qty, precision_rounding=0.000001):
            raise ValidationError(u"批次%s每包装数量设置无效，必须是一个大于零的正数！"% self.product_lot_name)
        if float_compare(self.receipt_label_qty, self.product_lot_qty, precision_rounding=0.000001) > 0.0:
            raise ValidationError(u"批次%s每包装数量设置无效，不能超过批次的总数量！"% self.product_lot_name)



    @api.one
    def action_split_lot(self):
        temp_qty, label_lines = self.product_lot_qty, []
        label_count = int(math.ceil(self.product_lot_qty / self.receipt_label_qty))
        for i in range(0, label_count):
            if float_is_zero(temp_qty, precision_rounding=0.000001):
                break
            labelvals = {'product_lot_name': self.product_lot_name, 'receipt_warranty_date': self.receipt_warranty_date}
            if float_compare(temp_qty, self.receipt_label_qty, precision_rounding=0.000001) >= 0.0:
                labelvals['product_label_qty'] = self.receipt_label_qty
                temp_qty -= self.receipt_label_qty
            else:
                labelvals['product_label_qty'] = temp_qty
                temp_qty = 0.0
            label_lines.append((0, 0, labelvals))
        self.product_wizard_id.write({'wizard_label_lines': label_lines})







class AASStockReceiptProductLabelWizard(models.TransientModel):
    _name = "aas.stock.receipt.product.label.wizard"
    _description = u"收货明细产品标签向导"

    product_wizard_id = fields.Many2one(comodel_name='aas.stock.receipt.product.wizard', string=u'收货明细产品向导', ondelete='cascade')
    product_lot_name = fields.Char(string=u"批次名称", required=True)
    product_label_qty = fields.Float(string=u'标签数量', digits=dp.get_precision('Product Unit of Measure'), required=True)
    receipt_warranty_date = fields.Date(string=u'质保日期')
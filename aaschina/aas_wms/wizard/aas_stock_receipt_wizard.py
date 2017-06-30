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

    receipt_id = fields.Many2one(comodel_name='aas.stock.receipt', string=u'收货单', ondelete='cascade')
    line_id = fields.Many2one(comodel_name='aas.stock.receipt.line', string=u'收货明细', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    need_warranty = fields.Boolean(string=u'质保期', default=False)
    receipt_locked = fields.Boolean(string=u'锁定', default=False)
    origin_order = fields.Char(string=u'来源单据')
    split_qty = fields.Float(string=u'拆分数量', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_lot_split')
    balance_qty = fields.Float(string=u'剩余数量', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_lot_split')
    lot_lines = fields.One2many(comodel_name='aas.stock.receipt.product.lot.wizard', inverse_name='wizard_id', string=u'批次明细')
    label_lines = fields.One2many(comodel_name='aas.stock.receipt.product.label.wizard', inverse_name='wizard_id', string=u'标签明细')


    @api.onchange('product_id')
    def action_change_product(self):
        self.lot_lines, self.label_lines, self.product_qty = [], [], 0.0
        if self.product_id:
            self.product_uom, self.need_warranty = self.product_id.uom_id.id, self.product_id.need_warranty
        else:
            self.product_uom, self.need_warranty = False, False

    @api.multi
    def write(self, vals):
        if vals.get('product_id'):
            product_id = self.env['product.product'].browse(vals.get('product_id'))
            vals.update({'product_uom': product_id.uom_id.id, 'need_warranty': product_id.need_warranty})
        return super(AASStockReceiptProductWizard, self).write(vals)





    @api.one
    def action_check_lots(self):
        if not self.product_qty or float_compare(self.product_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise UserError(u'收货数量必须是一个正数！')
        if not self.lot_lines or len(self.lot_lines) <= 0:
            raise UserError(u'请先添加批次明细！')
        total_lot_qty = 0.0
        for lline in self.lot_lines:
            if self.need_warranty and not lline.warranty_date:
                raise UserError(u'批次%s未添加质保日期'% lline.lot_name)
            total_lot_qty += lline.lot_qty
        if float_compare(self.product_qty, total_lot_qty, precision_rounding=0.000001) != 0.0:
            raise UserError(u'拆分的批次总数必须和收货数量相同！')


    @api.depends('product_qty', 'lot_lines.lot_qty', 'label_lines.label_qty')
    def _compute_lot_split(self):
        for record in self:
            record.split_qty, record.balance_qty = 0.0, record.product_qty
            if record.label_lines and len(record.label_lines) > 0:
                record.split_qty = sum([lline.label_qty for lline in record.label_lines])
                record.balance_qty = record.product_qty - record.split_qty
            elif record.lot_lines and len(record.lot_lines) > 0:
                record.split_qty = sum([lline.lot_qty for lline in self.lot_lines])
                record.balance_qty = record.product_qty - record.split_qty



    @api.multi
    def action_lot_lines_split(self):
        self.ensure_one()
        self.action_check_lots()
        for lline in self.lot_lines:
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
        if not self.label_lines or len(self.label_lines) <= 0:
            raise UserError(u'请先添加标签明细！')
        total_label_qty = 0.0
        for lline in self.label_lines:
            if self.need_warranty and not lline.warranty_date:
                raise UserError(u'请仔细检查有标签未添加质保日期')
            total_label_qty += lline.label_qty
        if float_compare(self.product_qty, total_label_qty, precision_rounding=0.000001) != 0.0:
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
        receipt, product, lotdict = self.receipt_id, self.product_id, {}
        if receipt.receipt_type=='purchase':
            location_id = self.env.ref('stock.stock_location_suppliers').id
        elif receipt.receipt_type=='sundry':
            location_id = self.env.ref('aas_wms.stock_location_sundry').id
        else:
            location_id = self.env['stock.warehouse'].get_default_warehouse().lot_stock_id.id
        receipt_labels = []
        for lline in self.label_lines:
            if lline.lot_name in lotdict:
                lot_id = lotdict[lline.lot_name]
            else:
                lot_id = self.get_product_lot(product, lline.lot_name).id
                lotdict[lline.lot_name] = lot_id
            label = self.action_build_label(lot_id, lline.label_qty, location_id, lline.warranty_date)
            receipt_labels.append((0, 0, {
                'receipt_id': receipt.id, 'label_id': label.id, 'product_id': label.product_id.id, 'product_uom': label.product_uom.id,
                'origin_order': label.origin_order, 'product_lot': lot_id, 'label_location': location_id, 'product_qty': label.product_qty
            }))
        if not self.line_id:
            self.env['aas.stock.receipt.line'].create({
                'receipt_id': receipt.id, 'product_id': self.product_id.id, 'product_qty': self.product_qty,
                'origin_order': self.origin_order, 'label_related': True, 'label_list': receipt_labels,
                'push_location': False if not self.product_id.push_location else self.product_id.push_location.id
            })
        else:
            self.line_id.write({{'label_related': True, 'label_list': receipt_labels}})


    @api.multi
    def action_build_label(self, lot_id, lot_qty, location_id, warranty_date):
        self.ensure_one()
        receipt = self.receipt_id
        labelvals = {'product_id': self.product_id.id, 'product_uom': self.product_id.uom_id.id}
        labelvals.update({'location_id': location_id, 'product_qty': lot_qty, 'product_lot': lot_id, 'state': 'draft'})
        labelvals.update({'company_id': self.env.user.company_id.id, 'origin_order': self.origin_order})
        labelvals.update({'locked': True, 'locked_order': receipt.name, 'partner_id': receipt.partner_id and receipt.partner_id.id})
        labelvals.update({'warranty_date': warranty_date or False})
        return self.env['aas.product.label'].create(labelvals)







class AASStockReceiptProductLotWizard(models.TransientModel):
    _name = "aas.stock.receipt.product.lot.wizard"
    _description = u"收货明细产品批次向导"
    _rec_name = "lot_name"

    wizard_id = fields.Many2one(comodel_name='aas.stock.receipt.product.wizard', string=u'收货明细产品向导', ondelete='cascade')
    lot_name = fields.Char(string=u"批次名称", required=True)
    lot_qty = fields.Float(string=u'批次数量', digits=dp.get_precision('Product Unit of Measure'), required=True)
    label_qty = fields.Float(string=u'每包装数量', digits=dp.get_precision('Product Unit of Measure'), required=True)
    warranty_date = fields.Date(string=u'质保日期')


    @api.one
    @api.constrains('lot_qty', 'label_qty')
    def _check_lot_qty(self):
        if self.lot_qty and float_compare(self.lot_qty, 0.0, precision_rounding=0.000001) < 0.0:
            raise ValidationError(u"批次%s数量设置无效，必须是一个正数！"% self.lot_name)
        if float_is_zero(self.lot_qty, precision_rounding=0.000001):
            raise ValidationError(u"批次%s数量设置无效，必须是一个正数！"% self.product_lot_name)
        if self.label_qty and float_compare(self.label_qty, 0.0, precision_rounding=0.000001) < 0.0:
            raise ValidationError(u"批次%s每包装数量设置无效，必须是一个正数！"% self.lot_name)
        if float_is_zero(self.label_qty, precision_rounding=0.000001):
            raise ValidationError(u"批次%s每包装数量设置无效，必须是一个大于零的正数！"% self.lot_name)
        if float_compare(self.label_qty, self.lot_qty, precision_rounding=0.000001) > 0.0:
            raise ValidationError(u"批次%s每包装数量设置无效，不能超过批次的总数量！"% self.lot_name)



    @api.one
    def action_split_lot(self):
        temp_qty, label_lines = self.lot_qty, []
        label_count = int(math.ceil(self.lot_qty / self.label_qty))
        for i in range(0, label_count):
            if float_is_zero(temp_qty, precision_rounding=0.000001):
                break
            labelvals = {'lot_name': self.lot_name, 'warranty_date': self.warranty_date}
            if float_compare(temp_qty, self.label_qty, precision_rounding=0.000001) >= 0.0:
                labelvals['label_qty'] = self.label_qty
                temp_qty -= self.label_qty
            else:
                labelvals['label_qty'] = temp_qty
                temp_qty = 0.0
            label_lines.append((0, 0, labelvals))
        self.wizard_id.write({'label_lines': label_lines})







class AASStockReceiptProductLabelWizard(models.TransientModel):
    _name = "aas.stock.receipt.product.label.wizard"
    _description = u"收货明细产品标签向导"

    wizard_id = fields.Many2one(comodel_name='aas.stock.receipt.product.wizard', string=u'收货明细产品向导', ondelete='cascade')
    lot_name = fields.Char(string=u"批次名称", required=True)
    label_qty = fields.Float(string=u'标签数量', digits=dp.get_precision('Product Unit of Measure'), required=True)
    warranty_date = fields.Date(string=u'质保日期')
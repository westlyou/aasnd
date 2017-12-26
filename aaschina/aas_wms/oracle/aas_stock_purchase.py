# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-5 11:30
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class AASEBSPurchaseOrder(models.Model):
    _auto = False
    _log_access = False
    _name = 'aas.ebs.purchase.order'
    _description = 'AAS EBS Purchase Order'
    _order = 'id desc'

    name = fields.Char(string=u'订单号')
    partner_id = fields.Integer(string=u'供应商')
    created_by = fields.Integer(string='created_by')
    creation_date = fields.Datetime(string=u'创建日期')
    last_update_date = fields.Datetime(string=u'修改日期')
    last_updated_by = fields.Integer(string='last_updated_by')



class AASEBSPurchaseOrderLine(models.Model):
    _auto = False
    _log_access = False
    _name = 'aas.ebs.purchase.order.line'
    _description = 'AAS EBS Purchase Order Line'


    order_id = fields.Many2one(comodel_name='aas.ebs.purchase.order', string=u'采购订单')
    product_id = fields.Integer(string=u'产品')
    product_qty = fields.Float(string=u'数量')
    created_by = fields.Integer(string='created_by')
    creation_date = fields.Datetime(string=u'创建日期')
    last_update_date = fields.Datetime(string=u'修改日期')
    last_updated_by = fields.Integer(string='last_updated_by')



class AASStockPurchaseOrder(models.Model):
    _name = 'aas.stock.purchase.order'
    _description = 'AAS Stock Purchase Order'
    _order = 'id desc'

    name = fields.Char(string=u'订单号')
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'供应商')
    created_by = fields.Integer(string='created_by')
    creation_date = fields.Datetime(string=u'创建日期')
    last_update_date = fields.Datetime(string=u'修改日期')
    last_updated_by = fields.Integer(string='last_updated_by')
    ebs_order_id = fields.Integer(string=u'EBS采购订单ID')
    ebsorder = fields.Boolean(string=u'Oracle订单', default=False, copy=False)
    receiptable = fields.Boolean(string=u'可否收货', compute='_compute_receiptable', store=True)
    order_lines = fields.One2many(comodel_name='aas.stock.purchase.order.line', inverse_name='order_id', string=u'采购明细')

    @api.depends('order_lines.receiptable')
    def _compute_receiptable(self):
        for record in self:
            record.receiptable = any([rline.receiptable for rline in record.order_lines])

    _sql_constraints = [
        ('uniq_name', 'unique (name)', u'采购收货订单号不可以重复！')
    ]


    @api.model
    def action_import_order(self, order_number):
        """
        导入采购订单
        :param order_number:
        :return:
        """
        values = {'success': True, 'message': ''}
        if self.env['aas.stock.purchase.order'].search_count([('name', '=', order_number)]) > 0:
            values.update({'success': False, 'message': u'订单%s已存在，请不要重复导入！'% order_number})
            return values
        ebsorder = self.env['aas.ebs.purchase.order'].search([('name', '=', order_number)], limit=1)
        if not ebsorder:
            values.update({'success': False, 'message': u'订单%s不存在，请不要导入！'% order_number})
            return values
        ordervals = {
            'name': ebsorder.name, 'partner_id': ebsorder.partner_id, 'ebs_order_id': ebsorder.id,'created_by': ebsorder.created_by,
            'creation_date': ebsorder.creation_date, 'last_updated_by': ebsorder.last_updated_by, 'last_update_date': ebsorder.last_update_date
        }
        ebsorderlines = self.env['aas.ebs.purchase.order.line'].search([('order_id', '=', ebsorder.id)])
        if ebsorderlines and len(ebsorderlines) > 0:
            productdict = {}
            for eline in ebsorderlines:
                pkey = 'P'+str(eline.product_id)
                if pkey in productdict:
                    productdict[pkey]['product_qty'] += eline.product_qty
                else:
                    tproduct = self.env['product.product'].browse(eline.product_id)
                    if not tproduct:
                        values.update({'success': False, 'message': u'请仔细检查，可能有Oracle产品未同步到当前系统！'})
                        return values
                    productdict[pkey] = {
                        'product_id': eline.product_id, 'product_uom': tproduct.uom_id.id, 'product_qty': eline.product_qty,
                        'order_name': ebsorder.name, 'partner_id': ebsorder.partner_id,'creation_date': ebsorder.creation_date,
                        'last_update_date': ebsorder.last_update_date, 'created_by': ebsorder.created_by, 'last_updated_by': ebsorder.last_updated_by
                    }
            ordervals['order_lines'] = [(0, 0, pval) for pkey, pval in productdict.items()]
        ordervals['ebsorder'] = True
        purchaseorder = self.env['aas.stock.purchase.order'].create(ordervals)
        values['purchaseid'] = purchaseorder.id
        return values


    @api.multi
    def action_synchronize(self):
        """
        同步采购订单
        :return:
        """
        self.ensure_one()
        if self.ebs_order_id:
            ebsorder = self.env['aas.ebs.purchase.order'].browse(self.ebs_order_id)
        else:
            ebsorder = self.env['aas.ebs.purchase.order'].search([('name', '=', self.name)], limit=1)
        if not ebsorder:
            raise UserError(u"Oracle中未搜索到此采购订单！")
        ebs_purchase_dict, aas_purchase_dict = {}, {}
        ebs_order_lines = self.env['aas.ebs.purchase.order.line'].search([('order_id', '=', ebsorder.id)])
        if ebs_order_lines and len(ebs_order_lines) > 0 :
            for ebsline in ebs_order_lines:
                product_key = 'P'+str(ebsline.product_id)
                if product_key in ebs_purchase_dict:
                    ebs_purchase_dict[product_key]['product_qty'] += ebsline.product_qty
                else:
                    tproduct = self.env['product.product'].browse(ebsline.product_id)
                    if not tproduct:
                        raise UserError(u'请仔细检查，可能有Oracle产品未同步到当前系统！')
                    ebs_purchase_dict[product_key] = {
                        'product_id': ebsline.product_id,
                        'product_qty': ebsline.product_qty,
                        'product_uom': tproduct.uom_id.id,
                        'creation_date': ebsline.creation_date,
                        'last_update_date': ebsline.last_update_date,
                        'created_by': ebsline.created_by,
                        'last_updated_by': ebsline.last_updated_by,
                        'order_name': self.name,
                        'partner_id': ebsline.partner_id.id
                    }
        if self.order_lines and len(self.order_lines) > 0:
            for aasline in self.order_lines:
                product_key = 'P'+str(aasline.product_id.id)
                aas_purchase_dict[product_key] = {
                    'id': aasline.id,
                    'product_id': aasline.product_id.id,
                    'product_code': aasline.product_id.default_code,
                    'product_qty': aasline.product_qty,
                    'receipt_qty': aasline.receipt_qty,
                    'rejected_qty': aasline.rejected_qty
                }
        aas_line_list = []
        if len(ebs_purchase_dict) > 0:
            for pkey in ebs_purchase_dict:
                ebs_line = ebs_purchase_dict[pkey]
                if pkey not in aas_purchase_dict:
                    aas_line_list.append((0, 0, ebs_line))
                    continue
                aas_line = aas_purchase_dict[pkey]
                if float_compare(ebs_line['product_qty'], aas_line['product_qty'], precision_rounding=0.000001) != 0:
                    if float_compare(ebs_line['product_qty'], aas_line['receipt_qty'], precision_rounding=0.000001) < 0:
                        raise UserError(u'订单数量不能小于已收货数量')
                    aas_line_list.append((1, aas_line['id'], {'product_qty': ebs_line['product_qty']}))
                del aas_purchase_dict[pkey]
        if len(aas_purchase_dict) > 0:
            for pkey in aas_purchase_dict:
                aas_line = aas_purchase_dict[pkey]
                if float_compare(aas_line['receipt_qty'], aas_line['rejected_qty'], precision_rounding=0.000001) != 0:
                    raise UserError(u"产品：%s已有收货,不可以清除！"% aas_line['product_code'])
                else:
                    aas_line_list.append((2, aas_line['id'], False))
        if len(aas_line_list) > 0:
            self.write({'order_lines': aas_line_list})
        return {"type": "ir.actions.client", "tag": "reload"}


    @api.multi
    def action_purchase_receipt(self):
        """
        生成采购收货单
        :return:
        """
        self.ensure_one()
        plines = []
        for pline in self.order_lines:
            receipt_qty = pline.product_qty + pline.rejected_qty - pline.receipt_qty - pline.doing_qty
            if float_compare(receipt_qty, 0.0, precision_rounding=0.000001) > 0.0:
                plines.append((0, 0, {'line_id': pline.id, 'receipt_qty': receipt_qty, 'product_qty': receipt_qty}))
        if not plines or len(plines) <= 0:
            raise UserError(u'请仔细检查，可能当前采购订单已完成收货！')

        wizard = self.env['aas.stock.purchase.receipt.wizard'].create({
            'partner_id': self.partner_id.id, 'purchase_lines': plines
        })
        view_form = self.env.ref('aas_wms.view_form_aas_stock_purchase_receipt_line')
        return {
            'name': u"收货明细",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.stock.purchase.receipt.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }




class AASStockPurchaseOrderLine(models.Model):
    _name = 'aas.stock.purchase.order.line'
    _description = 'AAS Stock Purchase Order Line'
    _rec_name = 'line_name'

    order_id = fields.Many2one(comodel_name='aas.stock.purchase.order', string=u'采购订单', ondelete='cascade')
    order_name = fields.Char(string=u'订单号')
    line_name = fields.Char(string=u'采购明细')
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'供应商')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位')
    product_qty = fields.Float(string=u'订单数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    receipt_qty = fields.Float(string=u'收货数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    rejected_qty = fields.Float(string=u'退货数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    doing_qty = fields.Float(string=u'确认数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    creation_date = fields.Datetime(string=u'创建日期')
    last_update_date = fields.Datetime(string=u'修改日期')
    created_by = fields.Integer(string='created_by')
    last_updated_by = fields.Integer(string='last_updated_by')
    receiptable = fields.Boolean(string=u'可否收货', compute='_compute_receiptable', store=True)

    @api.depends('product_qty', 'receipt_qty', 'rejected_qty', 'doing_qty')
    def _compute_receiptable(self):
        for record in self:
            receipt_qty = record.product_qty+record.rejected_qty-record.receipt_qty-record.doing_qty
            record.receiptable = float_compare(receipt_qty, 0.0, precision_rounding=0.000001) > 0.0



    @api.model
    def action_before_create(self, vals):
        if vals.get('order_id') and (not vals.get('order_name') or not vals.get('partner_id')):
            order = self.env['aas.stock.purchase.order'].browse(vals.get('order_id'))
            vals.update({'order_name': order.name, 'partner_id': order.partner_id.id})
        if not vals.get('product_uom'):
            product_id = self.env['product.product'].browse(vals.get('product_id'))
            vals['product_uom'] = product_id.uom_id.id


    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        record = super(AASStockPurchaseOrderLine, self).create(vals)
        line_name = '['+record.order_id.name+']'+record.product_id.default_code
        record.write({'line_name': line_name})
        return record




class AASStockPurchaseReceiptWizard(models.TransientModel):
    _name = 'aas.stock.purchase.receipt.wizard'
    _description = 'AAS Stock Purchase Receipt Wizard'

    partner_id = fields.Many2one(comodel_name='res.partner', string=u'供应商', ondelete='restrict')

    purchase_orders = fields.One2many(comodel_name='aas.stock.purchase.receipt.order.wizard', inverse_name='wizard_id', string=u'订单明细')
    purchase_lines = fields.One2many(comodel_name='aas.stock.purchase.receipt.line.wizard', inverse_name='wizard_id', string=u'采购明细')


    @api.multi
    def action_order_lines(self):
        """
        通过添加多个采购订单生成待收货的订单明细
        :return:
        """
        self.ensure_one()
        if not self.purchase_orders or len(self.purchase_orders) <= 0:
            raise UserError(u'请先添加采购订单！')
        lines = []
        for wporder in self.purchase_orders:
            porder = wporder.purchase_id
            for pline in porder.order_lines:
                receipt_qty = pline.product_qty + pline.rejected_qty - pline.receipt_qty - pline.doing_qty
                if float_compare(receipt_qty, 0.0, precision_rounding=0.000001) > 0.0:
                    lines.append((0, 0, {'line_id': pline.id, 'receipt_qty': receipt_qty, 'product_qty': receipt_qty}))
        if not lines or len(lines) <= 0:
            raise UserError(u'请仔细检查，可能当前采购订单都已完成收货！')
        self.write({'purchase_lines': lines})
        view_form = self.env.ref('aas_wms.view_form_aas_stock_purchase_receipt_line')
        return {
            'name': u"收货明细",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.stock.purchase.receipt.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context
        }



    @api.multi
    def action_receipt(self):
        """
        生成收货单
        :return:
        """
        self.ensure_one()
        if not self.purchase_lines or len(self.purchase_lines) <= 0:
            raise UserError(u'请重新生成收货明细！')
        receiptvals, rlines, orderdict = {'partner_id': self.partner_id.id, 'receipt_type': 'purchase'}, [], {}
        for pline in self.purchase_lines:
            tline, torder, tproduct = pline.line_id, pline.line_id.order_id, pline.line_id.product_id
            rlines.append((0, 0, {
                'product_id': tproduct.id, 'product_uom': tproduct.uom_id.id, 'origin_order': tline.order_id.name,
                'receipt_type': 'purchase', 'push_location': tproduct.push_location and tproduct.push_location.id,
                'product_qty': pline.product_qty
            }))
            tkey, doing_qty = 'T'+str(torder.id), tline.doing_qty+pline.product_qty
            if tkey in orderdict:
                orderdict[tkey]['lines'].append((1, tline.id, {'doing_qty': doing_qty}))
            else:
                orderdict[tkey] = {'order': torder, 'lines': [(1, tline.id, {'doing_qty': doing_qty})]}
        receiptvals['receipt_lines'] = rlines
        receipt = self.env['aas.stock.receipt'].create(receiptvals)
        # 更新采购明细的doing_qty
        for okey, oval in orderdict.items():
            porder, plines = oval['order'], oval['lines']
            porder.write({'order_lines': plines})
        view_form = self.env.ref('aas_wms.view_form_aas_stock_receipt_purchase')
        return {
            'name': u"采购收货",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.stock.receipt',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'self',
            'res_id': receipt.id,
            'context': self.env.context
        }




class AASStockPurchaseReceiptOrderWizard(models.TransientModel):
    _name = 'aas.stock.purchase.receipt.order.wizard'
    _description = 'AAS Stock Purchase Receipt Order Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.stock.purchase.receipt.wizard', string=u'采购收货', ondelete='cascade')
    purchase_id = fields.Many2one(comodel_name='aas.stock.purchase.order', string=u'采购订单', ondelete='cascade')


class AASStockPurchaseReceiptLineWizard(models.TransientModel):
    _name = 'aas.stock.purchase.receipt.line.wizard'
    _description = 'AAS Stock Purchase Receipt Line Wizard'


    wizard_id = fields.Many2one(comodel_name='aas.stock.purchase.receipt.wizard', string=u'采购收货', ondelete='cascade')
    line_id = fields.Many2one(comodel_name='aas.stock.purchase.order.line', string=u'收货明细', ondelete='cascade')
    receipt_qty = fields.Float(string=u'可收货数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    product_qty = fields.Float(string=u'收货数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)


    @api.one
    @api.constrains('product_qty')
    def action_check_product_qty(self):
        if float_compare(self.product_qty, self.receipt_qty, precision_rounding=0.000001) > 0.0:
            raise ValidationError(u'收货数量不可以大于最大可收货数量')
        if float_compare(self.product_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise ValidationError(u'收货数量必须是一个正数！')




class AASStockReceipt(models.Model):
    _inherit = 'aas.stock.receipt'

    @api.one
    def action_cancel(self):
        if self.receipt_type == 'purchase':
            if self.state == 'done':
                raise UserError(u'收货单%s已完成，请不要取消！'% self.name)
            if self.state == 'cancel':
                return True
            # 采购收货单取消之后要更新采购订单明细的已收货数量或处理中的数量
            for rline in self.receipt_lines:
                if not rline.origin_order or rline.state == 'cancel':
                    continue
                linedomain = [('product_id', '=', rline.product_id.id), ('order_name', '=', rline.origin_order)]
                purchaseline = self.env['aas.stock.purchase.order.line'].search(linedomain, limit=1)
                if not purchaseline:
                    continue
                if rline.state == 'draft':
                    temp_qty = purchaseline.doing_qty - rline.product_qty
                    if float_compare(temp_qty, 0.0, precision_rounding=0.000001) < 0.0:
                        temp_qty = 0.0
                    purchaseline.write({'doing_qty': temp_qty})
                else:
                    temp_qty = purchaseline.receipt_qty - rline.product_qty
                    if float_compare(temp_qty, 0.0, precision_rounding=0.000001) < 0.0:
                        temp_qty = 0.0
                    purchaseline.write({'receipt_qty': temp_qty})
        return super(AASStockReceipt, self).action_cancel()





class AASStockReceiptLine(models.Model):
    _inherit = 'aas.stock.receipt.line'

    @api.one
    def action_confirm(self):
        super(AASStockReceiptLine, self).action_confirm()
        if self.receipt_type=='purchase' and self.origin_order:
            # 采购收货确认之后需要将采购明细上的处理数量更新为已收货数量
            linedomain = [('product_id', '=', self.product_id.id), ('order_name', '=', self.origin_order)]
            purchaseline = self.env['aas.stock.purchase.order.line'].search(linedomain, limit=1)
            if purchaseline:
                receipt_qty, doing_qty = purchaseline.receipt_qty + self.product_qty, purchaseline.doing_qty - self.product_qty
                if float_compare(doing_qty, 0.0, precision_rounding=0.000001) < 0.0:
                    doing_qty = 0.0
                if float_compare(receipt_qty, 0.0, precision_rounding=0.000001) < 0.0:
                    receipt_qty = 0.0
                purchaseline.write({'receipt_qty': receipt_qty, 'doing_qty': doing_qty})


    @api.multi
    def unlink(self):
        purchasedict = {}
        for record in self:
            if record.receipt_type != 'purchase' or not record.origin_order:
                continue
            linedomain = [('product_id', '=', record.product_id.id), ('order_name', '=', record.origin_order)]
            purchaseline = self.env['aas.stock.purchase.order.line'].search(linedomain, limit=1)
            if not purchaseline:
                continue
            pkey = 'PL'+str(purchaseline.id)
            if pkey not in purchasedict:
                purchasedict[pkey] = {
                    'purchaseline': purchaseline,
                    'doing_qty': purchaseline.doing_qty, 'receipt_qty': purchaseline.receipt_qty
                }
            if record.state == 'draft':
                purchasedict[pkey]['doing_qty'] -= record.product_qty
            else:
                purchasedict[pkey]['receipt_qty'] -= record.product_qty
        result = super(AASStockReceiptLine, self).unlink()
        if purchasedict and len(purchasedict) > 0:
            # 采购收货单删除时需要清理采购订单明细上的已收数量或处理中数量
            for pkey, pval in purchasedict.items():
                purchaseline, doing_qty, receipt_qty = pval['purchaseline'], pval['doing_qty'], pval['receipt_qty']
                if float_compare(doing_qty, 0.0, precision_rounding=0.000001) < 0.0:
                    doing_qty = 0.0
                if float_compare(receipt_qty, 0.0, precision_rounding=0.000001) < 0.0:
                    receipt_qty = 0.0
                purchaseline.write({'doing_qty': doing_qty, 'receipt_qty': receipt_qty})
        return result


class AASStockDelivery(models.Model):
    _inherit = 'aas.stock.delivery'

    @api.one
    def action_deliver_done(self):
        super(AASStockDelivery, self).action_deliver_done()
        if self.delivery_type != 'purchase' or not self.origin_order:
            return
        purchaseorderdomain = [('name', '=', self.origin_order)]
        purchaseorder = self.env['aas.stock.purchase.order'].search(purchaseorderdomain, limit=1)
        if not purchaseorder:
            return
        deliveryproductdict, purchaselines = {}, []
        for dline in self.delivery_lines:
            pkey = 'P'+str(dline.product_id.id)
            if pkey in deliveryproductdict:
                deliveryproductdict[pkey] += dline.product_qty
            else:
                deliveryproductdict[pkey] = dline.product_qty
        for pline in purchaseorder.order_lines:
            pkey = 'P'+str(pline.product_id.id)
            if pkey in deliveryproductdict:
                purchaselines.append((1, pline.id, {'rejected_qty': pline.rejected_qty+deliveryproductdict[pkey]}))
        if purchaselines and len(purchaselines) > 0:
            purchaseorder.write({'order_lines': purchaselines})
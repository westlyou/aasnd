# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError
from odoo.tools.sql import drop_view_if_exists

import logging
_logger = logging.getLogger(__name__)

RECEIPT_TYPE = [('purchase', u'采购收货'), ('manufacture', u'生产入库'), ('manreturn', u'生产退料'), ('sundry', u'杂项入库')]
RECEIPT_STATE = [('draft', u'草稿'), ('confirm', u'确认'), ('tocheck', u'待检'), ('checked', u'已检'), ('receipt', u'收货'), ('done', u'完成'), ('cancel', u'取消')]



class AASStockReceipt(models.Model):
    _name = 'aas.stock.receipt'
    _description = u'收货单'
    _order = "id desc"

    name = fields.Char(string=u'名称', copy=False)
    order_user = fields.Many2one(comodel_name='res.users', string=u'下单人员', ondelete='restrict', default=lambda self: self.env.user)
    order_time = fields.Datetime(string=u'下单时间', default=fields.Datetime.now)
    receipt_type = fields.Selection(selection=RECEIPT_TYPE, string=u'收货类型')
    state = fields.Selection(selection=RECEIPT_STATE, string=u'状态', default='draft')
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'业务伙伴', ondelete='restrict')
    remark = fields.Text(string=u'备注', copy=False)
    done_time = fields.Datetime(string=u'完成时间')
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)

    receipt_lines = fields.One2many(comodel_name='aas.stock.receipt.line', inverse_name='receipt_id', string=u'收货明细')
    label_lines = fields.One2many(comodel_name='aas.stock.receipt.label', inverse_name='receipt_id', string=u'收货标签')
    operation_lines = fields.One2many(comodel_name='aas.stock.receipt.operation', inverse_name='receipt_id', string=u'收货作业')
    move_lines = fields.One2many(comodel_name='aas.stock.receipt.move', inverse_name='receipt_id', string=u'执行明细')


    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('aas.stock.receipt')
        return super(AASStockReceipt, self).create(vals)

    @api.one
    def action_refresh_push_location(self):
        lines = []
        if not self.receipt_lines or len(self.receipt_lines) <= 0:
            return
        for rline in self.receipt_lines:
            if not rline.product_id or not rline.product_id.push_location:
                continue
            lines.append((1, rline.id, {'push_location': rline.product_id.push_location.id}))
        if lines and len(lines) > 0:
            self.write({'receipt_lines': lines})

    @api.one
    def action_confirm(self):
        if not self.receipt_lines or len(self.receipt_lines) <= 0:
            raise UserError(u'您还没添加收货明细，不可以直接确认收货，请先添加收货明细！')
        if any([not rline.label_related for rline in self.receipt_lines]):
            raise UserError(u'您还有收货明细未关联标签，请仔细检查！')
        for rline in self.receipt_lines:
            if rline.state != 'draft':
                continue
            rline.action_confirm()
        if self.state == 'draft':
            self.write({'state': 'confirm'})


class AASStockReceiptLine(models.Model):
    _name = 'aas.stock.receipt.line'
    _description = u'收货明细'
    _rec_name = 'product_id'
    _order = "id desc, product_id"

    receipt_id = fields.Many2one(comodel_name='aas.stock.receipt', string=u'收货单', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品名称', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'产品单位')
    origin_order = fields.Char(string=u'来源单据', copy=False)
    label_related = fields.Boolean(string=u'标签关联', default=False)
    receipt_type = fields.Selection(selection=RECEIPT_TYPE, string=u'收货类型')
    state = fields.Selection(selection=RECEIPT_STATE, string=u'状态', default='draft')
    push_location = fields.Many2one(comodel_name='stock.location', string=u'推荐库位', help=u'最近上架库位')
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'收货库位', ondelete='restrict')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string=u'收货仓库', ondelete='restrict')
    product_qty = fields.Float(string=u'收货数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    receipt_qty = fields.Float(string=u'已上架数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    doing_qty = fields.Float(string=u'处理中数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    label_list = fields.One2many(comodel_name='aas.stock.receipt.label', inverse_name='line_id', string=u'收货标签')
    operation_list = fields.One2many(comodel_name='aas.stock.receipt.operation', inverse_name='line_id', string=u'收货作业')

    _sql_constraints = [
        ('uniq_receipt_line', 'unique (receipt_id, product_id, origin_order)', u'请不要在同一单据上对相同产品重复收货！')
    ]

    @api.model
    def action_before_create(self, vals):
        if ('location_id' not in vals) or (not vals.get('location_id')):
            mainbase = self.env['stock.warehouse'].get_default_warehouse()
            vals['warehouse_id'], vals['location_id'] = mainbase.id, mainbase.wh_input_stock_loc_id.id
        vals['company_id'] = self.env.user.company_id.id
        product_id = self.env['product.product'].browse(vals.get('product_id'))
        vals['product_uom'] = product_id.uom_id.id
        receipt_id = self.env['aas.stock.receipt'].browse(vals.get('receipt_id'))
        vals['receipt_type'] = receipt_id.receipt_type

    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        return super(AASStockReceiptLine, self).create(vals)


    @api.one
    def action_refresh_push_location(self):
        if self.product_id and self.product_id.push_location:
            self.write({'push_location': self.product_id.push_location.id})

    @api.one
    def action_confirm(self):
        if self.state != 'draft':
            return
        if not self.label_related:
            raise UserError(u'%s还未关联收货标签，不可以确认收货！'% self.product_id.default_code)
        movedict, labels, receipt = {}, self.env['aas.product.label'], self.receipt_id
        for rlabel in self.label_list:
            label = rlabel.label_id
            mkey = 'move_'+str(label.product_lot.id)+'_'+str(label.location_id.id)
            if mkey in movedict:
                movedict[mkey]['product_qty'] += label.product_qty
            else:
                movedict[mkey] = {
                    'product_id': self.product_id.id, 'product_uom': self.product_uom, 'product_lot': label.product_lot.id,
                    'origin_order': self.origin_order, 'receipt_type': self.receipt_type, 'partner_id': self.receipt_id.receipt_id and self.receipt_id.receipt_id.id,
                    'receipt_user': self.env.user.id, 'location_src_id': label.location_id.id, 'location_dest_id': self.location_id.id, 'product_qty': label.product_qty, 'company_id': self.company_id.id
                }
        self.label_list.write({'location_id': self.location_id.id, 'stocked': True, 'state': 'normal'})
        self.write({'state': 'confirm'})
        move_lines, receiptvals = [], {}
        for mkey, mval in movedict.items():
            move_lines.append((0, 0, mval))
        receiptvals['move_lines'] = move_lines
        if receipt.state == 'draft' and all([rline.state not in ['draft', 'cancel'] for rline in receipt.receipt_lines]):
            receiptvals['state'] = 'confirm'
        receipt.write(receiptvals)

    @api.multi
    def action_label_list(self):
        self.ensure_one()
        if self.label_related:
            action = self.env.ref('aas_wms.action_aas_stock_receipt_label')
            form = self.env.ref('aas_wms.view_form_aas_stock_receipt_label')
            tree = self.env.ref('aas_wms.view_tree_aas_stock_receipt_label')
            result = {
                'name': action.name,
                'type': action.type,
                'views': [[tree.id, 'tree'], [form.id, 'form']],
                'target': action.target,
                'context': action.context,
                'res_model': action.res_model,
            }
            if self.label_list and len(self.label_list) > 0:
                result['domain'] = "[('id','in',%s)]" % self.label_list.ids
            else:
                result = {'type': 'ir.actions.act_window_close'}
            return result
        else:
            wizard = self.env['aas.stock.receipt.product.wizard'].create({
                'receipt_line_id': self.id, 'receipt_product_id': self.product_id.id, 'receipt_product_uom': self.product_uom.id,
                'receipt_product_qty': self.product_qty, 'receipt_need_warranty': self.product_id.need_warranty
            })
            view_form = self.env.ref('aas_wms.view_form_aas_stock_receipt_product_lot_wizard')
            return {
                'name': u"批次明细",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'aas.stock.receipt.product.wizard',
                'views': [(view_form.id, 'form')],
                'view_id': view_form.id,
                'target': 'new',
                'res_id': wizard.id,
                'context': self.env.context
            }




class AASStockReceiptLabel(models.Model):
    _name = 'aas.stock.receipt.label'
    _description = u'收货标签'
    _rec_name = 'label_id'
    _order = "id desc"

    receipt_id = fields.Many2one(comodel_name='aas.stock.receipt', string=u'收货单', ondelete='cascade')
    line_id = fields.Many2one(comodel_name='aas.stock.receipt.line', string=u'收货明细', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'收货标签', ondelete='set null')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品名称', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'产品单位')
    origin_order = fields.Char(string=u'来源单据', copy=False)
    checked = fields.Boolean(string=u'是否作业', default=False, copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    label_location = fields.Many2one(comodel_name='stock.location', string=u'来源库位', ondelete='restrict')
    product_qty = fields.Float(string=u'上架数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    _sql_constraints = [
        ('uniq_receipt_label', 'unique (receipt_id, label_id)', u'请不要重复添加标签！')
    ]


class AASStockReceiptOperation(models.Model):
    _name = 'aas.stock.receipt.operation'
    _description = u'收货作业'
    _order = "id desc"

    receipt_id = fields.Many2one(comodel_name='aas.stock.receipt', string=u'收货单', ondelete='cascade')
    line_id = fields.Many2one(comodel_name='aas.stock.receipt.line', string=u'收货明细', ondelete='cascade')
    rlabel_id = fields.Many2one(comodel_name='aas.stock.receipt.label', string=u'收货标签', ondelete='set null')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品名称', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'产品单位')
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    push_time = fields.Datetime(string=u'上架时间')
    push_onshelf = fields.Boolean(string=u'是否上架', default=False, copy=False)
    push_user = fields.Many2one(comodel_name='res.users', string=u'上架员工', ondelete='restrict')
    product_qty = fields.Float(string=u'上架数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    _sql_constraints = [
        ('uniq_receipt_rlabel', 'unique (receipt_id, label_id)', u'请不要重复添加标签！')
    ]


class AASStockReceiptMove(models.Model):
    _name = 'aas.stock.receipt.move'
    _description = u'执行明细'
    _order = "id desc"

    receipt_id = fields.Many2one(comodel_name='aas.stock.receipt', string=u'收货单', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品名称', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'产品单位')
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    origin_order = fields.Char(string=u'来源单据', copy=False)
    receipt_type = fields.Selection(selection=RECEIPT_TYPE, string=u'收货类型')
    receipt_date = fields.Date(string=u'收货日期', default=fields.Date.today)
    receipt_time = fields.Datetime(string=u'收货时间', default=fields.Datetime.now)
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'业务伙伴', ondelete='restrict')
    receipt_user = fields.Many2one(comodel_name='res.users', string=u'收货员工', ondelete='restrict')
    location_src_id = fields.Many2one(comodel_name='stock.location', string=u'来源库位', ondelete='restrict')
    location_dest_id = fields.Many2one(comodel_name='stock.location', string=u'目标库位', ondelete='restrict')
    product_qty = fields.Float(string=u'收货数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    @api.model
    def create(self, vals):
        record = super(AASStockReceiptMove, self).create(vals)
        record.action_receive_deliver()
        record.action_stock_move()
        return record

    @api.one
    def action_receive_deliver(self):
        """
        更新收发汇总表
        :return:
        """
        if self.location_src_id.usage == 'internal':
            self.env['aas.receive.deliver'].action_deliver(self.product_id.id, self.location_src_id.id, self.product_lot.id, self.product_qty)
        if self.location_dest_id.usage == 'internal':
            self.env['aas.receive.deliver'].action_receive(self.product_id.id, self.location_dest_id.id, self.product_lot.id, self.product_qty)


    @api.one
    def action_stock_move(self):
        """
        生成移库单，更新库存
        :return:
        """
        self.env['stock.move'].create({
            'name': self.receipt_id.name, 'product_id': self.product_id.id, 'product_uom': self.product_uom.id,
            'create_date': fields.Datetime.now(), 'restrict_lot_id': self.product_lot.id, 'product_uom_qty': self.product_qty,
            'location_id': self.location_src_id.id, 'location_dest_id': self.location_dest_id.id, 'company_id': self.company_id.id
        }).action_done()



class AASStockReceiptMoveReport(models.Model):
    _auto = False
    _name = "aas.stock.receipt.move.report"
    _order = "receipt_date desc, product_id"

    product_id = fields.Many2one(comodel_name='product.product', string=u'产品名称', readonly=True)
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'产品单位', readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', readonly=True)
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', readonly=True)
    receipt_date = fields.Date(string=u'收货日期', readonly=True)
    origin_order = fields.Char(string=u'来源单据', readonly=True)
    receipt_user = fields.Many2one(comodel_name='res.users', string=u'收货员工', readonly=True)
    location_src_id = fields.Many2one(comodel_name='stock.location', string=u'来源库位', readonly=True)
    location_dest_id = fields.Many2one(comodel_name='stock.location', string=u'目标库位', readonly=True)
    product_qty = fields.Float(string=u'收货数量', digits=dp.get_precision('Product Unit of Measure'), readonly=True)
    receipt_type = fields.Selection(selection=RECEIPT_TYPE, string=u'收货类型', readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'业务伙伴', readonly=True)


    def _select(self):
        select_str = """
        SELECT min(asrm.id) as id,
        asrm.product_id as product_id,
        asrm.product_uom as product_uom,
        asrm.product_lot as product_lot,
        sum(asrm.product_qty) as product_qty,
        asrm.receipt_date as receipt_date,
        asrm.receipt_user as receipt_user,
        asrm.company_id as company_id,
        asrm.location_src_id as location_src_id,
        asrm.location_dest_id as location_dest_id,
        asrm.origin_order as origin_order,
        asrm.receipt_type as receipt_type,
        asrm.partner_id as partner_id
        """
        return select_str

    def _from(self):
        from_str = """
        aas_stock_receipt_move asrm
        """
        return from_str

    def _group_by(self):
        group_by_str = """
        GROUP BY asrm.product_id,asrm.product_lot,asrm.product_uom,asrm.receipt_date,asrm.receipt_user,asrm.location_src_id,asrm.location_dest_id,
        asrm.company_id,asrm.receipt_type,asrm.partner_id,asrm.origin_order
        """
        return group_by_str

    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s FROM %s %s )""" % (self._table, self._select(), self._from(), self._group_by()))
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError
from odoo.tools.sql import drop_view_if_exists

import logging
_logger = logging.getLogger(__name__)

RECEIPT_TYPE = [('purchase', u'采购收货'), ('manufacture', u'成品入库'), ('manreturn', u'生产退料'), ('sundry', u'杂项入库')]
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
    receipt_lines = fields.One2many(comodel_name='aas.stock.receipt.line', inverse_name='receipt_id', string=u'收货明细')
    label_lines = fields.One2many(comodel_name='aas.stock.receipt.label', inverse_name='receipt_id', string=u'收货标签')
    operation_lines = fields.One2many(comodel_name='aas.stock.receipt.operation', inverse_name='receipt_id', string=u'收货作业')
    move_lines = fields.One2many(comodel_name='aas.stock.receipt.move', inverse_name='receipt_id', string=u'执行明细')
    note_lines = fields.One2many(comodel_name='aas.stock.receipt.note', inverse_name='receipt_id', string=u'备注明细')
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)


    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('aas.stock.receipt')
        return super(AASStockReceipt, self).create(vals)

    @api.multi
    def unlink(self):
        labels = self.env['aas.product.label']
        for record in self:
            if record.state != 'draft':
                raise UserError(u'收货单%s已经在执行，不可以删除！'% record.name)
            if record.label_lines and len(record.label_lines) > 0:
                for rlabel in record.label_lines:
                    labels |= rlabel.label_id
        result = super(AASStockReceipt, self).unlink()
        if labels and len(labels) > 0:
            labels.unlink()
        return result

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


    @api.multi
    def action_label_list(self):
        """
        收入产品并拆分标签，生成收货明细和标签记录
        主要在采购收货、杂项入库、以及生成退料时使用
        :return:
        """
        self.ensure_one()
        wizardvals = {'receipt_id': self.id}
        rline = self.env['aas.stock.receipt.line'].search([('receipt_id', '=', self.id), ('label_related', '=', False)], limit=1)
        if rline:
            wizardvals.update({'line_id': rline.id, 'product_id': rline.product_id.id, 'product_uom': rline.product_uom.id})
            wizardvals.update({'need_warranty': rline.product_id.need_warranty, 'origin_order': rline.origin_order, 'product_qty': rline.product_qty})
        wizard = self.env['aas.stock.receipt.product.wizard'].create(wizardvals)
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

    @api.multi
    def action_receipt_labels(self):
        """
        直接通过标签生成收货单记录
        主要在成品入库、生产退料使用
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.stock.receipt.label.wizard'].create({'receipt_id': self.id})
        view_form = self.env.ref('aas_wms.view_form_aas_stock_receipt_label_wizard')
        return {
            'name': u"标签入库",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.stock.receipt.label.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }


    @api.one
    def action_cancel(self):
        if self.state == 'done':
            raise UserError(u'收货单%s已完成，请不要取消！'% self.name)
        if self.state == 'cancel':
            return True
        outlabels, internallabels = self.env['aas.product.label'], self.env['aas.product.label']
        if self.label_lines and len(self.label_lines) > 0:
            for rlabel in self.label_lines:
                if rlabel.label_location.usage != 'internal':
                    outlabels |= rlabel.label_id
                else:
                    internallabels |= rlabel.label_id
            if outlabels and len(outlabels) > 0:
                outlabels.write({'state': 'over', 'locked': False, 'locked_order': False})
            if internallabels and len(internallabels) > 0:
                internallabels.write({'locked': False, 'locked_order': False})
        receiptvals = {'state': 'cancel'}
        if self.receipt_lines and len(self.receipt_lines) > 0:
            receiptvals['receipt_lines'] = [(1, rline.id, {'state': 'cancel'}) for rline in self.receipt_lines]
        if self.move_lines and len(self.move_lines) > 0:
            receiptvals['move_lines'] = [(0, 0, {
                'product_id': mline.product_id.id, 'product_uom': mline.product_uom.id,
                'product_lot': mline.product_lot.id, 'origin_order': mline.origin_order,
                'receipt_type': mline.receipt_type, 'receipt_user': self.env.user.id,
                'product_qty': mline.product_qty, 'receipt_note': u'取消收货',
                'partner_id': False if not mline.partner_id else mline.partner_id.id,
                'location_src_id': mline.location_dest_id.id, 'location_dest_id': mline.location_src_id.id
            }) for mline in self.move_lines]
        self.write(receiptvals)
        return True




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

    @api.one
    def action_push_all(self):
        if self.state in ['draft', 'cancel', 'tocheck',  'done']:
            raise UserError(u'请仔细检查收货单，当前状态不可以批量上架！')
        for rline in self.receipt_lines:
            rline.action_push_all()

    @api.one
    def action_push_done(self):
        if self.state in ['draft', 'cancel', 'tocheck', 'done']:
            raise UserError(u'请仔细检查收货单，当前状态不可以收货上架！')
        for rline in self.receipt_lines:
            rline.action_push_done()


    @api.model
    def action_print_label(self, printer_id, ids=[], domain=[]):
        values = {'success': True, 'message': ''}
        printer = self.env['aas.label.printer'].browse(printer_id)
        if not printer.field_lines or len(printer.field_lines) <= 0:
            values.update({'success': False, 'message': u'请联系管理员标签打印未指定具体打印内容！'})
            return values
        values.update({'printer': printer.name, 'serverurl': printer.serverurl})
        if printer.model_id.model != 'aas.product.label':
            values.update({'success': False, 'message': u'请仔细检查是否选择正确打印机；如果打印机正确，请联系管理员检查配置是否正确！'})
            return values
        values.update({'printer': printer.name, 'serverurl': printer.serverurl})
        if ids and len(ids) > 0:
            receiptdomain = [('id', 'in', ids)]
        else:
            receiptdomain = domain
        receipts = self.env['aas.stock.receipt'].search(receiptdomain)
        if not receipts or len(receipts) <= 0:
            values.update({'success': False, 'message': u'未搜索到需要打印标签的收货单！'})
            return values
        labelids = []
        for receipt in receipts:
            receiptlabels = self.env['aas.stock.receipt.label'].search([('receipt_id', '=', receipt.id), ('label_current', '=', True)])
            if receiptlabels and len(receiptlabels) > 0:
                labelids.extend([rlabel.label_id.id for rlabel in receiptlabels])
        if not labelids or len(labelids) <= 0:
            values.update({'success': False, 'message': u'暂时不需要打印任何标签！'})
            return values
        field_list = [fline.field_name for fline in printer.field_lines]
        records = self.env['aas.product.label'].search_read(domain=[('id', 'in', labelids)], fields=field_list)
        if not records or len(records) <= 0:
            values.update({'success': False, 'message': u'未搜索到需要打印的标签！'})
            return values
        records = printer.action_correct_records(records)
        values['records'] = records
        return values


    @api.multi
    def action_note(self):
        """
        添加备注
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.stock.receipt.note.wizard'].create({'receipt_id': self.id})
        view_form = self.env.ref('aas_wms.view_form_aas_stock_receipt_note_wizard')
        return {
            'name': u"收货备注",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.stock.receipt.note.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }


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
    need_push = fields.Boolean(string=u'可以上架', compute='_compute_receipt_need_push')
    push_location = fields.Many2one(comodel_name='stock.location', string=u'上架库位', help=u'最近上架库位')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'收货库位', ondelete='restrict')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string=u'收货仓库', ondelete='restrict')
    product_qty = fields.Float(string=u'收货数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    receipt_qty = fields.Float(string=u'已上架数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    doing_qty = fields.Float(string=u'处理中数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    label_list = fields.One2many(comodel_name='aas.stock.receipt.label', inverse_name='line_id', string=u'收货标签')
    operation_list = fields.One2many(comodel_name='aas.stock.receipt.operation', inverse_name='line_id', string=u'收货作业')
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)
    note_lines = fields.One2many(comodel_name='aas.stock.receipt.note', inverse_name='receipt_line', string=u'备注明细')

    product_code = fields.Char(string=u'产品编码')

    _sql_constraints = [
        ('uniq_receipt_line', 'unique (receipt_id, product_id, origin_order)', u'请不要在同一单据上对相同产品重复收货！')
    ]

    @api.depends('receipt_type', 'state', 'product_qty', 'receipt_qty', 'doing_qty')
    def _compute_receipt_need_push(self):
        for record in self:
            states = ['receipt']
            if record.receipt_type=='purchase':
                states.append('checked')
            else:
                states.append('confirm')
            record.need_push = record.state in states and float_compare(record.product_qty, record.receipt_qty+record.doing_qty, precision_rounding=0.000001) > 0.0

    @api.model
    def action_before_create(self, vals):
        if not vals.get('location_id', False):
            mainbase = self.env['stock.warehouse'].get_default_warehouse()
            vals['warehouse_id'], vals['location_id'] = mainbase.id, mainbase.wh_input_stock_loc_id.id
        if not vals.get('receipt_type'):
            receipt_id = self.env['aas.stock.receipt'].browse(vals.get('receipt_id'))
            vals['receipt_type'] = receipt_id.receipt_type
        product_id = self.env['product.product'].browse(vals.get('product_id'))
        vals.update({
            'product_uom': product_id.uom_id.id, 'product_code': product_id.default_code,
            'push_location': False if not product_id.push_location else product_id.push_location.id
        })

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
        context = {'operate_order': self.receipt_id.name}
        if self.env.context and len(self.env.context) > 0:
            context.update(self.env.context)
        movedict, labels, receipt = {}, self.env['aas.product.label'], self.receipt_id
        for rlabel in self.label_list:
            label = rlabel.label_id
            labels |= label
            mkey = 'move_'+str(label.product_lot.id)+'_'+str(label.location_id.id)
            if mkey in movedict:
                movedict[mkey]['product_qty'] += label.product_qty
            else:
                movedict[mkey] = {
                    'product_id': self.product_id.id, 'product_uom': self.product_uom.id, 'product_lot': label.product_lot.id,
                    'origin_order': self.origin_order, 'receipt_type': self.receipt_type, 'partner_id': self.receipt_id.partner_id and self.receipt_id.partner_id.id,
                    'receipt_user': self.env.user.id, 'location_src_id': label.location_id.id, 'location_dest_id': self.location_id.id, 'product_qty': label.product_qty, 'company_id': self.company_id.id
                }
        labels.with_context(context).write({'location_id': self.location_id.id, 'stocked': True, 'state': 'normal'})
        move_lines, receiptvals = [], {'receipt_lines': [(1, self.id, {'state': 'confirm'})]}
        for mkey, mval in movedict.items():
            move_lines.append((0, 0, mval))
        receiptvals['move_lines'] = move_lines
        receipt.write(receiptvals)

    @api.one
    def action_push_all(self):
        if self.state in ['draft', 'cancel', 'tocheck', 'done']:
            raise UserError(u'请仔细检查收货单或收货明细，当前状态不可以批量上架！')
        if not self.push_location:
            raise UserError(u'请先设置好上架库位，再批量上架！')
        labellist = self.env['aas.stock.receipt.label'].search([('line_id', '=', self.id), ('checked', '=', False)])
        if labellist and len(labellist) > 0:
            operationlist = [(0, 0, {'rlabel_id': rlabel.id, 'location_id': self.push_location.id}) for rlabel in labellist]
            self.receipt_id.write({'operation_lines': operationlist})

    @api.one
    def action_push_done(self):
        if self.state in ['draft', 'cancel', 'tocheck', 'done']:
            raise UserError(u'请仔细检查收货单或收货明细，当前状态不可以批量上架！')
        operationlist = self.env['aas.stock.receipt.operation'].search([('line_id', '=', self.id), ('push_onshelf', '=', False)])
        if not operationlist or len(operationlist) <= 0:
            raise UserError(u"请仔细检查，还可能还没有添加上架作业标签！")
        productdict, receiptvals, movedict, operationlines, receiptlabels = {}, {}, {}, [], self.env['aas.stock.receipt.label']
        push_user, push_time, push_date = self.env.user.id, fields.Datetime.now(), fields.Date.today()
        manreturn = True if self.receipt_type == 'manreturn' else False
        for roperation in operationlist:
            pkey = 'P'+str(roperation.product_id.id)
            if pkey in productdict:
                productdict[pkey]['location_id'] = roperation.location_id.id
            else:
                productdict[pkey] = {'product': roperation.product_id, 'location_id': roperation.location_id.id}
            label = roperation.rlabel_id.label_id
            if label.state != 'normal':
                raise UserError(u'标签%s状态异常，非正常状态标签不可以上架！'% label.name)
            operationlines.append((1, roperation.id, {'push_onshelf': True, 'push_user': push_user, 'push_time': push_time}))
            mkey = 'move_'+str(label.product_lot.id)+'_'+str(label.location_id.id)+'_'+str(roperation.location_id.id)
            if mkey in movedict:
                movedict[mkey]['product_qty'] += label.product_qty
            else:
                movedict[mkey] = {
                    'product_id': self.product_id.id, 'product_uom': self.product_uom.id, 'product_lot': label.product_lot.id,
                    'origin_order': self.origin_order, 'receipt_type': self.receipt_type, 'partner_id': self.receipt_id.partner_id and self.receipt_id.partner_id.id,
                    'receipt_user': self.env.user.id, 'location_src_id': label.location_id.id, 'location_dest_id': roperation.location_id.id, 'product_qty': label.product_qty, 'company_id': self.company_id.id
                }
            labelvals = {'locked': False, 'locked_order': False, 'prioritized': manreturn}
            labelvals.update({'onshelf_time': push_time, 'onshelf_date': push_date, 'location_id': roperation.location_id.id})
            label.write(labelvals)
            receiptlabels |= roperation.rlabel_id
        # 收货清单可上架标记更更新为False
        receiptlabels.write({'pushable': False})
        # 记录原料最近一次存放位置，为下次上架提供推荐库位
        for pkey, pval in productdict.items():
            product_id, location_id = pval['product'], pval['location_id']
            product_id.write({'push_location': location_id})
        # 更新收货单信息
        receiptvals['operation_lines'] = operationlines
        receiptvals['move_lines'] = [(0, 0, mval) for mkey, mval in movedict.items()]
        receiptvals['receipt_lines'] = [(1, self.id, {'receipt_qty': self.receipt_qty+self.doing_qty, 'doing_qty': 0.0})]
        self.receipt_id.write(receiptvals)
        # 判断当前收货明细是否结束收货
        labelist = self.env['aas.stock.receipt.label'].search([('line_id', '=', self.id), ('pushable', '=', True)])
        if not labelist or len(labelist) <= 0:
            self.write({'state': 'done'})
        # 判断当前收货单是否结束收货
        templabels = self.env['aas.stock.receipt.label'].search([('receipt_id', '=', self.receipt_id.id), ('pushable', '=', True)])
        if not templabels or len(templabels) <= 0:
            self.receipt_id.write({'state': 'done', 'done_time': fields.Datetime.now()})


    @api.multi
    def action_note(self):
        """
        添加备注
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.stock.receipt.note.wizard'].create({
            'receipt_id': self.receipt_id.id, 'receipt_line': self.id
        })
        view_form = self.env.ref('aas_wms.view_form_aas_stock_receipt_note_wizard')
        return {
            'name': u"收货备注",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.stock.receipt.note.wizard',
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
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'收货标签', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品名称', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'产品单位')
    origin_order = fields.Char(string=u'来源单据', copy=False, default='')
    checked = fields.Boolean(string=u'是否作业', default=False, copy=False)
    pushable = fields.Boolean(string=u'是否可以上架', default=True, copy=False)
    label_current = fields.Boolean(string=u'是否新建', default=False, copy=False)
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    label_location = fields.Many2one(comodel_name='stock.location', string=u'来源库位', ondelete='restrict')
    product_qty = fields.Float(string=u'产品数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)

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
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品名称', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'产品单位')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    push_time = fields.Datetime(string=u'上架时间')
    push_onshelf = fields.Boolean(string=u'是否上架', default=False, copy=False)
    location_id = fields.Many2one(comodel_name='stock.location', string=u'上架库位')
    push_user = fields.Many2one(comodel_name='res.users', string=u'上架员工', ondelete='restrict')
    product_qty = fields.Float(string=u'上架数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('uniq_receipt_rlabel', 'unique (receipt_id, rlabel_id)', u'请不要重复添加标签！')
    ]

    @api.onchange('rlabel_id')
    def action_change_label(self):
        if self.rlabel_id:
            self.product_id, self.product_uom = self.rlabel_id.product_id.id, self.rlabel_id.product_uom.id
            self.product_lot, self.product_qty = self.rlabel_id.product_lot.id, self.rlabel_id.label_id.product_qty
        else:
            self.product_id, self.product_uom, self.product_lot, self.product_qty = False, False, False, 0.0

    @api.model
    def action_before_create(self, vals):
        rlabel = self.env['aas.stock.receipt.label'].browse(vals.get('rlabel_id'))
        vals.update({
            'label_id': rlabel.label_id.id,
            'receipt_id': rlabel.receipt_id.id, 'line_id': rlabel.line_id.id,
            'product_id': rlabel.product_id.id, 'product_lot': rlabel.product_lot.id,
            'product_qty': rlabel.label_id.product_qty, 'product_uom': rlabel.product_uom.id
        })

    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        record = super(AASStockReceiptOperation, self).create(vals)
        record.action_after_create()
        return record

    @api.one
    def action_after_create(self):
        rlabel, rline, receipt = self.rlabel_id, self.line_id, self.receipt_id
        label, location = rlabel.label_id, self.location_id
        if label.qualified and location.mrblocation:
            raise UserError(u'合格品请不要放置在MRB库位上！')
        elif not label.qualified and not location.mrblocation:
            raise UserError(u'不合格品请放置在MRB库位上！')
        receiptvals = {'label_lines': [(1, rlabel.id, {'checked': True})]}
        if receipt.state!='receipt':
            receiptvals['state'] = 'receipt'
        lineval = {'doing_qty': rline.doing_qty + rlabel.product_qty}
        if rline.state!='receipt':
            lineval['state'] = 'receipt'
        receiptvals['receipt_lines'] = [(1, rline.id, lineval)]
        receipt.write(receiptvals)


    @api.multi
    def unlink(self):
        rlabels = self.env['aas.stock.receipt.label']
        for record in self:
            if record.push_onshelf:
                raise UserError(u'标签%s已上架，不可以删除！'% record.rlabel_id.label_id.name)
            rlabels |= record.rlabel_id
        result = super(AASStockReceiptOperation, self).unlink()
        rlabels.write({'checked': False})
        linesdict = {}
        for rlabel in rlabels:
            receipt, rline = rlabel.receipt_id, rlabel.line_id
            if not receipt.operation_lines or len(receipt.operation_lines) <= 0:
                rstate = 'confirm' if receipt.receipt_type!='purchase' else 'checked'
                receipt.write({'state': rstate})
            lkey = 'line_'+str(rline.id)
            if lkey in linesdict:
                linesdict[lkey]['doing_qty'] -= rlabel.product_qty
            else:
                linesdict[lkey] = {'line': rline, 'doing_qty': rline.doing_qty - rlabel.product_qty}
        for tkey, tval in linesdict.items():
            rline, doing_qty = tval['line'], tval['doing_qty']
            linvals = {'doing_qty': doing_qty}
            if float_compare(doing_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                linvals['doing_qty'] = 0.0
                linvals['state'] = 'confirm' if rline.receipt_type!='purchase' else 'checked'
            rline.write(linvals)
        return result



class AASStockReceiptMove(models.Model):
    _name = 'aas.stock.receipt.move'
    _description = u'执行明细'
    _order = "id desc"

    receipt_id = fields.Many2one(comodel_name='aas.stock.receipt', string=u'收货单', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品名称', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'产品单位')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'产品批次', ondelete='restrict')
    origin_order = fields.Char(string=u'来源单据', copy=False)
    receipt_note = fields.Text(string=u'备注')
    receipt_type = fields.Selection(selection=RECEIPT_TYPE, string=u'收货类型')
    receipt_date = fields.Date(string=u'收货日期', default=fields.Date.today)
    receipt_time = fields.Datetime(string=u'收货时间', default=fields.Datetime.now)
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'业务伙伴', ondelete='restrict')
    receipt_user = fields.Many2one(comodel_name='res.users', string=u'收货员工', ondelete='restrict')
    location_src_id = fields.Many2one(comodel_name='stock.location', string=u'来源库位', ondelete='restrict')
    location_dest_id = fields.Many2one(comodel_name='stock.location', string=u'目标库位', ondelete='restrict')
    product_qty = fields.Float(string=u'收货数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)

    @api.model
    def create(self, vals):
        record = super(AASStockReceiptMove, self).create(vals)
        record.action_stock_move()
        return record

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


class AASStockReceiptNote(models.Model):
    _name = 'aas.stock.receipt.note'
    _description = u'收货备注清单'
    _order = "id desc"

    receipt_id = fields.Many2one(comodel_name='aas.stock.receipt', string=u'收货单', ondelete='cascade')
    receipt_line = fields.Many2one(comodel_name='aas.stock.receipt.line', string=u'收货明细', ondelete='cascade')
    action_user = fields.Many2one(comodel_name='res.users', string=u'备注用户', default=lambda self: self.env.user)
    action_time = fields.Datetime(string=u'时间', default=fields.Datetime.now, copy=False)
    action_note = fields.Text(string=u'备注内容')
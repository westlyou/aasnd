# -*-  coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

class AASMESLabel(models.Model):
    _name = 'aas.mes.label'
    _description = 'AAS MES Label'
    _order = 'id desc'

    name = fields.Char(string=u'名称', copy=False)
    state = fields.Selection(selection=[('draft', u'草稿'), ('done', u'完成')], string=u'状态', default='draft')
    location_id = fields.Many2one(comodel_name='stock.location',string=u'库位', ondelete='restrict')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'操作员工', ondelete='restrict')
    operator_id = fields.Many2one(comodel_name='res.users', string=u'制单人', default=lambda self:self.env.user)
    operation_time = fields.Datetime(string=u'制单时间', default=fields.Datetime.now, copy=False)
    product_lines = fields.One2many(comodel_name='aas.mes.label.line', inverse_name='mlabel_id', string=u'产品明细')

    @api.model
    def create(self,vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('aas.mes.label')
        return super(AASMESLabel, self).create(vals)


    @api.one
    def action_create_label(self):
        if not self.product_lines or len(self.product_lines) <= 0:
            raise UserError(u'请先添加产品明细')
        for record in self.product_lines:
            if record.label_id:
                continue
            product = record.product_id
            label = self.env['aas.product.label'].create({
                'location_id': self.location_id.id,
                'product_id': product.id, 'product_uom': product.uom_id.id,
                'product_lot': record.product_lot.id, 'product_qty': record.product_qty
            })
            record.write({'label_id': label.id})
        self.write({'state': 'done'})

    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(u'%s已完成不可以删除'% record.name)
        return super(AASMESLabel, self).unlink()


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
            tempdomain = [('id', 'in', ids)]
        else:
            tempdomain = domain
        mlabels = self.env['aas.mes.label'].search(tempdomain)
        if not mlabels or len(mlabels) <= 0:
            values.update({'success': False, 'message': u'未搜索到需要打印标签的收货单！'})
            return values
        labelids = []
        for mlabel in mlabels:
            if not mlabel.product_lines or len(mlabel.product_lines) <= 0:
                continue
            for mlline in mlabel.product_lines:
                if not mlline.label_id:
                    continue
                labelids.append(mlline.label_id.id)
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

class AASMESLabelLine(models.Model):
    _name = 'aas.mes.label.line'
    _description = 'AAS MES Label Line'
    _order = 'id desc'

    mlabel_id = fields.Many2one(comodel_name='aas.mes.label',string=u'现场标签', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product',string=u'产品', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'))
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')

    @api.one
    @api.constrains('product_qty')
    def action_constrains_product_qty(self):
        if float_compare(self.product_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise ValidationError(u'%s数量必须大于零'% self.product_id.default_code)

    @api.model
    def create(self,vals):
        record = super(AASMESLabelLine, self).create(vals)
        domain = [('location_id', '=', record.mlabel_id.location_id.id)]
        domain += [('product_id', '=', record.product_id.id), ('lot_id', '=', record.product_lot.id)]
        stocklist = self.env['stock.quant'].search(domain)
        if not stocklist or len(stocklist) <= 0:
            raise UserError(u'系统中%s没有库存！'% record.product_id.default_code)
        stock_qty = sum([tstock.qty for tstock in stocklist])
        if float_compare(record.product_qty, stock_qty, precision_rounding=0.000001) > 0.0:
            raise UserError(u'系统中%s库存只有%s！'% (record.product_id.default_code, stock_qty))
        return record


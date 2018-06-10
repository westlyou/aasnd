# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-10-12 10:31
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

REJECTTYPES = [('produce', u'产线'), ('oqcchecking', 'OQC')]

SERIALSTATES = [('draft', u'草稿'), ('normal', u'正常'), ('rework', u'返工'), ('shipped', u'已发货')]

class AASMESSerialnumber(models.Model):
    _name = 'aas.mes.serialnumber'
    _description = 'AAS MES Serialnumber'
    _order = 'id desc'

    name = fields.Char(string=u'名称', required=True, index=True)
    regular_code = fields.Char(string=u'规则编码', copy=False)
    sequence = fields.Integer(string=u'规则序号', copy=False)
    sequence_code = fields.Char(string=u'序列编码', copy=False)
    stocked = fields.Boolean(string=u'已库存', default=False, copy=False)
    qualified = fields.Boolean(string=u'合格的', default=True, copy=False)
    operation_date = fields.Char(string=u'生成日期', copy=False)
    operation_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    state = fields.Selection(selection=SERIALSTATES, string=u'状态', default='draft', copy=False)
    operator_id = fields.Many2one('res.users', string=u'操作人', ondelete='restrict', default=lambda self: self.env.user)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    internal_product_code = fields.Char(string=u'产品编码', copy=False, help=u'在公司内部的产品编码')
    customer_product_code = fields.Char(string=u'客户编码', copy=False, help=u'在客户方的产品编码')
    reworksource = fields.Selection(selection=REJECTTYPES, string=u'返工来源', default='produce')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'操作员工', ondelete='restrict')
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'操作设备', ondelete='restrict')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', index=True)
    printed = fields.Boolean(string=u'已打印', default=False, copy=False)
    consumed = fields.Boolean(string=u'已消耗', default=False, copy=False, help=u'是否已消耗原材料')
    reworked = fields.Boolean(string=u'是否返工', default=False, copy=False)
    rework_count = fields.Integer(string=u'返工次数', default=0)

    lastone_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'上一个', index=True, ondelete='restrict')
    output_time = fields.Datetime(string=u'产出时间', copy=False)
    output_internal = fields.Float(string=u'产出间隔', default=0.0, help=u'上一次产出的序列号与本次产出的时间间隔')
    outputuser_id = fields.Many2one(comodel_name='res.users', string=u'产出用户', index=True, ondelete='restrict')
    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'产出工单', index=True, ondelete='restrict')
    production_id = fields.Many2one(comodel_name='aas.production.product', string=u'产出记录', index=True)
    traced = fields.Boolean(string=u'已被追溯关联', default=False, copy=False)
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', index=True, ondelete='restrict')
    operation_id = fields.Many2one(comodel_name='aas.mes.operation', string=u'操作记录', index=True, ondelete='restrict')
    badmode_name = fields.Char(string=u'不良名称', copy=False, help=u'最近一次上报不良的不良模式名称')

    rework_lines = fields.One2many(comodel_name='aas.mes.rework', inverse_name='serialnumber_id', string=u'返工清单')
    operation_lines = fields.One2many(comodel_name='aas.mes.operation.record', inverse_name='serialnumber_id', string=u'操作清单')

    _sql_constraints = [
        ('uniq_name', 'unique (name)', u'序列号的名称不可以重复！')
    ]


    @api.model
    def action_print_label(self, printer_id, ids=[], domain=[]):
        values = {'success': True, 'message': ''}
        printer = self.env['aas.label.printer'].browse(printer_id)
        if not printer.field_lines or len(printer.field_lines) <= 0:
            values.update({'success': False, 'message': u'请联系管理员标签打印未指定具体打印内容！'})
            return values
        values.update({'printer': printer.name, 'serverurl': printer.serverurl})
        field_list = [fline.field_name for fline in printer.field_lines]
        if ids and len(ids) > 0:
            labeldomain = [('id', 'in', ids)]
        else:
            labeldomain = domain
        if not labeldomain or len(labeldomain) <= 0:
            return {'success': False, 'message': u'您可能已经选择了所有标签或未选择任何标签，请选中需要打印的标签！'}
        records = self.search_read(domain=labeldomain, fields=field_list)
        if not records or len(records) <= 0:
            values.update({'success': False, 'message': u'未搜索到需要打印的标签！'})
            return values
        records = printer.action_correct_records(records)
        values['records'] = records
        return values

    @api.model
    def create(self, vals):
        vals['operation_date'] = fields.Datetime.to_china_today()
        record = super(AASMESSerialnumber, self).create(vals)
        record.action_after_create()
        return record


    @api.one
    def action_after_create(self):
        operation = self.env['aas.mes.operation'].create({
            'mesline_id': False if not self.mesline_id else self.mesline_id.id,
            'serialnumber_id': self.id, 'serialnumber_name': self.name,
            'product_id': self.product_id.id, 'internal_product_code': self.internal_product_code,
            'customer_product_code': self.customer_product_code, 'operation_date': self.operation_date
        })
        barcoderecord = self.env['aas.mes.operation.record'].create({
            'operation_id': operation.id, 'operator_id': self.operator_id.id,
            'operate_type': 'newbarcode', 'employee_id': self.employee_id.id, 'equipment_id': self.equipment_id.id
        })
        operation.write({'barcode_create': True, 'barcode_record_id': barcoderecord.id})
        self.write({'operation_id': operation.id})

    @api.one
    def action_functiontest(self):
        toperation = self.env['aas.mes.operation'].search([('serialnumber_id', '=', self.id)], limit=1)
        trecord = self.env['aas.mes.operation.record'].create({
            'operation_id': toperation.id, 'operate_result': 'PASS', 'operate_type': 'functiontest'
        })
        toperation.write({'function_test': True, 'functiontest_record_id': trecord.id})
        # self.write({'workorder_id': 7014})


    @api.multi
    def action_show_operationlist(self):
        """
        显示操作记录
        :return:
        """
        self.ensure_one()
        operation = self.env['aas.mes.operation'].search([('serialnumber_id', '=', self.id)], limit=1)
        view_form = self.env.ref('aas_mes.view_form_aas_mes_operation')
        return {
            'name': u"操作记录",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.operation',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'self',
            'res_id': operation.id,
            'context': self.env.context
        }

    @api.multi
    def action_gp12packing(self, mesline):
        """
        GP12打包标签
        :param mesline:
        :return:
        """
        values = {'success': True, 'message': '', 'label_id': '0', 'label_name': ''}
        firstserial = self[0]
        ttoday = fields.Datetime.to_china_today()
        lotcode = ttoday.replace('-', '')
        outputlocation = mesline.location_production_id
        product, product_qty = firstserial.product_id, len(self)
        productlot = self.env['stock.production.lot'].action_checkout_lot(product.id, lotcode)
        # 新建库存标签
        label = self.env['aas.product.label'].create({
            'product_id': product.id, 'product_lot': productlot.id, 'product_qty': product_qty,
            'location_id': outputlocation.id, 'company_id': self.env.user.company_id.id, 'stocked': True,
            'customer_code': firstserial.customer_product_code
        })
        product_code, customer_code = product.default_code, firstserial.customer_product_code
        # 新建GP12成品标签
        self.env['aas.mes.production.label'].create({
            'label_id': label.id, 'product_id': product.id,  'product_qty': product_qty,
            'lot_id': productlot.id, 'product_code': product_code, 'customer_code': customer_code,
            'operator_id': self.env.user.id, 'action_date': ttoday, 'location_id': outputlocation.id,
            'isserialnumber': True
        })
        # 更新产线成品库存
        srclocation = self.env.ref('stock.location_production')
        label.action_stock(srclocation.id)
        # 更新序列号上标签和批次信息
        self.write({'label_id': label.id, 'product_lot': label.product_lot.id})
        operationlist = self.env['aas.mes.operation'].search([('serialnumber_id', 'in', self.ids)])
        if operationlist and len(operationlist) > 0:
            operationlist.write({'labeled': True, 'label_id': label.id})
        # 更新产出信息上的批次信息
        productionlist = self.env['aas.production.product'].search([('serialnumber_id', 'in', self.ids)])
        if productionlist and len(productionlist) > 0:
            productionlist.write({'product_lot': productlot.id})
        values.update({'label_id': label.id, 'label_name': label.name})
        return values



class AASProductLabelSerialnumber(models.Model):
    _name = 'aas.product.label.serialnumber'
    _description = 'AAS Product Label Serialnumber'
    _order = 'bind_time desc'

    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', index=True)
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', index=True)
    bind_time = fields.Datetime(string=u'绑定时间', default=fields.Datetime.now, copy=False)
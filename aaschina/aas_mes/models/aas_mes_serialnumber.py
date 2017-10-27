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


SERIALSTATES = [('draft', u'草稿'), ('normal', u'正常'), ('rework', u'返工'), ('shipped', u'已发货')]

class AASMESSerialnumber(models.Model):
    _name = 'aas.mes.serialnumber'
    _description = 'AAS MES Serialnumber'

    name = fields.Char(string=u'名称', required=True, copy=False)
    regular_code = fields.Char(string=u'规则编码', copy=False)
    sequence = fields.Integer(string=u'规则序号', copy=False)
    sequence_code = fields.Char(string=u'序列编码', copy=False)
    used = fields.Boolean(string=u'已使用', default=False, copy=False)
    qualified = fields.Boolean(string=u'合格的', default=True, copy=False)
    operation_date = fields.Char(string=u'生成日期', copy=False)
    operation_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    state = fields.Selection(selection=SERIALSTATES, string=u'状态', default='draft', copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'操作人', ondelete='restrict', default=lambda self: self.env.user)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    internal_product_code = fields.Char(string=u'产品编码', copy=False, help=u'在公司内部的产品编码')
    customer_product_code = fields.Char(string=u'客户编码', copy=False, help=u'在客户方的产品编码')
    reworked = fields.Boolean(string=u'是否返工', default=False, copy=False)
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'操作员工', ondelete='restrict')
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'操作设备', ondelete='restrict')

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
        vals['operation_date'] = fields.Datetime.to_timezone_string(fields.Datetime.now(), 'Asia/Shanghai')[0:10]
        record = super(AASMESSerialnumber, self).create(vals)
        record.action_after_create()
        return record


    @api.one
    def action_after_create(self):
        operation = self.env['aas.mes.operation'].create({'serialnumber_id': self.id, 'serialnumber_name': self.name})
        barcoderecord = self.env['aas.mes.operation.record'].create({
            'operation_id': operation.id, 'operator_id': self.user_id.id,
            'operate_type': 'newbarcode', 'employee_id': self.employee_id.id, 'equipment_id': self.equipment_id.id
        })
        operation.write({'barcode_create': True, 'barcode_record_id': barcoderecord.id})
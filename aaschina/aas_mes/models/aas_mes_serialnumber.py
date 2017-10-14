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

class AASMESSerialnumber(models.Model):
    _name = 'aas.mes.serialnumber'
    _description = 'AAS MES Serialnumber'

    name = fields.Char(string=u'名称', required=True, copy=False)
    regular_code = fields.Char(string=u'规则编码', copy=False)
    sequence = fields.Integer(string=u'规则序号', copy=False)
    used = fields.Boolean(string=u'已使用', default=False, copy=False)
    action_date = fields.Char(string=u'生成日期', copy=False)
    create_time = fields.Datetime(string=u'创建时间', default=fields.Datetime.now, copy=False)
    user_id = fields.Many2one(comodel_name='res.users', string=u'创建人', ondelete='restrict', default=lambda self: self.env.user)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    internal_product_code = fields.Char(string=u'产品编码', copy=False, help=u'在公司内部的产品编码')
    customer_product_code = fields.Char(string=u'客户编码', copy=False, help=u'在客户方的产品编码')

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
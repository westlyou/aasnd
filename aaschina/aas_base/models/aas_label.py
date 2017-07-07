# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class AASLabelPrinter(models.Model):
    _name = 'aas.label.printer'
    _description = u'标签打印机'

    name = fields.Char(string=u'名称', copy=False)
    host = fields.Char(string=u'主机', help=u'打印机IP地址')
    port = fields.Integer(string=u"端口", default=80, help=u'打印机服务端口')
    completeurl = fields.Char(string=u'打印服务', help=u'打印机服务请求完整的URL')
    model_id = fields.Many2one(comodel_name='ir.model', string=u'标签对象', ondelete='set null')
    field_lines = fields.One2many(comodel_name='aas.label.printer.lines', inverse_name='printer_id', string=u'打印明细')

    _sql_constraints = [
        ('uniq_name', 'unique (name)', u'标签打印机的名称不能重复！')
    ]

    @api.multi
    def action_correct_records(self, records):
        """
        修正记录，删除id字段，many2one字段只取名称
        :param records:
        :return:
        """
        self.ensure_one()
        if not records or len(records) <= 0:
            return []
        def updaterecord(record):
            del record['id']
            for rkey, rval in record.items():
                if isinstance(rval, tuple):
                    record[rkey] = rval[1]
            return record
        trecords = map(updaterecord, records)
        return trecords


class AASLabelPrinterLines(models.Model):
    _name = 'aas.label.printer.lines'
    _description = u'标签打印明细'

    field_name = fields.Char(string=u'字段名称')
    field_type = fields.Char(string=u'字段类型')
    print_name = fields.Char(string=u'打印名称', required=True)
    field_id = fields.Many2one(comodel_name='ir.model.fields', string=u'字段', ondelete='cascade', required=True)
    printer_id = fields.Many2one(comodel_name='aas.label.printer', string=u'打印机', ondelete='cascade', required=True)

    @api.onchange('field_id')
    def change_field(self):
        if self.field_id:
            self.field_name = self.field_id.name
            self.print_name = self.field_id.name
            self.field_type = self.field_id.ttype

    @api.model
    def create(self, vals):
        tfield = self.env['ir.model.fields'].browse(vals.get('field_id'))
        vals.update({'field_name': tfield.name, 'field_type': tfield.ttype})
        return super(AASLabelPrinterLines, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('field_id'):
            tfield = self.env['ir.model.fields'].browse(vals.get('field_id'))
            vals.update({'field_name': tfield.name, 'field_type': tfield.ttype})
        return super(AASLabelPrinterLines, self).write(vals)


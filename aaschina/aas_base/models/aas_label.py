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

    name = fields.Char(string=u'名称')
    host = fields.Char(string=u'主机', default='127.0.0.1', help=u'打印机IP地址')
    port = fields.Integer(string=u"端口", default=80, help=u'打印机服务端口')
    serverurl = fields.Char(string=u'打印服务', help=u'打印机服务请求完整的URL', compute='_compute_serverurl', store=True)
    model_id = fields.Many2one(comodel_name='ir.model', string=u'标签对象', ondelete='set null', copy=True)
    field_lines = fields.One2many('aas.label.printer.lines', inverse_name='printer_id', string=u'打印明细', copy=True)

    _sql_constraints = [
        ('uniq_name', 'unique (name)', u'标签打印机的名称不能重复！')
    ]

    @api.depends('host', 'port')
    def _compute_serverurl(self):
        for record in self:
            port = '80' if not record.port else str(record.port)
            record.serverurl = record.host+':'+port

    @api.model
    def create(self, vals):
        if not vals.get('field_lines'):
            raise UserError(u'请先添加需要打印的字段！')
        return super(AASLabelPrinter, self).create(vals)

    @api.one
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.setdefault('name', "%s (copy)" % (self.name or ''))
        return super(AASLabelPrinter, self).copy(default)


    @api.multi
    def action_correct_records(self, records):
        """
        修正记录，删除id字段，many2one字段只取名称
        :param records:
        :return:
        """
        self.ensure_one()
        fieldsdict, changenamedict = {}, {}
        for fline in self.field_lines:
            fieldsdict[fline.field_name] = {'field_name': fline.field_name, 'field_type': fline.field_type, 'print_name': fline.print_name}
            if fline.field_name != fline.print_name:
                changenamedict[fline.field_name] = fline.print_name
        if not records or len(records) <= 0:
            return []
        def updaterecord(record):
            del record['id']
            for rkey, rval in record.items():
                if rval and fieldsdict[rkey]['field_type'] == 'many2one':
                    record[rkey] = rval[1]
                elif rval and fieldsdict[rkey]['field_type'] == 'datetime':
                    record[rkey] = fields.Datetime.to_timezone_string(rval, 'Asia/Shanghai')
                elif not rval and fieldsdict[rkey]['field_type'] != 'boolean':
                    record[rkey] = ''
                elif rkey == 'qualified':
                    record[rkey] = u'合格' if rval else u'不合格'
            return record
        trecords = map(updaterecord, records)
        def updatedictname(record):
            for dkey, dval in changenamedict.items():
                if dkey in record:
                    record[dval] = record[dkey]
                    del record[dkey]
            return record
        if changenamedict and len(changenamedict) > 0:
            trecords = map(updatedictname, trecords)
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


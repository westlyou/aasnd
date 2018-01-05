# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-8-17 09:42
"""

from odoo import api, fields, models, tools, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

EQUIPMENTSTATES = [('normal', u'正常'), ('test', u'测试中'), ('produce', u'生产中'), ('repair', u'维修中'), ('maintain', u'保养中'), ('scrap', u'报废')]

EQUIPMENTPRIORITY = [('useless', u'无用设备'), ('assist', u'辅助设备'), ('common', u'普通设备'), ('important', u'重要设备'), ('precise', u'精密设备'), ('secret', u'机密设备')]

class AASEquipmentCategory(models.Model):
    _name = 'aas.equipment.category'
    _description = 'AAS Equipment Category'

    name = fields.Char(string=u'名称', copy=False)
    company = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('uniq_name', 'unique (name)', u'请不要重复添加同一个名称！')
    ]


class AASEquipmentEquipment(models.Model):
    _name = 'aas.equipment.equipment'
    _description = 'AAS Equipment Equipment'


    name = fields.Char(string=u'名称', index=True)
    code = fields.Char(string=u'编码', index=True)
    barcode = fields.Char(string=u'条码', compute='_compute_barcode', store=True, index=True)
    active = fields.Boolean(string=u'是否有效', default=True)
    supplier = fields.Many2one(comodel_name='res.partner', string=u'供应商')
    responsible = fields.Many2one(comodel_name='res.users', string=u'责任人')
    category = fields.Many2one(comodel_name='aas.equipment.category', string=u'类别')
    purchase_date = fields.Date(string=u'采购日期', default=fields.Date.today, copy=False)
    state_color = fields.Integer(string=u'状态颜色值', compute='_compute_state_color', store=True)
    state = fields.Selection(selection=EQUIPMENTSTATES, string=u'状态', default='normal', readonly=True)
    priority = fields.Selection(EQUIPMENTPRIORITY, string=u'设备等级', index=True, default='common')

    image = fields.Binary("Image")
    image_small = fields.Binary("Small-sized image")
    image_medium = fields.Binary("Medium-sized image")
    company = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('uniq_code', 'unique (code)', u'设备编码已存在，请不要重复添加！')
    ]

    @api.multi
    def name_get(self):
        return [(record.id, '%s[%s]' % (record.name, record.code)) for record in self]

    @api.model
    def create(self, vals):
        tools.image_resize_images(vals)
        return super(AASEquipmentEquipment, self).create(vals)


    @api.depends('state')
    def _compute_state_color(self):
        statedict = {'normal': 1, 'test': 2, 'produce': 3, 'repair': 4, 'maintain': 5, 'scrap': 6}
        for record in self:
            if (not record.state) or (record.state not in statedict):
                record.state_color = 1
            else:
                record.state_color = statedict[record.state]


    @api.multi
    @api.depends('code')
    def _compute_barcode(self):
        for record in self:
            record.barcode = 'AK'+record.code


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
            return {'success': False, 'message': u'您可能已经选择了所有设备或未选择任何设备，请选中需要打印标签的设备！'}
        records = self.search_read(domain=labeldomain, fields=field_list)
        if not records or len(records) <= 0:
            values.update({'success': False, 'message': u'未搜索到需要打印的设备！'})
            return values
        records = printer.action_correct_records(records)
        values['records'] = records
        return values


    @api.multi
    def action_show_datalist(self):
        """显示设备数据
        :return:
        """
        self.ensure_one()
        equipment_code = self.code
        view_form = self.env.ref('aas_equipment.view_form_aas_equipment_data')
        view_tree = self.env.ref('aas_equipment.view_tree_aas_equipment_data')
        return {
            'name': u"设备数据",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'aas.equipment.data',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'target': 'self',
            'context': self.env.context,
            'domain': "[('app_code','=','"+equipment_code+"')]"
        }
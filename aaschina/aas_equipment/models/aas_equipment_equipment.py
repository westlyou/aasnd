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


    name = fields.Char(string=u'名称')
    code = fields.Char(string=u'编码')
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
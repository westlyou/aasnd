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
    product_lines = fields.One2many(comodel_name='aas.mes.label.line', inverse_name='mlabel_id', string=u'标签明细')


class AASMESLabelLine(models.Model):
    _name = 'aas.mes.label.line'
    _description = 'AAS MES Label Line'
    _order = 'id desc'

    mlabel_id = fields.Many2one(comodel_name='aas.mes.label',string=u'现场标签', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product',string=u'产品', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'))
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
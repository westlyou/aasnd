# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

LABEL_STATE = [('draft', u'草稿'), ('normal', u'正常'), ('frozen', u'冻结'), ('over', u'消亡')]

class AASProductLabel(models.Model):
    _name = 'aas.product.label'
    _description = u'产品标签'

    name = fields.Char(string=u'名称', copy=False)
    barcode = fields.Char(string='Barcode', copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', required=True, ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', required=True, ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=1.0)
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='set null')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')
    state = fields.Selection(selection=LABEL_STATE, string=u'状态', default='normal', copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null')

    date_code = fields.Char(string='DateCode')
    qualified = fields.Boolean(string=u'是否合格', default=True)
    stocked = fields.Boolean(string=u'是否库存', default=False, help=u'是否已经进入库存')
    customer_code = fields.Char(string=u'客户编码', help=u'产品在客户方的编码')
    origin_order = fields.Char(string=u'来源单据')
    pack_user = fields.Char(string=u'包装员工')
    prioritized = fields.Boolean(string=u'优先处理', default=False)
    locked = fields.Boolean(string=u'锁定', default=False)
    locked_order = fields.Char(string=u'锁定单据', help=u'标签是因为此单据而锁定')
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'业务伙伴', ondelete='set null')

    parent_id = fields.Many2one(comodel_name='aas.product.label', string=u'父标签', ondelete='restrict', copy=False)
    parent_left = fields.Integer(string='Left Parent', select=1)
    parent_right = fields.Integer(string='Right Parent', select=1)
    child_lines = fields.One2many(comodel_name='aas.product.label', inverse_name='parent_id', string=u'子标签')
    origin_id = fields.Many2one(comodel_name='aas.product.label', string=u'源标签', ondelete='set null', help=u'当前标签由拆解而得的源头标签')
    origin_lines = fields.One2many(comodel_name='aas.product.label', inverse_name='origin_id', string=u'拆解标签')

    onshelf_time = fields.Datetime(string=u'上架时间', help=u'货物到库存库位上架的时间')
    onshelf_date = fields.Date(string=u'上架日期', help=u'货物上架日期，拣货时排序使用')
    offshelf_time = fields.Datetime(string=u'下架时间', help=u'货物从库存库位下架的时间')
    stock_date = fields.Date(string=u'库龄日期', help=u'库龄时间段，货物允许放在仓库的最后日期')
    warranty_date = fields.Date(string=u'质保日期', help=u'质保时间段，货物最后有效的日期，过期将自动冻结')

    journal_lines = fields.One2many(comodel_name='aas.product.label.journal', inverse_name='label_id', string=u'查存卡')


# 标签流水帐  查存卡
class AASProductLabelJournal(models.Model):
    _name = "aas.product.label.journal"
    _description = u"标签查存卡"

    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='cascade')
    record_time = fields.Datetime(string=u'时间', required=True, default=fields.Datetime.now)
    location_src_id = fields.Many2one(comodel_name='stock.location', string=u'发出', ondelete='set null')
    location_dest_id = fields.Many2one(comodel_name='stock.location', string=u'收入', ondelete='set null')
    journal_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    balance_qty = fields.Float(string=u'结存', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    consume_order = fields.Char(string=u'操作单据', copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null')





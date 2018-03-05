# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-3-5 09:59
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


OQCCHECKSTATES = [('draft', u'草稿'), ('confirm', u'确认'), ('checking', u'检验中'), ('done', u'完成')]

class AASQualityOQCOrder(models.Model):
    _name = 'aas.quality.oqcorder'
    _description = 'AAS Quality OQCOrder'

    name = fields.Char(string=u'名称', copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_qty = fields.Float(string=u'报检数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    commit_user = fields.Many2one(comodel_name='res.users', string=u'报检人员', ondelete='restrict')
    commit_time = fields.Datetime(string=u'报检时间', default=fields.Datetime.now, copy=False)
    remark = fields.Text(string=u'备注', copy=False)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    label_lines = fields.One2many(comodel_name='aas.quality.oqcorder.label', inverse_name='order_id', string=u'标签清单')



class AASQualityOQCOrder(models.Model):
    _name = 'aas.quality.oqcorder.label'
    _description = 'AAS Quality OQCOrder Label'

    order_id = fields.Many2one(comodel_name='aas.quality.oqcorder', string='Order', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    checked = fields.Boolean(string=u'是否检验', default=False, copy=False)
    checker_id = fields.Many2one(comodel_name='res.users', string=u'检验员', ondelete='restrict')
    checking_time = fields.Datetime(string=u'检验时间', copy=False)
    qualified = fields.Boolean(string=u'是否合格', default=False, copy=False)


    @api.one
    def action_checking(self, qualified=False):
        """OQC检测判定
        :param qualified:
        :return:
        """
        self.write({
            'checked': True, 'checker_id': self.env.user.id,
            'checking_time': fields.Datetime.now(), 'qualified': qualified
        })
        if qualified:
            self.label_id.write({'oqcpass': True})
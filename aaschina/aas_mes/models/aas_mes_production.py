# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-1-6 16:03
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


# 成品标签记录
class AASMESProduction(models.Model):
    _name = 'aas.mes.production.label'
    _description = 'AAS MES Production Label'

    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', index=True)
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', index=True)
    action_date = fields.Char(string=u'日期', copy=False, index=True)
    action_time = fields.Datetime(string=u'时间', default=fields.Datetime.now, copy=False)
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工')
    operator_id = fields.Many2one(comodel_name='res.users', string=u'用户')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)


    @api.model
    def action_gp12_dolabel(self, product_id, productlot_id, product_qty, location_id, customer_code=False):
        label = self.env['aas.product.label'].create({
            'product_id': product_id, 'product_lot': productlot_id, 'product_qty': product_qty, 'stocked': True,
            'location_id': location_id, 'company_id': self.env.user.company_id.id, 'customer_code': customer_code
        })
        chinadate = fields.Datetime.to_china_string(fields.Datetime.now())[0:10]
        self.env['aas.mes.production.label'].create({
            'product_id': product_id, 'label_id': label.id, 'product_qty': product_qty,
            'operator_id': self.env.user.id, 'action_date': chinadate
        })
        return label
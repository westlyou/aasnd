# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-4-25 13:19
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

class AASProductPackage(models.Model):
    _name = 'aas.product.package'
    _description = u'产品包装方式'

    name = fields.Char(string=u'名称', required=True, copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    customer_id = fields.Many2one(comodel_name='res.partner', string=u'客户', domain=[('customer', '=', True)], ondelete='restrict')

    _sql_constraints = [
        ('uniq_name', 'unique (name, product_id, customer_id)', u'请不要重复添加同一个记录！')
    ]


    @api.model
    def action_loading_package(self, product_code):
        """加载产品包装方式
        :param product_code:
        :return:
        """
        values = {'success': True, 'message': '', 'packagelist': []}
        if not product_code:
            return values
        product_code = product_code.strip()
        if not product_code:
            return values
        product = self.env['product.product'].search([('default_code', '=', product_code)], limit=1)
        if not product:
            values.update({'success': False, 'message': u'请检查料号是否设置正确！'})
            return values
        packagelist = self.env['aas.product.package'].search([('product_id', '=', product.id)])
        if packagelist and len(packagelist) > 0:
            values['packagelist'] = [{'package_id': package.id, 'package_name': package.name} for package in packagelist]
        return values

# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-6-4 14:34
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError
from odoo.tools.sql import drop_view_if_exists

import logging

_logger = logging.getLogger(__name__)


class AASProductProduct(models.Model):
    _auto = False
    _name = 'aas.product.product'
    _description = 'AAS Product Product'


    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', readonly=True)
    ptemplate_id = fields.Many2one(comodel_name='product.template', string=u'模板', readonly=True)
    product_name = fields.Char(string=u'名称', readonly=True)
    product_code = fields.Char(string=u'内部编码', readonly=True)
    customer_code = fields.Char(string=u'客户编码', readonly=True)
    category_id = fields.Many2one(comodel_name='product.category', string=u'分类', readonly=True)
    category_name = fields.Char(string=u'分类名称', readonly=True)


    def _select_sql(self):
        _select_sql = """
        SELECT pproduct.id AS id,
        pproduct.id AS product_id,
        ptemplate.id AS ptemplate_id,
        ptemplate.name AS product_name,
        pproduct.default_code AS product_code,
        ptemplate.customer_product_code AS customer_code,
        ptemplate.categ_id AS category_id,
        pcategory.name AS category_name
        FROM product_product pproduct JOIN product_template ptemplate ON pproduct.product_tmpl_id = ptemplate.id
        JOIN product_category pcategory ON pcategory.id = ptemplate.categ_id
        """
        return _select_sql


    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (self._table, self._select_sql()))


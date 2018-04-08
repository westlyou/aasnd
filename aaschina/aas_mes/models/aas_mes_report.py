# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-3-12 19:57
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging
from odoo.tools.sql import drop_view_if_exists

_logger = logging.getLogger(__name__)

class AASMESProducePlanReport(models.Model):
    _auto = False
    _name = 'aas.mes.produce.plan.report'
    _description = 'AAS MES Produce Plan Report'


    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', index=True)
    mesline_name = fields.Char(string=u'产线名称', copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', index=True)
    product_code = fields.Char(string=u'产品编码', copy=False)
    produce_date = fields.Char(string=u'生产日期', copy=False)
    plan_qty = fields.Float(string=u'计划数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)


    def _select_sql(self):
        _select_sql = """
        SELECT MIN(workorder.id) AS id,
        workorder.mesline_id AS mesline_id,
        workorder.mesline_name AS mesline_name,
        workorder.product_id AS product_id,
        workorder.product_code AS product_code,
        workorder.produce_date AS produce_date,
        sum(workorder.input_qty) AS plan_qty
        FROM aas_mes_workorder workorder
        GROUP BY workorder.mesline_id, workorder.mesline_name, workorder.product_id, workorder.product_code, workorder.produce_date
        """
        return _select_sql


    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (self._table, self._select_sql()))



class AASMESProduceOutputReport(models.Model):
    _auto = False
    _name = 'aas.mes.produce.output.report'
    _description = 'AAS MES Produce Output Report'


    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', index=True)
    mesline_name = fields.Char(string=u'产线名称', copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', index=True)
    product_code = fields.Char(string=u'产品编码', copy=False)
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', index=True)
    workstation_name = fields.Char(string=u'工位名称', copy=False)
    output_date = fields.Char(string=u'产出日期', copy=False)
    output_qty = fields.Float(string=u'产出数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)


    def _select_sql(self):
        _select_sql = """
        SELECT MIN(ampo.id) AS id,
        ampo.mesline_id AS mesline_id,
        ampo.mesline_name AS mesline_name,
        ampo.product_id AS product_id,
        ampo.product_code AS product_code,
        ampo.workstation_id AS workstation_id,
        ampo.workstation_name AS workstation_name,
        ampo.output_date AS output_date,
        sum(ampo.product_qty) AS output_qty
        FROM aas_production_product ampo
        GROUP BY ampo.mesline_id, ampo.mesline_name, ampo.product_id, ampo.product_code, ampo.output_date, ampo.workstation_id, ampo.workstation_name
        """
        return _select_sql


    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (self._table, self._select_sql()))

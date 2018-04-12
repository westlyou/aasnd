# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-4-12 16:29
"""


from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError
from odoo.tools.sql import drop_view_if_exists

import logging

_logger = logging.getLogger(__name__)


class AASMESWorkorderFinishontimeReport(models.Model):
    _auto = False
    _name = 'aas.mes.workorder.finishontime.report'
    _description = 'AAS MES Workorder Finish ON Time Report'
    _order = 'id desc'



    workorder_name = fields.Char(string=u'工单编号', copy=False)
    mesline_name = fields.Char(string=u'产线名称', copy=False)
    product_code = fields.Char(string=u'内部料号', copy=False)
    customer_code = fields.Char(string=u'客户料号', copy=False)
    finish_date = fields.Char(string=u'日期', copy=False)
    plan_qty = fields.Float(string=u'计划数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    output_qty = fields.Float(string=u'完成数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    finishontime = fields.Boolean(string=u'准时完成', default=False, copy=False)
    plan_start = fields.Datetime(string=u'计划开工时间', copy=False)
    plan_finish = fields.Datetime(string=u'计划完工时间', copy=False)
    produce_start = fields.Datetime(string=u'实际开工时间', copy=False)
    produce_finish = fields.Datetime(string=u'实际完工时间', copy=False)


    def _select_sql(self):
        _select_sql = """
        SELECT workorder.id AS id,
        workorder.name AS workorder_name,
        workorder.mesline_name AS mesline_name,
        workorder.product_code AS product_code,
        workorder.customer_code AS customer_code,
        workorder.plan_finish_date AS finish_date,
        workorder.input_qty AS plan_qty,
        workorder.output_qty AS output_qty,
        workorder.plan_start AS plan_start,
        workorder.plan_finish AS plan_finish,
        workorder.produce_start AS produce_start,
        workorder.produce_finish AS produce_finish,
        workorder.finishontime AS finishontime
        FROM aas_mes_workorder workorder
        """
        return _select_sql


    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (self._table, self._select_sql()))



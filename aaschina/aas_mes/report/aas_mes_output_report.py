# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-3-1 21:13
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError
from odoo.tools.sql import drop_view_if_exists

import logging

_logger = logging.getLogger(__name__)

class AASMESWeekOutputReport(models.Model):
    _auto = False
    _name = 'aas.mes.week.output.report'
    _description = 'AAS MES Week Output Report'

    product_code = fields.Char(string=u'产品编码', copy=False)
    customer_pn = fields.Char(string=u'客方编码', copy=False)
    mesline_name = fields.Char(string=u'产线名称', copy=False)
    schedule_name = fields.Char(string=u'班次名称', copy=False)
    workstation_name = fields.Char(string=u'工位名称', copy=False)
    qty1 = fields.Float(string=u'QTY1', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    qty2 = fields.Float(string=u'QTY2', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    qty3 = fields.Float(string=u'QTY3', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    qty4 = fields.Float(string=u'QTY4', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    qty5 = fields.Float(string=u'QTY5', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    qty6 = fields.Float(string=u'QTY6', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    qty7 = fields.Float(string=u'QTY7', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    qty = fields.Float(string=u'QTY', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    def _select_sql(self):
        _select_sql = """
        with aas_output_week_detail as (
with aas_erveryday_output as (select min(ampo.id) as id,
ampo.mesline_name,
ampo.workstation_name,
ampo.output_date,
ampo.product_code,
ampo.customer_pn,
sum(ampo.output_qty) as output_qty,
CASE WHEN ampo.schedule_name='白班' THEN 'Day' ELSE 'Night' END AS schedule_name
from aas_mes_production_output ampo
where ampo.output_date in (to_char(CURRENT_DATE, 'yyyy-MM-dd'), to_char(CURRENT_DATE -1, 'yyyy-MM-dd'),
                      to_char(CURRENT_DATE -2, 'yyyy-MM-dd'),to_char(CURRENT_DATE -3, 'yyyy-MM-dd'),
                      to_char(CURRENT_DATE -4, 'yyyy-MM-dd'),to_char(CURRENT_DATE -5, 'yyyy-MM-dd'),
                     to_char(CURRENT_DATE -6, 'yyyy-MM-dd'))
group by ampo.mesline_name, ampo.schedule_name, ampo.workstation_name, ampo.output_date, ampo.product_code,ampo.customer_pn)
select aeo.id as id,
aeo.mesline_name,
aeo.workstation_name,
aeo.product_code,
aeo.customer_pn,
aeo.schedule_name,
CASE WHEN aeo.output_date=to_char(CURRENT_DATE, 'yyyy-MM-dd') THEN aeo.output_qty ELSE 0 END AS qty1,
CASE WHEN aeo.output_date=to_char(CURRENT_DATE - 1, 'yyyy-MM-dd') THEN aeo.output_qty ELSE 0 END AS qty2,
CASE WHEN aeo.output_date=to_char(CURRENT_DATE - 2, 'yyyy-MM-dd') THEN aeo.output_qty ELSE 0 END AS qty3,
CASE WHEN aeo.output_date=to_char(CURRENT_DATE - 3, 'yyyy-MM-dd') THEN aeo.output_qty ELSE 0 END AS qty4,
CASE WHEN aeo.output_date=to_char(CURRENT_DATE - 4, 'yyyy-MM-dd') THEN aeo.output_qty ELSE 0 END AS qty5,
CASE WHEN aeo.output_date=to_char(CURRENT_DATE - 5, 'yyyy-MM-dd') THEN aeo.output_qty ELSE 0 END AS qty6,
CASE WHEN aeo.output_date=to_char(CURRENT_DATE - 6, 'yyyy-MM-dd') THEN aeo.output_qty ELSE 0 END AS qty7,
CASE WHEN aeo.output_date>=to_char(CURRENT_DATE - 6, 'yyyy-MM-dd') and aeo.output_date<=to_char(CURRENT_DATE, 'yyyy-MM-dd') THEN aeo.output_qty ELSE 0 END AS qty
from aas_erveryday_output aeo
)
select min(aowd.id) as id,
aowd.mesline_name,
aowd.workstation_name,
aowd.product_code,
aowd.customer_pn,
aowd.schedule_name,
sum(aowd.qty1) as qty1,
sum(aowd.qty2) as qty2,
sum(aowd.qty3) as qty3,
sum(aowd.qty4) as qty4,
sum(aowd.qty5) as qty5,
sum(aowd.qty6) as qty6,
sum(aowd.qty7) as qty7,
sum(aowd.qty) as qty
from aas_output_week_detail aowd
group by aowd.mesline_name,aowd.workstation_name,aowd.product_code,aowd.schedule_name,aowd.customer_pn
        """
        return _select_sql


    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (self._table, self._select_sql()))


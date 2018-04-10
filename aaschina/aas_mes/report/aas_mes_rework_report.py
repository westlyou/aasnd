# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-4-10 11:02
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError
from odoo.tools.sql import drop_view_if_exists

import logging

_logger = logging.getLogger(__name__)

class AASMESReworkReport(models.Model):
    _auto = False
    _name = 'aas.mes.rework.report'
    _description = 'AAS MES Rework Report'
    _order = 'rework_date desc'

    rework_date = fields.Char(string=u'日期', copy=False)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线')
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    mesline_name = fields.Char(string=u'产线名称', copy=False)
    schedule_name = fields.Char(string=u'班次名称', copy=False)
    workstation_name = fields.Char(string=u'工位名称', copy=False)
    product_code = fields.Char(string=u'产品编码', copy=False)
    customer_code = fields.Char(string=u'客方编码', copy=False)
    repairer_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'维修员工')
    repairer_name = fields.Char(string=u'维修员工', copy=False)
    repair_worktime = fields.Float(string=u'维修工时', default=0.0)

    def _select_sql(self):
        _select_sql = """
        SELECT MIN(rework.id) AS id,
        rework.badmode_date AS rework_date,
        rework.mesline_id AS mesline_id,
        rework.schedule_id AS schedule_id,
        rework.workstation_id AS workstation_id,
        rework.mesline_name AS mesline_name,
        rework.schedule_name AS schedule_name,
        rework.workstation_name AS workstation_name,
        rework.internalpn AS product_code,
        rework.customerpn AS customer_code,
        rework.repairer_id AS repairer_id,
        rework.repairer_name AS repairer_name,
        sum(rework.repair_worktime) AS repair_worktime
        FROM aas_mes_rework rework
        WHERE rework.repairer_id IS NOT NULL
        GROUP BY rework.badmode_date, rework.mesline_id, rework.schedule_id, rework.workstation_id, rework.mesline_name,
        rework.schedule_name, rework.workstation_name, rework.internalpn, rework.customerpn, rework.repairer_id,
        rework.repairer_name
        """
        return _select_sql


    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (self._table, self._select_sql()))
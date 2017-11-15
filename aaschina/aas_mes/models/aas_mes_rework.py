# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-11-15 09:35
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

class AASMESRework(models.Model):
    _name = 'aas.mes.rework'
    _description = 'AAS MES Rework'
    _order = 'commit_time desc'
    _rec_name = 'serialnumber_id'

    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', ondelete='restrict')
    internalpn = fields.Char(string=u'内部料号', copy=False)
    customerpn = fields.Char(string=u'客户料号', copy=False)
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    badmode_id = fields.Many2one(comodel_name='aas.mes.badmode', string=u'不良模式', ondelete='restrict')
    badmode_date = fields.Char(string=u'不良日期', compute='_compute_badmode_date', store=True)
    commit_time = fields.Datetime(string=u'上报时间', default=fields.Datetime.now, copy=False)
    commiter_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'上报员工', ondelete='restrict')
    repair_time = fields.Datetime(string=u'维修时间', copy=False)
    repairer_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'维修员工', ondelete='restrict')
    repair_note = fields.Text(string=u'维修结果')
    ipqcchecker_id = fields.Many2one(comodel_name='aas.hr.employee', string='IPQC', ondelete='restrict')
    ipqccheck_time = fields.Datetime(string=u'IPQC确认时间', copy=False)
    ipqccheck_note = fields.Text(string=u'IPQC结果')
    state = fields.Selection(selection=[('commit', u'不良上报'), ('repair', u'返工维修'), ('ipqc', u'IPQC确认')], string=u'状态', default='commit', copy=False)


    @api.depends('commit_time')
    def _compute_badmode_date(self):
        for record in self:
            if record.commit_time:
                record.badmode_date = fields.Datetime.to_timezone_string(record.commit_time, 'Asia/Shanghai')
            else:
                record.badmode_date = False

    @api.model
    def create(self, vals):
        record = super(AASMESRework, self).create(vals)
        record.write({
            'internalpn': self.serialnumber_id.internal_product_code,
            'customerpn': self.serialnumber_id.customer_product_code
        })
        return record


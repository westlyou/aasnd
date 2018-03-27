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

REWORKSTATES = [('commit', u'不良上报'), ('repair', u'返工维修'), ('ipqc', u'IPQC确认'), ('done', u'完成')]

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
    commit_worktime = fields.Float(string=u'上报工时', default=0.0)
    repair_time = fields.Datetime(string=u'维修时间', copy=False)
    repairer_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'维修员工', ondelete='restrict')
    repair_note = fields.Text(string=u'维修结果')
    repair_worktime = fields.Float(string=u'维修工时', default=0.0)
    ipqcchecker_id = fields.Many2one(comodel_name='aas.hr.employee', string='IPQC', ondelete='restrict')
    ipqccheck_time = fields.Datetime(string=u'IPQC确认时间', copy=False)
    ipqccheck_note = fields.Text(string=u'IPQC结果')
    ipqc_worktime = fields.Float(string=u'IPQC工时', default=0.0)
    state = fields.Selection(selection=REWORKSTATES, string=u'状态', default='commit', copy=False)


    @api.depends('commit_time')
    def _compute_badmode_date(self):
        for record in self:
            if record.commit_time:
                record.badmode_date = fields.Datetime.to_china_date(record.commit_time)
            else:
                record.badmode_date = False

    @api.model
    def create(self, vals):
        record = super(AASMESRework, self).create(vals)
        record.action_after_create()
        return record

    @api.one
    def action_after_create(self):
        tserialnumber = self.serialnumber_id
        self.write({
            'internalpn': tserialnumber.internal_product_code, 'customerpn': tserialnumber.customer_product_code
        })
        equipmentid, employeeid, employeename = False, False, False
        workstation, mesline = self.workstation_id, self.serialnumber_id.mesline_id
        tempdomain = [('serialnumber_id', '=', tserialnumber.id)]
        tempdomain += [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        tempoutput = self.env['aas.mes.production.output'].search(tempdomain, order='output_time desc', limit=1)
        if tempoutput:
            tempoutput.write({'pass_onetime': False, 'qualified': False})
        else:
            self.env['aas.mes.production.output'].create({
                'product_id': tserialnumber.product_id.id, 'output_qty': 1.0,
                'output_date': fields.Datetime.to_china_today(), 'mesline_id': mesline.id,
                'schedule_id': False if not mesline.schedule_id else mesline.schedule_id.id,
                'workstation_id': workstation.id, 'equipment_id': equipmentid,
                'pass_onetime': False, 'qualified': False,
                'employee_id': employeeid, 'employee_name': employeename, 'serialnumber_id': tserialnumber.id
            })


    @api.model
    def action_commit(self, serialnumber_id, workstation_id, badmode_id, commiter_id):
        rework = self.env['aas.mes.rework'].create({
            'serialnumber_id': serialnumber_id, 'workstation_id': workstation_id, 'badmode_id': badmode_id,
            'commiter_id': commiter_id, 'commit_time': fields.Datetime.now(), 'state': 'repair'
        })
        operation = self.env['aas.mes.operation'].search([('serialnumber_id', '=', rework.serialnumber_id.id)], limit=1)
        operation.write({
            'function_test': False, 'functiontest_record_id': False,
            'final_quality_check': False, 'fqccheck_record_id': False,
            'gp12_check': False, 'gp12_record_id': False,
            'commit_badness': True, 'commit_badness_count': operation.commit_badness_count + 1,
            'dorework': False, 'ipqc_check': False
        })
        rework.serialnumber_id.write({'qualified': False, 'reworked': True})

    @api.one
    def action_repair(self, repairer_id, repair_note):
        self.write({
            'repairer_id': repairer_id, 'repair_note': repair_note,
            'repair_time': fields.Datetime.now(), 'state': 'ipqc'
        })
        operation = self.env['aas.mes.operation'].search([('serialnumber_id', '=', self.serialnumber_id.id)], limit=1)
        operation.write({'dorework': True, 'dorework_count': operation.dorework_count + 1})


    @api.one
    def action_ipqcchecking(self, ipqcchecker_id, ipqccheck_note):
        self.write({
            'ipqcchecker_id': ipqcchecker_id, 'ipqccheck_note': ipqccheck_note,
            'ipqccheck_time': fields.Datetime.now(), 'state': 'done'
        })
        operation = self.env['aas.mes.operation'].search([('serialnumber_id', '=', self.serialnumber_id.id)], limit=1)
        operation.write({'ipqc_check': True, 'ipqc_check_count': operation.ipqc_check_count + 1})
        self.serialnumber_id.write({'qualified': True})



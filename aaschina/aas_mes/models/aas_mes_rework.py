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
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线')
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次')
    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    badmode_id = fields.Many2one(comodel_name='aas.mes.badmode', string=u'不良模式', ondelete='restrict')
    badmode_date = fields.Char(string=u'不良日期')
    commit_time = fields.Datetime(string=u'上报时间', default=fields.Datetime.now, copy=False)
    commiter_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'上报员工', ondelete='restrict')
    repair_time = fields.Datetime(string=u'维修时间', copy=False)
    repairer_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'维修员工', ondelete='restrict')
    repair_note = fields.Text(string=u'维修结果')
    repair_start = fields.Datetime(string=u'维修开工', copy=False)
    repair_finish = fields.Datetime(string=u'维修完工', copy=False)
    repair_worktime = fields.Float(string=u'维修工时', compute='_compute_repair_worktime', store=True)
    ipqcchecker_id = fields.Many2one(comodel_name='aas.hr.employee', string='IPQC', ondelete='restrict')
    ipqccheck_time = fields.Datetime(string=u'IPQC确认时间', copy=False)
    ipqccheck_note = fields.Text(string=u'IPQC结果')
    state = fields.Selection(selection=REWORKSTATES, string=u'状态', default='commit', copy=False)

    mesline_name = fields.Char(string=u'产线名称', copy=False)
    schedule_name = fields.Char(string=u'班次名称', copy=False)
    workstation_name = fields.Char(string=u'工位名称', copy=False)
    repairer_name = fields.Char(string=u'维修员工', copy=False)

    material_lines = fields.One2many(comodel_name='aas.mes.rework.material', inverse_name='rework_id', string=u'消耗清单')

    @api.model
    def create(self, vals):
        vals['badmode_date'] = fields.Datetime.to_china_today()
        record = super(AASMESRework, self).create(vals)
        record.action_after_create()
        return record


    @api.depends('repair_start', 'repair_finish')
    def _compute_repair_worktime(self):
        for record in self:
            if not record.repair_start or not record.repair_finish:
                record.repair_worktime = 0.0
            else:
                finishtime = fields.Datetime.from_string(record.repair_finish)
                starttime = fields.Datetime.from_string(record.repair_start)
                record.repair_worktime = (finishtime - starttime).total_seconds() / 3600.0




    @api.one
    def action_after_create(self):
        workstation = self.workstation_id
        tserialnumber = self.serialnumber_id
        repairvals = {
            'workstation_name': workstation.name,
            'internalpn': tserialnumber.internal_product_code, 'customerpn': tserialnumber.customer_product_code
        }
        tmesline = self.mesline_id
        if not tmesline:
            tmesline = tserialnumber.mesline_id
        repairvals.update({'mesline_id': tmesline.id, 'mesline_name': tmesline.name})
        tschedule = tmesline.schedule_id
        if tschedule:
            repairvals.update({'schedule_id': tschedule.id, 'schedule_name': tschedule.name})
        tempdomain = [('serialnumber_id', '=', tserialnumber.id)]
        tempdomain += [('mesline_id', '=', tmesline.id), ('workstation_id', '=', workstation.id)]
        tempoutput = self.env['aas.production.product'].search(tempdomain, order='output_time desc', limit=1)
        if tempoutput:
            tserialnumber.write({'qualified': False})
            tempoutput.write({'onepass': False, 'qualified': False})
        self.write(repairvals)


    @api.model
    def action_commit(self, serialnumber_id, workstation_id, badmode_id, commiter_id, mesline_id=False):
        tserialnumber = self.env['aas.mes.serialnumber'].browse(serialnumber_id)
        meslineid = mesline_id if mesline_id else tserialnumber.mesline_id.id
        reworking = self.env['aas.mes.rework'].create({
            'mesline_id': meslineid,
            'serialnumber_id': tserialnumber.id, 'workstation_id': workstation_id, 'state': 'repair',
            'badmode_id': badmode_id, 'commiter_id': commiter_id, 'commit_time': fields.Datetime.now(),
            'workorder_id': False if not tserialnumber.workorder_id else tserialnumber.workorder_id.id
        })
        operation = self.env['aas.mes.operation'].search([('serialnumber_id', '=', tserialnumber.id)], limit=1)
        operation.write({
            'function_test': False, 'functiontest_record_id': False,
            'final_quality_check': False, 'fqccheck_record_id': False,
            'gp12_check': False, 'gp12_record_id': False,
            'commit_badness': True, 'commit_badness_count': operation.commit_badness_count + 1,
            'dorework': False, 'ipqc_check': False
        })
        tserialnumber.write({
            'qualified': False, 'reworked': True,
            'reworksource': 'produce', 'badmode_name': reworking.badmode_id.name
        })

    @api.one
    def action_repair(self, repairer_id, repair_note, worktime=0.0):
        repairer = self.env['aas.hr.employee'].browse(repairer_id)
        self.write({
            'repairer_id': repairer_id, 'repair_note': repair_note,
            'repair_time': fields.Datetime.now(), 'state': 'ipqc', 'repairer_name': repairer.name
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




class AASMESReworkMaterial(models.Model):
    _name = 'aas.mes.rework.material'
    _description = 'AAS MES Rework Material'


    rework_id = fields.Many2one(comodel_name='aas.mes.rework', string=u'返工单', ondelete='restrict')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料', ondelete='restrict')
    material_uom = fields.Many2one(comodel_name='product.uom', string=u'单位')
    material_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    material_qty = fields.Float(string=u'消耗数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)



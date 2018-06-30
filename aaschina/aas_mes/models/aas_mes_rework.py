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

REWORKSTATES = [('commit', u'不良上报'), ('repair', u'返工维修'), ('ipqc', u'IPQC确认'), ('done', u'完成'), ('closed', u'关闭')]

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

    material_lines = fields.One2many('aas.mes.rework.material', inverse_name='rework_id', string=u'消耗清单')

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
        serialvals = {'rework_id': self.id}
        if tempoutput:
            serialvals['qualified'] = False
            tempoutput.write({'onepass': False, 'qualified': False})
        self.write(repairvals)
        tserialnumber.write(serialvals)


    @api.model
    def action_commit(self, serialnumber_id, workstation_id, badmode_id, commiter_id, mesline_id=False):
        tserialnumber = self.env['aas.mes.serialnumber'].browse(serialnumber_id)
        meslineid = mesline_id if mesline_id else tserialnumber.mesline_id.id
        workorderid = False if not tserialnumber.workorder_id else tserialnumber.workorder_id.id
        reworking = self.env['aas.mes.rework'].create({
            'mesline_id': meslineid, 'workorder_id': workorderid,
            'serialnumber_id': tserialnumber.id, 'workstation_id': workstation_id, 'state': 'repair',
            'badmode_id': badmode_id, 'commiter_id': commiter_id, 'commit_time': fields.Datetime.now()
        })
        operation = self.env['aas.mes.operation'].search([('serialnumber_id', '=', tserialnumber.id)], limit=1)
        operation.write({
            'function_test': False, 'functiontest_record_id': False,
            'final_quality_check': False, 'fqccheck_record_id': False,
            'commit_badness': True, 'commit_badness_count': operation.commit_badness_count + 1,
            'dorework': False, 'ipqc_check': False, 'gp12_check': False, 'gp12_record_id': False
        })
        serialvals = {'qualified': False, 'reworksource': 'produce', 'badmode_name': reworking.badmode_id.name}
        if not tserialnumber.reworked:
            serialvals.update({'reworked': True, 'rework_count': 1})
        else:
            serialvals['rework_count'] = tserialnumber.rework_count + 1
        tserialnumber.write(serialvals)
        if not tserialnumber.workorder_id:
            return True
        workorder = tserialnumber.workorder_id
        self.env['aas.production.badmode'].create({
            'workorder_id': workorder.id,  'mesline_id': meslineid,
            'workstation_id': workstation_id, 'serialnumber_id': serialnumber_id,
            'product_id': workorder.product_id.id, 'badmode_id': badmode_id,
            'badmode_qty': 1.0, 'badmode_date': reworking.badmode_date
        })
        if tserialnumber.rework_count <= 1:
            workorder.write({'badmode_qty': workorder.badmode_qty + 1})




    @api.model
    def action_finish_repair(self, rework, materiallist=[]):
        """ 返工维修报工
        :param rework:
        :param materiallist: [{'mesline_id': 1, 'material_id': 1, 'material_qty': 10.0}]
        :return:
        """
        values = {'success': True, 'message': ''}
        movelines, materiallines, feedids = [], [], []
        reworkvals = {'repair_finish': fields.Datetime.now(), 'state': 'ipqc', 'repair_note': 'OK'}
        if materiallist and len(materiallist) > 0:
            for material in materiallist:
                meslineid = material['mesline_id']
                materialid, materialqty = material['material_id'], material['material_qty']
                consumevals = self.action_loading_rework_consumelist(meslineid, materialid, materialqty, loadmove=True)
                if not consumevals.get('success', False):
                    return consumevals
                movelines += consumevals['movelines']
                materiallines += consumevals['materiallines']
                feedids += consumevals['feedmaterialids']
            if materiallines and len(materiallines) > 0:
                reworkvals['material_lines'] = materiallines
        rework.write(reworkvals)
        optdomain = [('serialnumber_id', '=', rework.serialnumber_id.id)]
        operation = self.env['aas.mes.operation'].search(optdomain, limit=1)
        operation.write({'dorework': True, 'dorework_count': operation.dorework_count + 1})
        if movelines and len(movelines) > 0:
            movelist = self.env['stock.move']
            for tempmove in movelines:
                movelist |= self.env['stock.move'].create(tempmove)
            movelist.action_done()
        if feedids and len(feedids) > 0:
            feedinglist = self.env['aas.mes.feedmaterial'].browse(feedids)
            feedinglist.action_freshandclear()
        return values


    def action_loading_rework_consumelist(self, meslineid, materialid, materialqty, loadmove=False):
        values = {
            'success': True, 'message': '', 'meslineid': meslineid, 'feedmaterialids': [],
            'materialid': materialid, 'materialcode': '', 'materialqty': materialqty,
            'stockqty': 0.0, 'movelines': [], 'materiallines': []
        }
        material = self.env['product.product'].browse(materialid)
        feedomain = [('mesline_id', '=', meslineid), ('material_id', '=', materialid)]
        feedmaterialist = self.env['aas.mes.feedmaterial'].search(feedomain, order='id asc')
        if not feedmaterialist or len(feedmaterialist) <= 0:
            values.update({'success': False, 'message': u'%s还未投料或产线投料已消耗完毕，请先上料！'% material.default_code})
            return values
        stock_qty, waitqty, feedmaterialids, companyid = 0.0, materialqty, [], self.env.user.company_id.id
        movedict, materialdict, productionlocation = {}, {}, self.env.ref('stock.location_production')
        for feedmaterial in feedmaterialist:
            if not loadmove:
                stock_qty += feedmaterial.material_qty
                continue
            feedmaterialids.append(feedmaterial.id)
            quantlist = feedmaterial.action_checking_quants()
            for quant in quantlist:
                if float_compare(waitqty, 0.0, precision_rounding=0.000001) <= 0.0:
                    break
                if float_compare(quant.qty, 0.0, precision_rounding=0.000001) <= 0.0:
                    break
                if float_compare(waitqty, quant.qty, precision_rounding=0.000001) >= 0.0:
                    temp_qty = quant.qty
                else:
                    temp_qty = waitqty
                pkey = 'P-'+str(quant.lot_id.id)+'-'+str(quant.location_id.id)
                if pkey not in movedict:
                    movedict[pkey] = {
                        'name': u'返工消耗', 'product_id': materialid, 'product_uom': material.uom_id.id,
                        'create_date': fields.Datetime.now(), 'restrict_lot_id': quant.lot_id.id,
                        'product_uom_qty': temp_qty, 'location_id': quant.location_id.id,
                        'location_dest_id': productionlocation.id, 'company_id': companyid,
                    }
                else:
                    movedict[pkey]['product_uom_qty'] += temp_qty
                if pkey not in materialdict:
                    materialdict[pkey] = {
                        'mesline_id': meslineid, 'material_id': materialid, 'material_qty': temp_qty,
                        'material_uom': material.uom_id.id, 'material_lot': quant.lot_id.id,
                        'location_id': quant.location_id.id
                    }
                else:
                    materialdict[pkey]['material_qty'] += temp_qty

                waitqty -= temp_qty

            stock_qty += feedmaterial.material_qty
        if float_compare(stock_qty, materialqty, precision_rounding=0.000001) <= 0.0:
            values.update({'success': False, 'message': u'%s上料不足，请先补足消耗数量！'% material.default_code})
            return values
        if movedict and len(movedict) > 0:
            values['movelines'] = movedict.values()
        if materialdict and len(materialdict) > 0:
            values['materiallines'] = [(0, 0, mval) for mkey, mval in materialdict.items()]
        values.update({
            'materialcode': material.default_code, 'stockqty': stock_qty, 'feedmaterialids': feedmaterialids
        })
        return values



    @api.one
    def action_ipqcchecking(self, ipqcchecker_id, ipqccheck_note):
        self.write({
            'ipqcchecker_id': ipqcchecker_id, 'ipqccheck_note': ipqccheck_note,
            'ipqccheck_time': fields.Datetime.now(), 'state': 'done'
        })
        operation = self.env['aas.mes.operation'].search([('serialnumber_id', '=', self.serialnumber_id.id)], limit=1)
        operation.write({'ipqc_check': True, 'ipqc_check_count': operation.ipqc_check_count + 1})
        self.serialnumber_id.write({'qualified': True})

    @api.multi
    def action_close_rework(self):
        """关闭返工单
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.mes.rework.close.wizard'].create({'rework_id': self.id})
        view_form = self.env.ref('aas_mes.view_form_aas_mes_rework_close_wizard')
        return {
            'name': u"关闭返工单",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.rework.close.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }



class AASMESReworkConsumeMaterial(models.Model):
    _name = 'aas.mes.rework.material'
    _description = 'AAS MES Rework Material'


    rework_id = fields.Many2one(comodel_name='aas.mes.rework', string=u'返工单', ondelete='restrict')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料', ondelete='restrict')
    material_uom = fields.Many2one(comodel_name='product.uom', string=u'单位')
    material_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    material_qty = fields.Float(string=u'消耗数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)


class AASMESReworkCloseWizard(models.TransientModel):
    _name = 'aas.mes.rework.close.wizard'
    _description = 'AAS MES Rework Close Wizard'

    rework_id = fields.Many2one(comodel_name='aas.mes.rework', string=u'返工单', ondelete='cascade')
    ipqccheck_id = fields.Many2one(comodel_name='aas.hr.employee', string='IPQC', ondelete='cascade')
    close_note = fields.Text(string=u'备注')

    @api.one
    def action_done(self):
        self.rework_id.write({
            'ipqcchecker_id': self.ipqccheck_id.id, 'state': 'closed',
            'ipqccheck_time': fields.Datetime.now(), 'ipqccheck_note': self.close_note
        })
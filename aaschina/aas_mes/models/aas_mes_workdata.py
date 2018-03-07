# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-3-6 23:30
"""

#### 报表补救

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


# 消耗明细
class AASMESWorkdataConsume(models.Model):
    _name = 'aas.mes.workdata.consume'
    _description = 'AAS MES Workdata Consume'

    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', ondelete='restrict')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料', ondelete='restrict')
    material_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    material_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)



# 成品产出
class AASMESWorkdataOutput(models.Model):
    _name = 'aas.mes.workdata.output'
    _description = 'AAS MES Workdata Output'

    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', index=True)
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)








class AASMESWorkorder(models.Model):
    _inherit = 'aas.mes.workorder'

    @api.model
    def action_output(self, workorder_id, product_id, commit_qty, container_id=None,
                      workstation_id=None, badmode_lines=[], serialnumber=None):
        tempvals = super(AASMESWorkorder, self).action_output(workorder_id, product_id, commit_qty, container_id,
                                                              workstation_id, badmode_lines, serialnumber)
        workorder = self.env['aas.mes.workorder'].browse(workorder_id)
        if serialnumber:
            tserialnumber = self.env['aas.mes.serialnumber'].search([('name', '=', serialnumber)], limit=1)
            self.env['aas.mes.workdata.output'].create({
                'workorder_id': workorder.id, 'product_id': product_id,
                'serialnumber_id': tserialnumber.id, 'product_qty': '1'
            })
        else:
            temp_qty = commit_qty
            if badmode_lines and len(badmode_lines) > 0:
                temp_qty -= sum([bline['badmode_qty'] for bline in badmode_lines])
            if float_compare(temp_qty, 0.0, precision_rounding=0.000001) > 0:
                lotname = workorder.mesline_id.workdate.replace('-', '')
                product_lot = self.env['stock.production.lot'].action_checkout_lot(product_id, lotname)
                outputdoamin = [('workorder_id', '=', workorder_id), ('product_lot', '=', product_lot.id)]
                workdataoutput = self.env['aas.mes.workdata.output'].search(outputdoamin, limit=1)
                if not workdataoutput:
                    self.env['aas.mes.workdata.output'].create({
                        'workorder_id': workorder_id, 'product_id': product_id,
                        'product_lot': product_lot.id, 'product_qty': temp_qty
                    })
                else:
                    workdataoutput.update({'product_qty': workdataoutput.product_qty + temp_qty})
        return tempvals


    @api.multi
    def action_loading_consume(self):
        self.ensure_one()
        consumelist = []
        templist = self.env['aas.mes.workdata.consume'].search([('workorder_id', '=', self.id)])
        if templist and len(templist) > 0:
            for tconsume in templist:
                consumelist.append({
                    'master_workorder_id': self.id, 'product_id': self.product_id.id,
                    'master_mesline_id': self.mesline_id.id, 'master_output_qty': self.output_qty,
                    'master_input_qty': self.input_qty, 'material_lot': tconsume.material_lot.id,
                    'slave_workorder_id': tconsume.workorder_id.id, 'material_id': tconsume.material_id.id,
                    'slave_mesline_id': tconsume.workorder_id.mesline_id.id,
                    'slave_output_qty': tconsume.workorder_id.output_qty,
                    'slave_input_qty': tconsume.workorder_id.input_qty
                })
                outputdomain = [('product_id', '=', tconsume.material_id.id), ('product_lot', '=', tconsume.material_lot.id)]
                outputlist = self.env['aas.mes.workdata.output'].search(outputdomain)
                workorderids = []
                for tempout in outputlist:
                    if tempout.workorder_id.id in workorderids:
                        continue
                    workorderids.append(tempout.workorder_id.id)
                    consumelist += tempout.workorder_id.action_loading_consume()
        return consumelist


class AASMESWorkorderProduct(models.Model):
    _inherit = 'aas.mes.workorder.product'

    @api.model
    def action_output_consume(self, outputrecord):
        tempvals = super(AASMESWorkorderProduct, self).action_output_consume(outputrecord)
        movelist = self.env['stock.move'].browse(tempvals['moveids'])
        movedict = {}
        for tmove in movelist:
            mkey = 'M-'+str(tmove.product_id.id)+'-'+str(tmove.restrict_lot_id.id)
            if mkey in movedict:
                movedict[mkey]['material_qty'] += tmove.product_uom_qty
            else:
                movedict[mkey] = {
                    'material_id': tmove.product_id.id,
                    'material_lot': tmove.restrict_lot_id.id, 'material_qty': tmove.product_uom_qty
                }
        workorderid = outputrecord.workorder_id.id
        for mkey, mval in movedict.items():
            mlotid = mval['material_lot']
            consumedomain = [('workorder_id', '=', workorderid), ('material_lot', '=', mlotid)]
            tconsume = self.env['aas.mes.workdata.consume'].search(consumedomain, limit=1)
            if tconsume:
                tconsume.write({'material_qty': tconsume.material_qty + mval['material_qty']})
            else:
                self.env['aas.mes.workdata.consume'].create({
                    'workorder_id': workorderid, 'material_id': mval['material_id'],
                    'material_lot': mval['material_lot'], 'material_qty': mval['material_qty']
                })
        return tempvals




class AASMESSerialnumber(models.Model):
    _inherit = 'aas.mes.serialnumber'

    @api.multi
    def action_label(self, labelid):
        super(AASMESSerialnumber, self).action_label(labelid)
        label = self.env['aas.product.label'].browse(labelid)
        serialnumberlist = self.env['aas.mes.serialnumber'].search([('label_id', '=', labelid)])
        outputlist = self.env['aas.mes.workdata.output'].search([('serialnumber_id', 'in', serialnumberlist.ids)])
        if outputlist and len(outputlist) > 0:
            outputlist.write({'product_lot': label.product_lot.id})



class AASMESWorkticket(models.Model):
    _inherit = 'aas.mes.workticket'


    @api.multi
    def action_workticket_consume(self, trace, commit_qty):
        tvalues = super(AASMESWorkticket, self).action_workticket_consume(trace, commit_qty)
        movelist = self.env['stock.move'].browse(tvalues['moveids'])
        movedict = {}
        for tmove in movelist:
            mkey = 'M-'+str(tmove.product_id.id)+'-'+str(tmove.restrict_lot_id.id)
            if mkey in movedict:
                movedict[mkey]['material_qty'] += tmove.product_uom_qty
            else:
                movedict[mkey] = {
                    'material_id': tmove.product_id.id,
                    'material_lot': tmove.restrict_lot_id.id, 'material_qty': tmove.product_uom_qty
                }
        workorderid = trace.workorder_id.id
        for mkey, mval in movedict.items():
            mlotid = mval['material_lot']
            consumedomain = [('workorder_id', '=', workorderid), ('material_lot', '=', mlotid)]
            tconsume = self.env['aas.mes.workdata.consume'].search(consumedomain, limit=1)
            if tconsume:
                tconsume.write({'material_qty': tconsume.material_qty + mval['material_qty']})
            else:
                self.env['aas.mes.workdata.consume'].create({
                    'workorder_id': workorderid, 'material_id': mval['material_id'],
                    'material_lot': mval['material_lot'], 'material_qty': mval['material_qty']
                })
        return tvalues


    @api.one
    def action_workticket_output(self, trace, output_qty, badmode_qty):
        super(AASMESWorkticket, self).action_workticket_output(trace, output_qty, badmode_qty)
        if float_compare(output_qty, badmode_qty, precision_rounding=0.000001) > 0.0:
            workorder, mesline = trace.workorder_id, trace.workorder_id.mesline_id
            if not mesline.workdate:
                lotname = fields.Datetime.to_china_today().replace('-', '')
            else:
                lotname = mesline.workdate.replace('-', '')
            product_qty = output_qty - badmode_qty
            product_lot = self.env['stock.production.lot'].action_checkout_lot(self.product_id.id, lotname)
            outputdoamin = [('workorder_id', '=', workorder.id), ('product_lot', '=', product_lot.id)]
            workdataoutput = self.env['aas.mes.workdata.output'].search(outputdoamin, limit=1)
            if not workdataoutput:
                self.env['aas.mes.workdata.output'].create({
                    'workorder_id': workorder.id, 'product_id': self.product_id.id,
                    'product_lot': product_lot.id, 'product_qty': product_qty
                })
            else:
                workdataoutput.update({'product_qty': workdataoutput.product_qty + product_qty})





############################Wizard#################################

class AASMESWorkdataForwardTracingWizard(models.TransientModel):
    _name = 'aas.mes.workdata.forward.tracing.wizard'
    _description = 'AAS MES Workdata Forward Tracing Wizard'


    serialnumber = fields.Char(string=u'序列号', required=True, copy=False)


    @api.multi
    def action_done(self):
        self.ensure_one()
        reportlist = self.env['aas.mes.workdata.tracing.report.wizard'].search([])
        if reportlist and len(reportlist) > 0:
            reportlist.unlink()
        tserialnumber = self.env['aas.mes.serialnumber'].search([('name', '=', self.serialnumber)], limit=1)
        if not tserialnumber or not tserialnumber.workorder_id:
            raise UserError(u'请检查序列号是否有误，或当前隔离板还没有产出！')
        consumelist = tserialnumber.workorder_id.action_loading_consume()
        if not consumelist or len(consumelist) <= 0:
            raise UserError(u'当前未获取到追溯信息！')
        for tempval in consumelist:
            self.env['aas.mes.workdata.tracing.report.wizard'].create(tempval)
        view_form = self.env.ref('aas_mes.view_form_aas_mes_workdata_tracing_report_wizard')
        view_tree = self.env.ref('aas_mes.view_tree_aas_mes_workdata_tracing_report_wizard')
        return {
            'name': u"追溯信息",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'aas.mes.workdata.tracing.report.wizard',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'target': 'self',
            'context': self.env.context
        }



class AASMESWorkdataReverseTracingWizard(models.TransientModel):
    _name = 'aas.mes.workdata.reverse.tracing.wizard'
    _description = 'AAS MES Workdata Reverse Tracing Wizard'


    material_id = fields.Many2one(comodel_name='product.product', string=u'原料', required=True)
    material_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', required=True)


    @api.multi
    def action_done(self):
        self.ensure_one()
        reportlist = self.env['aas.mes.workdata.tracing.report.wizard'].search([])
        if reportlist and len(reportlist) > 0:
            reportlist.unlink()
        materialid, matrialotid = self.material_id.id, self.material_lot.id
        tracinglist = self.env['aas.mes.workdata.tracing.report.wizard'].action_loading_reverse_tracing(materialid, matrialotid)
        if not tracinglist or len(tracinglist) <= 0:
            raise UserError(u'当前未获取到追溯信息！')
        for tempval in tracinglist:
            self.env['aas.mes.workdata.tracing.report.wizard'].create(tempval)
        view_form = self.env.ref('aas_mes.view_form_aas_mes_workdata_tracing_report_wizard')
        view_tree = self.env.ref('aas_mes.view_tree_aas_mes_workdata_tracing_report_wizard')
        return {
            'name': u"追溯信息",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'aas.mes.workdata.tracing.report.wizard',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'target': 'self',
            'context': self.env.context
        }






class AASMESWorkdataTracingReportWizard(models.TransientModel):
    _name = 'aas.mes.workdata.tracing.report.wizard'
    _description = 'AAS MES Workdata Tracing Report Wizard'
    _rec_name = 'product_id'

    master_workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'上级工单')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品')
    master_mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'上级产线')
    master_output_qty = fields.Float(string=u'上级工单产出数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    master_input_qty = fields.Float(string=u'上级工单计划数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    material_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'原料批次')
    slave_workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'下级工单')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料')
    slave_mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'下级产线')
    slave_output_qty = fields.Float(string=u'下级工单产出', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    slave_input_qty = fields.Float(string=u'下级工单计划数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)


    @api.model
    def action_loading_reverse_tracing(self, material_id, material_lotid):
        tracinglist = []
        condomain = [('material_id', '=', material_id), ('material_lot', '=', material_lotid)]
        consumelist = self.env['aas.mes.workdata.consume'].search(condomain)
        if consumelist and len(consumelist) > 0:
            for tconsume in consumelist:
                workorder = tconsume.workorder_id
                tracinglist.append({
                    'master_workorder_id': workorder.id, 'product_id': workorder.product_id.id,
                    'master_mesline_id': workorder.mesline_id.id, 'master_output_qty': workorder.output_qty,
                    'master_input_qty': workorder.input_qty,
                    'material_lot': material_lotid, 'material_id': material_id
                })
                outdomain = [('workorder_id', '=', workorder.id)]
                outputlist = self.env['aas.mes.workdata.output'].search(outdomain)
                if not outputlist or len(outputlist) <= 0:
                    continue
                tempkeys = []
                for toutput in outputlist:
                    if not toutput.product_lot:
                        continue
                    tkey = 'T-'+str(toutput.workorder_id.id)+'-'+str(toutput.product_lot.id)
                    if tkey in tempkeys:
                        continue
                    tracinglist += self.env['aas.mes.workdata.tracing.report.wizard'].\
                        action_loading_reverse_tracing(toutput.product_id.id, toutput.product_lot.id)
        return tracinglist












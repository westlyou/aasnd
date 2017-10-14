# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-9-22 15:07
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


# 工票

TICKETSTATES = [('draft', u'草稿'), ('waiting', u'等待'), ('producing', u'生产'), ('pause', u'暂停'), ('done', u'完成')]


class AASMESWorkticket(models.Model):
    _name = 'aas.mes.workticket'
    _description = 'AAS MES Workticket'
    _order = 'workorder_id desc,sequence'
    _rec_name = 'workcenter_name'

    name = fields.Char(string=u'名称', required=True, copy=False)
    barcode = fields.Char(string=u'条码', compute="_compute_barcode", store=True)
    sequence = fields.Integer(string=u'序号')
    routing_id = fields.Many2one(comodel_name='aas.mes.routing', string=u'工艺', ondelete='restrict')
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    input_qty = fields.Float(string=u'投入数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    output_qty = fields.Float(string=u'产出数量', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_output_qty', store=True)
    state = fields.Selection(selection=TICKETSTATES, string=u'状态', default='draft', copy=False)
    time_wait = fields.Datetime(string=u'等待时间', copy=False)
    time_start = fields.Datetime(string=u'开工时间', copy=False)
    time_finish = fields.Datetime(string=u'完工时间', copy=False)
    workcenter_name = fields.Char(string=u'工序名称')
    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'子工单', ondelete='cascade')
    workorder_name = fields.Char(string=u'子工单')
    mainorder_id = fields.Many2one(comodel_name='aas.mes.mainorder', string=u'主工单')
    mainorder_name = fields.Char(string=u'主工单')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'生产线', ondelete='restrict')
    mesline_name = fields.Char(string=u'生产线')
    badmode_qty = fields.Float(string=u'不良数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    badmode_lines = fields.One2many(comodel_name='aas.mes.workticket.badmode', inverse_name='workticket_id', string=u'不良明细')



    @api.depends('name')
    def _compute_barcode(self):
        for record in self:
            record.barcode = 'AR'+record.name

    @api.depends('input_qty', 'badmode_qty')
    def _compute_output_qty(self):
        for record in self:
            record.output_qty = record.input_qty - record.badmode_qty


    @api.multi
    def action_start(self):
        self.ensure_one()
        workstation = self.workcenter_id.workstation_id
        if not workstation:
            raise UserError(u'工序%s还未指定工位，请联系管理员进行设置！'% self.workcenter_name)
        if not workstation.employee_lines or len(workstation.employee_lines) <= 0:
            raise UserError(u'当前工位%s上没有员工在岗不可以开工！'% workstation.name)
        wizardvals = {'workticket_id': self.id, 'workstation_id': workstation.id, 'input_qty': self.input_qty}
        wizard = self.env['aas.mes.workticket.start.wizard'].create(wizardvals)
        view_form = self.env.ref('aas_mes.view_form_aas_mes_workticket_start_wizard')
        return {
            'name': u"生产开工",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.workticket.start.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }


    @api.one
    def action_doing_start(self, input_qty):
        workstation = self.workcenter_id.workstation_id
        self.write({'time_start': fields.Datetime.now(), 'input_qty': input_qty, 'state': 'producing'})
        tracevals = {'date_start': fields.Datetime.now()}
        if workstation.employee_lines and len(workstation.employee_lines) > 0:
            tracevals['employeelist'] = ','.join([temployee.name+'['+temployee.code+']' for temployee in workstation.employee_lines])
        if workstation.equipment_lines and len(workstation.equipment_lines):
            tracevals['equipmentlist'] = ','.join([tequipment.name+'['+tequipment.code+']' for tequipment in workstation.equipment_lines])
        temptrace = self.env['aas.mes.tracing'].search([('workorder_id', '=', self.workorder_id.id), ('workcenter_id', '=', self.workcenter_id.id)], limit=1)
        if temptrace:
            temptrace.write(tracevals)
        else:
            tracevals.update({
                'workorder_id': self.workorder_id.id, 'workorder_name': self.workorder_name,
                'workcenter_id': self.workcenter_id.id, 'workcenter_name': self.workcenter_name,
                'workstation_id': workstation.id, 'workstation_name': workstation.name,
                'mesline_id': self.mesline_id.id, 'mesline_name': self.mesline_name,
                'product_id': self.product_id.id, 'product_uom': self.product_uom.id,
                'product_code': self.product_id.default_code,
                'mainorder_id': False if not self.mainorder_id else self.mainorder_id.id,
                'mainorder_name': False if not self.mainorder_name else self.mainorder_name
            })
            self.env['aas.mes.tracing'].create(tracevals)
        if self.id == self.workorder_id.workcenter_start.id:
            tempvals = {'state': 'producing', 'produce_start': fields.Datetime.now()}
            # 子工单状态更新，开始生产
            self.workorder_id.write(tempvals)
            # 主工单状态更新，开始生产
            if self.mainorder_id and self.mainorder_id.state=='splited':
                self.mainorder_id.write(tempvals)


    @api.multi
    def action_finish(self):
        self.ensure_one()
        workstation = self.workcenter_id.workstation_id
        if not workstation:
            raise UserError(u'工序%s还未指定工位，请联系管理员进行设置！'% self.workcenter_name)
        if not workstation.employee_lines or len(workstation.employee_lines) <= 0:
            raise UserError(u'当前工位%s上没有员工在岗不可以完工！'% workstation.name)
        #判断有没有上料todo
        wizardvals = {
            'workticket_id': self.id, 'workstation_id': workstation.id,
            'input_qty': self.input_qty, 'workcenter_id': self.workcenter_id.id
        }
        wizard = self.env['aas.mes.workticket.finish.wizard'].create(wizardvals)
        view_form = self.env.ref('aas_mes.view_form_aas_mes_workticket_finish_wizard')
        return {
            'name': u"生产完工",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.workticket.finish.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }


    @api.one
    def action_doing_finish(self):
        badmode_qty = 0.0
        if self.badmode_lines and len(self.badmode_lines) > 0:
            badmode_qty = sum([bline.badmode_qty for bline in self.badmode_lines])
        self.write({'time_finish': fields.Datetime.now(), 'state': 'done', 'badmode_qty': badmode_qty})
        # 更新追溯信息
        temptrace = self.action_refresh_tracing()
        # 计算物料消耗
        self.action_material_consume(temptrace)
        # 创建下一个工票，或工单完成
        self.action_after_done()


    @api.multi
    def action_refresh_tracing(self):
        self.ensure_one()
        workstation = self.workcenter_id.workstation_id
        temptrace = self.env['aas.mes.tracing'].search([('workorder_id', '=', self.workorder_id.id), ('workcenter_id', '=', self.workcenter_id.id)], limit=1)
        if not temptrace:
            temptrace = self.env['aas.mes.tracing'].create({
                'workorder_id': self.workorder_id.id, 'workorder_name': self.workorder_name,
                'workcenter_id': self.workcenter_id.id, 'workcenter_name': self.workcenter_name,
                'workstation_id': workstation.id, 'workstation_name': workstation.name,
                'mesline_id': self.mesline_id.id, 'mesline_name': self.mesline_name,
                'product_id': self.product_id.id, 'product_uom': self.product_uom.id,
                'product_code': self.product_id.default_code,
                'mainorder_id': False if not self.mainorder_id else self.mainorder_id.id,
                'mainorder_name': False if not self.mainorder_name else self.mainorder_name
            })
        tracevals = {'date_finish': fields.Datetime.now()}
        employeelist = [] if not temptrace.employeelist else temptrace.employeelist.split(',')
        if workstation.employee_lines and len(workstation.employee_lines) > 0:
            for wemployee in workstation.employee_lines:
                wkey = wemployee.name+'['+wemployee.code+']'
                if wkey not in employeelist:
                    employeelist.append(wkey)
        if employeelist and len(employeelist) > 0:
            tracevals['employeelist'] = ','.join(employeelist)
        equipmentlist = [] if not temptrace.equipmentlist else temptrace.equipmentlist.split(',')
        if workstation.equipment_lines and len(workstation.equipment_lines) > 0:
            for wequipment in workstation.equipment_lines:
                wkey = wequipment.name+'['+wequipment.code+']'
                if wkey not in equipmentlist:
                    equipmentlist.append(wkey)
        if equipmentlist and len(equipmentlist) > 0:
            tracevals['equipmentlist'] = ','.join(equipmentlist)
        temptrace.write(tracevals)
        return temptrace


    @api.one
    def action_after_done(self):
        currentworkcenter = self.workcenter_id
        domain = [('routing_id', '=', self.routing_id.id), ('sequence', '>', currentworkcenter.sequence)]
        nextworkcenter = self.env['aas.mes.routing.line'].search(domain, order='sequence', limit=1)
        if nextworkcenter:
            tempworkcenter = self.env['aas.mes.workticket'].create({
                'name': self.workorder_id.name+'-'+str(nextworkcenter.sequence),
                'routing_id': self.routing_id.id, 'workcenter_id': nextworkcenter.id,
                'workcenter_name': nextworkcenter.name, 'product_id': self.product_id.id,
                'product_uom': self.product_uom.id, 'input_qty': self.output_qty,
                'state': 'waiting', 'time_wait': fields.Datetime.now(),
                'workorder_id': self.workorder_id.id, 'workorder_name': self.workorder_name,
                'mainorder_id': False if not self.mainorder_id else self.mainorder_id.id,
                'mainorder_name': self.mainorder_name, 'mesline_id': self.mesline_id.id,
                'mesline_name': self.mesline_name, 'sequence': nextworkcenter.sequence
            })
            self.workorder_id.write({
                'workcenter_id': tempworkcenter.id, 'workcenter_name': nextworkcenter.name
            })
        else:
            self.workorder_id.write({
                'workcenter_id': False, 'workcenter_name': False, 'workcenter_finish': self.id,
                'product_lines': [(0, 0, {'product_id': self.product_id.id, 'product_qty': self.output_qty})]
            })
            self.workorder_id.action_done()


    @api.one
    def action_material_consume(self, tracing):
        """
        计算物料消耗
        :param tracing:
        :return:
        """
        workcenter, workstation = self.workcenter_id, self.workcenter_id.workstation_id
        if not workstation:
            raise UserError(u'工位%s还未设置工位，请先设置工序工位！')
        mesbom = self.workorder_id.aas_bom_id
        bomworkcenterlist = self.env['aas.mes.bom.workcenter'].search([('bom_id', '=', mesbom.id), ('workcenter_id', '=', workcenter.id)])
        if not bomworkcenterlist or len(bomworkcenterlist) <= 0:
            return
        location_production = self.env.ref('aas_wms.location_production')
        movedict, productlotlist, feedlistneedrefresh = {}, [], self.env['aas.mes.feedmaterial']
        for bomworkcenter in bomworkcenterlist:
            product_id, product_qty = bomworkcenter.product_id, bomworkcenter.product_qty
            feedmaterials = self.env['aas.mes.feedmaterial'].search([('material_id', '=', product_id.id), ('workstation_id', '=', workstation.id)])
            if not feedmaterials or len(feedmaterials) <= 0:
                raise UserError(u'工位%s还未上料%s'% (workstation.name, product_id.default_code))
            for feedmaterial in feedmaterials:
                quantlist = feedmaterial.action_checking_quants()
                if not quantlist or len(quantlist) <= 0:
                    break
                if float_compare(feedmaterial.material_qty, product_qty, precision_rounding=0.000001) < 0.0:
                    raise UserError(u'工位%s的原料%s上料不足，请联系上料员或领班上料或调整产线库存！'% (workstation.name, product_id.default_code))
                for quant in quantlist:
                    if float_compare(product_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                        break
                    tempqty = product_qty if float_compare(quant.qty, product_qty, precision_rounding=0.000001) >= 0.0 else quant.qty
                    qkey = 'P-'+str(product_id.id)+'-'+str(quant.lot_id.id)+'-'+str(quant.location_id.id)
                    if qkey in movedict:
                        movedict[qkey]['product_uom_qty'] += quant.qty
                    else:
                        movedict[qkey] = {
                            'name': self.name, 'product_id': product_id.id, 'product_uom': product_id.uom_id.id,
                            'create_date': fields.Datetime.now(), 'restrict_lot_id': quant.lot_id.id,
                            'product_uom_qty': quant.qty, 'company_id': self.env.user.company_id.id,
                            'trace_id': tracing.id, 'location_id': quant.location_id.id, 'location_dest_id': location_production.id
                        }
                        productlotlist.append(quant.product_id.default_code+'['+quant.lot_id.name+']')
                    product_qty -= tempqty
                feedlistneedrefresh |= feedmaterial
        if movedict and len(movedict) > 0:
            movelist = self.env['stock.move']
            for mkey, mval in movedict.items():
                tempmove = self.env['stock.move'].create(mval)
                movelist |= tempmove
            movelist.action_done()
        if feedlistneedrefresh and len(feedlistneedrefresh) > 0:
            for feedmaterial in feedlistneedrefresh:
                feedmaterial.action_refresh_stock()
        tracing.write({'materiallist': '.'.join(productlotlist)})










class AASMESWorkticketBadmode(models.Model):
    _name = 'aas.mes.workticket.badmode'
    _description = 'AAS MES Workticket Badmode'
    _rec_name = 'badmode_id'

    workticket_id = fields.Many2one(comodel_name='aas.mes.workticket', string=u'工票', ondelete='cascade')
    badmode_id = fields.Many2one(comodel_name='aas.mes.badmode', string=u'不良模式', ondelete='restrict')
    badmode_qty = fields.Float(string=u'不良数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)






################################################向导########################################

# 开工向导
class AASMESWorkticketStartWizard(models.TransientModel):
    _name = 'aas.mes.workticket.start.wizard'
    _description = 'AAS MES Workstation Start Wizard'


    workticket_id = fields.Many2one(comodel_name='aas.mes.workticket', string=u'工票', ondelete='cascade')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位')
    input_qty = fields.Float(string=u'投入数量', digits=dp.get_precision('Product Unit of Measure'))

    @api.one
    def action_done(self):
        if not self.input_qty or float_compare(self.input_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise UserError(u'投入数量必须是一个大于0的数！')
        self.workticket_id.action_doing_start(self.input_qty)



# 完工向导
class AASMESWorkticketFinishWizard(models.TransientModel):
    _name = 'aas.mes.workticket.finish.wizard'
    _description = 'AAS MES Workstation Finish Wizard'


    workticket_id = fields.Many2one(comodel_name='aas.mes.workticket', string=u'工票', ondelete='cascade')
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位')
    input_qty = fields.Float(string=u'投入数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    output_qty = fields.Float(string=u'产出数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    badmode_lines = fields.One2many(comodel_name='aas.mes.workticket.badmode.wizard', inverse_name='wizard_id', string=u'不良信息')

    @api.model
    def create(self, vals):
        record = super(AASMESWorkticketFinishWizard, self).create(vals)
        if not record.workcenter_id:
            record.write({'workcenter_id': record.workticket_id.workcenter_id.id})
        return record

    @api.one
    def action_done(self):
        badmode_qty, badmode_lines = 0.0, []
        if self.badmode_lines and len(self.badmode_lines) > 0:
            for bline in self.badmode_lines:
                badmode_qty += bline.badmode_qty
                badmode = bline.badmode_id.badmode_id
                badmode_lines.append((0, 0, {'badmode_id': badmode.id, 'badmode_qty': bline.badmode_qty}))
        if float_compare(badmode_qty, self.input_qty, precision_rounding=0.000001) > 0.0:
            raise UserError(u'不良数量的总和不可以大于投入数量！')
        self.write({'output_qty': self.input_qty-badmode_qty})
        if badmode_lines and len(badmode_lines) > 0:
            self.workticket_id.write({'badmode_lines': badmode_lines})
        self.workticket_id.action_doing_finish()

class AASMESWorkticketFinishBadmodeWizard(models.TransientModel):
    _name = 'aas.mes.workticket.badmode.wizard'
    _description = 'AAS MES Workticket Badmode Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.mes.workticket.finish.wizard', string=u'完工向导', ondelete='cascade')
    badmode_id = fields.Many2one(comodel_name='aas.mes.routing.badmode', string=u'不良模式', ondelete='restrict')
    badmode_qty = fields.Float(string=u'不良数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    _sql_constraints = [
        ('uniq_badmode', 'unique (wizard_id, badmode_id)', u'请不要重复添加同一个不良模式！')
    ]

    @api.one
    @api.constrains('badmode_qty')
    def action_check_badmode_qty(self):
        if not self.badmode_qty or float_compare(self.badmode_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise ValidationError(u'不良数量必须是大于0的数！')








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
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次', ondelete='restrict')
    badmode_qty = fields.Float(string=u'不良数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    badmode_lines = fields.One2many(comodel_name='aas.mes.workticket.badmode', inverse_name='workticket_id', string=u'不良明细')

    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='restrict')

    @api.depends('name')
    def _compute_barcode(self):
        for record in self:
            record.barcode = 'AR'+record.name


    @api.depends('input_qty', 'badmode_qty')
    def _compute_output_qty(self):
        for record in self:
            if record.state in ['draft', 'waiting']:
                record.output_qty = 0.0
            else:
                record.output_qty = record.input_qty - record.badmode_qty


    @api.multi
    def action_start(self):
        self.ensure_one()
        workstation = self.workcenter_id.workstation_id
        if not workstation:
            raise UserError(u'工序%s还未指定工位，请联系管理员进行设置！'% self.workcenter_name)
        employeeliststr = workstation.action_get_employeestr(self.mesline_id.id, workstation.id)
        if not employeeliststr:
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
    def action_doing_start(self):
        workstation = self.workcenter_id.workstation_id
        ticketvals = {'time_start': fields.Datetime.now(), 'state': 'producing'}
        if self.mesline_id.schedule_id:
            ticketvals['schedule_id'] = self.mesline_id.schedule_id.id
        self.write(ticketvals)
        tracevals = {'date_start': fields.Datetime.now(), 'schedule_id': ticketvals.get('schedule_id', False)}
        tracevals['employeelist'] = workstation.action_get_employeestr(self.mesline_id.id, workstation.id)
        tracevals['equipmentlist'] = workstation.action_get_equipmentstr(self.mesline_id.id, workstation.id)
        temptrace = self.env['aas.mes.tracing'].search([('workorder_id', '=', self.workorder_id.id), ('workcenter_id', '=', self.workcenter_id.id)], limit=1)
        if temptrace:
            temptrace.write(tracevals)
        else:
            tracevals.update({
                'workorder_id': self.workorder_id.id, 'workcenter_id': self.workcenter_id.id,
                'workstation_id': workstation.id, 'mesline_id': self.mesline_id.id, 'product_id': self.product_id.id,
                'mainorder_id': False if not self.mainorder_id else self.mainorder_id.id
            })
            self.env['aas.mes.tracing'].create(tracevals)
        if self.id == self.workorder_id.workcenter_start.id:
            tempvals = {'state': 'producing', 'produce_start': fields.Datetime.now()}
            # 子工单状态更新，开始生产
            self.workorder_id.write(tempvals)
            # 主工单状态更新，开始生产
            if self.mainorder_id and self.mainorder_id.state == 'splited':
                self.mainorder_id.write(tempvals)


    @api.multi
    def action_finish(self):
        self.ensure_one()
        mesline, workstation = self.mesline_id, self.workcenter_id.workstation_id
        if not workstation:
            raise UserError(u'工序%s还未指定工位，请联系管理员进行设置！'% self.workcenter_name)
        employeeliststr = workstation.action_get_employeestr(self.mesline_id.id, workstation.id)
        if not employeeliststr:
            raise UserError(u'当前工位%s上没有员工在岗不可以完工！'% workstation.name)
        #判断有没有上料
        feedmateriallist = self.env['aas.mes.feedmaterial'].search([('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)])
        if not feedmateriallist or len(feedmateriallist) <= 0:
            raise UserError(u'当前工位%s上没有投料不可以完工！'% workstation.name)
        wizardvals = {
            'workticket_id': self.id, 'workstation_id': workstation.id,
            'input_qty': self.input_qty, 'workcenter_id': self.workcenter_id.id
        }
        routing_id, sequence = self.workcenter_id.routing_id.id, self.workcenter_id.sequence
        if self.env['aas.mes.routing.line'].search_count([('routing_id', '=', routing_id), ('sequence', '>', sequence)]) <= 0:
            wizardvals['need_container'] = True
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
        if self.state == 'done':
            return
        badmode_qty = 0.0
        if self.badmode_lines and len(self.badmode_lines) > 0:
            badmode_qty = sum([bline.badmode_qty for bline in self.badmode_lines])
        self.write({'time_finish': fields.Datetime.now(), 'state': 'done', 'badmode_qty': badmode_qty})
        # 更新追溯信息
        self.action_refresh_tracing()
        # 计算物料消耗
        self.action_material_consume()
        # 创建下一个工票，或工单完成
        self.action_after_done()


    @api.one
    def action_refresh_tracing(self):
        workstation = self.workcenter_id.workstation_id
        temptrace = self.env['aas.mes.tracing'].search([('workorder_id', '=', self.workorder_id.id), ('workcenter_id', '=', self.workcenter_id.id)], limit=1)
        if not temptrace:
            temptrace = self.env['aas.mes.tracing'].create({
                'workorder_id': self.workorder_id.id, 'workcenter_id': self.workcenter_id.id,
                'workstation_id': workstation.id, 'product_id': self.product_id.id, 'mesline_id': self.mesline_id.id,
                'schedule_id': False if not self.schedule_id else self.schedule_id.id,
                'mainorder_id': False if not self.mainorder_id else self.mainorder_id.id
            })
        tracevals = {'date_finish': fields.Datetime.now()}
        employeelist = [] if not temptrace.employeelist else temptrace.employeelist.split(',')
        employeestr, addemployee = workstation.action_get_employeestr(self.mesline_id.id, workstation.id), False
        if employeestr:
            for tempstr in employeestr.split(','):
                if tempstr not in employeelist:
                    employeelist.append(tempstr)
                    addemployee = True
        if addemployee:
            tracevals['employeelist'] = ','.join(employeelist)
        equipmentlist = [] if not temptrace.equipmentlist else temptrace.equipmentlist.split(',')
        equipmentstr, addequipment = workstation.action_get_equipmentstr(self.mesline_id.id, workstation.id), False
        if equipmentstr:
            for tempstr in equipmentstr.split(','):
                if tempstr not in equipmentlist:
                    equipmentlist.append(tempstr)
                    addequipment = True
        if addequipment:
            tracevals['equipmentlist'] = ','.join(equipmentlist)
        temptrace.write(tracevals)


    @api.one
    def action_material_consume(self):
        """
        计算物料消耗
        :return:
        """
        workorder, workcenter = self.workorder_id, self.workcenter_id
        product, workstation = self.product_id, workcenter.workstation_id
        if not workstation:
            raise UserError(u'还未设置工位，请先设置工序工位！')
        consumedomain = [('workorder_id', '=', workorder.id), ('workcenter_id', '=', workcenter.id), ('product_id', '=', product.id)]
        consumelist = self.env['aas.mes.workorder.consume'].search(consumedomain)
        if not consumelist or len(consumelist) <= 0:
            return
        destlocationid, companyid = self.env.ref('stock.location_production').id, self.env.user.company_id.id
        tracing = self.env['aas.mes.tracing'].search([('workorder_id', '=', workorder.id), ('workcenter_id', '=', workcenter.id)], limit=1)
        movevallist, consumelines, materiallist, movelist = [], [], [], self.env['stock.move']
        for tempconsume in consumelist:
            want_qty, material = tempconsume.consume_unit * self.input_qty, tempconsume.material_id
            feeddomain = [('workstation_id', '=', workstation.id), ('material_id', '=', material.id), ('mesline_id', '=', self.mesline_id.id)]
            feedmateriallist = self.env['aas.mes.feedmaterial'].search(feeddomain)
            if not feedmateriallist or len(feedmateriallist) <= 0:
                raise UserError(u'当前工位上原料%s还没投料，请先投料再继续操作！'% material.default_code)
            quant_qty = 0.0
            for feedmaterial in feedmateriallist:
                if float_compare(want_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                    break
                quants = feedmaterial.action_checking_quants()
                quant_qty += feedmaterial.material_qty
                if quants and len(quants) > 0:
                    for quant in quants:
                        if float_compare(want_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                            break
                        if float_compare(want_qty, quant.qty, precision_rounding=0.000001) <= 0.0:
                            tempqty = want_qty
                        else:
                            tempqty = quant.qty
                        materiallist.append(quant.product_id.default_code+'['+quant.lot_id.name+']')
                        moveval = {
                            'name': self.name, 'product_id': material.id,
                            'company_id': companyid, 'trace_id': tracing.id,
                            'product_uom': material.uom_id.id, 'create_date': fields.Datetime.now(),
                            'location_id': quant.location_id.id, 'location_dest_id': destlocationid,
                            'restrict_lot_id': quant.lot_id.id, 'product_uom_qty': tempqty
                        }
                        movevallist.append(moveval)
            if float_compare(quant_qty, want_qty, precision_rounding=0.000001) < 0.0:
                raise UserError(u'当前工位上原料%s投料不足，请先继续投料再进行其他操作！'% material.default_code)
            consumelines.append((1, tempconsume.id, {'consume_qty': tempconsume.consume_qty+want_qty}))
        if movevallist and len(movevallist) > 0:
            for moveval in movevallist:
                movelist |= self.env['stock.move'].create(moveval)
        if movelist and len(movelist) > 0:
            movelist.action_done()
        if materiallist and len(materiallist) > 0:
            tracing.write({'materiallist': ','.join(materiallist)})
        workorder.write({'consume_lines': consumelines})
        # 刷新上料记录库存
        feeddomain = [('workstation_id', '=', workstation.id), ('mesline_id', '=', self.mesline_id.id)]
        feedmateriallist = self.env['aas.mes.feedmaterial'].search(feeddomain)
        if feedmateriallist and len(feedmateriallist) > 0:
            for feedmaterial in feedmateriallist:
                feedmaterial.action_refresh_stock()


    @api.one
    def action_after_done(self):
        workorder, currentworkcenter = self.workorder_id, self.workcenter_id
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
            workordervals = {'workcenter_id': tempworkcenter.id, 'workcenter_name': nextworkcenter.name}
            if float_compare(self.badmode_qty, 0.0, precision_rounding=0.000001) > 0.0:
                consumedomain = [('workorder_id', '=', workorder.id), ('workcenter_id', '=', nextworkcenter.id)]
                consumedomain.append(('product_id', '=', self.product_id.id))
                consumelist = self.env['aas.mes.workorder.consume'].search(consumedomain)
                if consumelist and len(consumelist) > 0:
                    consumelines = []
                    for tempconsume in consumelist:
                        consumelines.append((1, tempconsume.id, {'input_qty': self.output_qty*tempconsume.consume_unit}))
                    workordervals['consume_lines'] = consumelines
            workorder.write(workordervals)
        else:
            # 工单完工
            mesline, product = workorder.mesline_id, self.product_id
            if not mesline.workdate:
                mesline.action_refresh_schedule()
            lotname = mesline.workdate.replace('-', '')
            product_lot = self.env['stock.production.lot'].action_checkout_lot(self.product_id.id, lotname)
            workorder.write({
                'workcenter_id': False, 'workcenter_name': False, 'workcenter_finish': self.id,
                'product_lines': [(0, 0, {
                    'mesline_id': mesline.id, 'product_id': product.id, 'product_qty': self.output_qty,
                    'product_lot': product_lot.id, 'output_date': self.mesline_id.workdate,
                    'container_id': False if not self.container_id else self.container_id.id,
                    'schedule_id': False if not self.mesline_id.schedule_id else self.mesline_id.schedule_id.id
                })]
            })
            self.workorder_id.action_done()
            # 容器产品进入库存
            if self.container_id:
                self.env['aas.container.product'].create({
                    'container_id': self.container_id.id, 'product_id': product.id,
                    'product_lot': product_lot.id, 'temp_qty': self.output_qty
                }).action_stock(self.output_qty)
            # 刷新成品批次
            tracelist = self.env['aas.mes.tracing'].search([('workorder_id', '=', workorder.id), ('product_id', '=', product.id)])
            if tracelist and len(tracelist) > 0:
                tracelist.write({'product_lot': product_lot.id, 'product_lot_name': product_lot.name})

    @api.multi
    def islastworkcenter(self):
        """
        验证是否是最后一道工序
        :return:
        """
        self.ensure_one()
        routing_id, sequence = self.routing_id.id, self.sequence
        workcenterlist = self.env['aas.mes.routing.line'].search([('routing_id', '=', routing_id), ('sequence', '>', sequence)])
        if workcenterlist and len(workcenterlist) > 0:
            return False
        else:
            return True








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

    need_container = fields.Boolean(string=u'需要容器', default=False, copy=False)
    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='restrict')

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
        ticketval = {}
        if badmode_lines and len(badmode_lines) > 0:
            ticketval['badmode_lines'] = badmode_lines
        if self.need_container and self.container_id:
            ticketval['container_id'] = self.container_id.id
        if ticketval and len(ticketval) > 0:
            self.workticket_id.write(ticketval)
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








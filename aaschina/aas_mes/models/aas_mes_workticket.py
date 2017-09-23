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
    _order = 'workorder_id desc,seqence'

    name = fields.Char(string=u'名称', required=True, copy=False)
    barcode = fields.Char(string=u'名称', compute="_compute_barcode", store=True)
    seqence = fields.Integer(string=u'序号')
    routing_id = fields.Many2one(comodel_name='aas.mes.routing', string=u'工艺', ondelete='restrict')
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    input_qty = fields.Float(string=u'投入数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    output_qty = fields.Float(string=u'产出数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
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
    starter_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'开工员工', ondelete='restrict')
    finisher_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'完工员工', ondelete='restrict')



    @api.depends('name')
    def _compute_barcode(self):
        for record in self:
            record.barcode = 'AR'+record.name


    @api.multi
    def action_start(self):
        self.ensure_one()
        workstation = self.workcenter_id.workstation_id
        if not workstation:
            raise UserError(u'工序%s还未指定工位，请联系管理员进行设置！'% self.workcenter_name)
        if not workstation.employee_lines or len(workstation.employee_lines) <= 0:
            raise UserError(u'当前工位%s上没有员工在岗不可以开工！'% workstation.name)
        wizardvals = {'workticket_id': self.id, 'workstation_id': workstation.id, 'input_qty': self.input_qty}
        if len(workstation.employee_lines) == 1:
            starter = workstation.employee_lines[0]
            wizardvals['starter_id'] = starter.id
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
    def action_doing_start(self, starter_id, input_qty):
        workstation = self.workcenter_id.workstation_id
        self.write({
            'starter_id': starter_id, 'time_start': fields.Datetime.now(),
            'input_qty': input_qty, 'state': 'producing'
        })
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
        wizardvals = {'workticket_id': self.id, 'workstation_id': workstation.id, 'output_qty': self.input_qty}
        if len(workstation.employee_lines) == 1:
            starter = workstation.employee_lines[0]
            wizardvals['finisher_id'] = starter.id
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
    def action_doing_finish(self, finisher_id, output_qty):
        workstation = self.workcenter_id.workstation_id
        self.write({
            'finisher_id': finisher_id, 'time_finish': fields.Datetime.now(),
            'output_qty': output_qty, 'state': 'done'
        })
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
        # 计算物料消耗
        self.action_material_consume(temptrace)
        # 创建下一个工票，或工单完成
        self.action_after_done()

    @api.one
    def action_after_done(self):
        nextworkcenter = self.env['aas.mes.routing.line'].search([('routing_id', '=', self.routing_id.id), ('sequence', '>', self.seqence)],
                                                                 order='routing_id desc,sequence', limit=1)
        if nextworkcenter:
            tempworkcenter = self.env['aas.mes.workticket'].create({
                'name': self.workorder_id.name+'-'+nextworkcenter.sequence, 'sequence': nextworkcenter.sequence,
                'routing_id': self.routing_id.id, 'workcenter_id': nextworkcenter.id,
                'workcenter_name': nextworkcenter.name, 'product_id': self.product_id.id,
                'product_uom': self.product_uom.id, 'input_qty': self.output_qty,
                'state': 'waiting', 'time_wait': fields.Datetime.now(),
                'workorder_id': self.workorder_id.id, 'workorder_name': self.workorder_name,
                'mainorder_id': False if not self.mainorder_id else self.mainorder_id.id,
                'mainorder_name': self.mainorder_name, 'mesline_id': self.mesline_id.id,
                'mesline_name': self.mesline_name
            })
            self.workorder_id.write({
                'workcenter_id': tempworkcenter.id, 'workcenter_name': nextworkcenter.name
            })
        else:
            self.workorder_id.write({'workcenter_id': False, 'workcenter_name': False, 'workcenter_finish': self.id})
            self.workorder_id.action_done()

    @api.one
    def action_material_consume(self, tracing):
        """
        计算物料消耗
        :param tracing:
        :return:
        """
        pass









################################################向导########################################

# 开工向导
class AASMESWorkticketStartWizard(models.TransientModel):
    _name = 'aas.mes.workticket.start.wizard'
    _description = 'AAS MES Workstation Start Wizard'


    workticket_id = fields.Many2one(comodel_name='aas.mes.workticket', string=u'工票', ondelete='cascade')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位')
    starter_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'开工员工')
    selecter_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'开工员工')
    input_qty = fields.Float(string=u'投入数量', digits=dp.get_precision('Product Unit of Measure'))

    @api.one
    def action_done(self):
        if not self.starter_id and not self.selecter_id:
            raise UserError(u'当前工位%s上可能没有员工在岗，请相关员工先刷卡上岗！'% self.workstation_id.name)
        if not self.input_qty or float_compare(self.input_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise UserError(u'投入数量必须是一个大于0的数！')
        tempemployee = self.selecter_id if not self.starter_id else self.starter_id
        self.workticket_id.action_doing_start(tempemployee.id, self.input_qty)



# 完工向导
class AASMESWorkticketFinishWizard(models.TransientModel):
    _name = 'aas.mes.workticket.finish.wizard'
    _description = 'AAS MES Workstation Finish Wizard'


    workticket_id = fields.Many2one(comodel_name='aas.mes.workticket', string=u'工票', ondelete='cascade')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位')
    finisher_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'玩工员工')
    selecter_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'玩工员工')
    output_qty = fields.Float(string=u'产出数量', digits=dp.get_precision('Product Unit of Measure'))

    @api.one
    def action_done(self):
        if not self.finisher_id and not self.selecter_id:
            raise UserError(u'当前工位%s上可能没有员工在岗，请相关员工先刷卡上岗！'% self.workstation_id.name)
        if not self.output_qty or float_compare(self.output_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise UserError(u'投入数量必须是一个大于0的数！')
        tempemployee = self.selecter_id if not self.finisher_id else self.finisher_id
        self.workticket_id.action_doing_finish(tempemployee.id, self.output_qty)




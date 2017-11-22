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
TICKETSTATEDICT = {'draft': u'草稿', 'waiting': u'等待', 'producing': u'生产', 'pause': u'暂停', 'done': u'完成'}

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
    output_qty = fields.Float(string=u'产出数量', digits=dp.get_precision('Product Unit of Measure'))
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
        self.write({'time_start': fields.Datetime.now(), 'state': 'producing'})
        workorder = self.workorder_id
        if self.id == workorder.workcenter_start.id:
            tempvals = {'state': 'producing', 'produce_start': fields.Datetime.now()}
            # 子工单状态更新，开始生产
            self.workorder_id.write(tempvals)
            # 主工单状态更新，开始生产
            if self.mainorder_id and self.mainorder_id.state == 'splited':
                self.mainorder_id.write(tempvals)



    @api.multi
    def action_commit(self):
        self.ensure_one()
        mesline, workstation = self.mesline_id, self.workcenter_id.workstation_id
        if not workstation:
            raise UserError(u'工序%s还未指定工位，请联系管理员进行设置！'% self.workcenter_name)
        employeeliststr = workstation.action_get_employeestr(self.mesline_id.id, workstation.id)
        if not employeeliststr:
            raise UserError(u'当前工位%s上没有员工在岗不可以完工！'% workstation.name)
        waiting_qty = self.input_qty - self.output_qty - self.badmode_qty
        # 弹出报工向导
        wizardvals = {
            'workticket_id': self.id, 'workstation_id': workstation.id,
            'waiting_qty': waiting_qty, 'workcenter_id': self.workcenter_id.id
        }
        routing_id, sequence = self.workcenter_id.routing_id.id, self.workcenter_id.sequence
        if self.env['aas.mes.routing.line'].search_count([('routing_id', '=', routing_id), ('sequence', '>', sequence)]) <= 0:
            wizardvals['need_container'] = True
        wizard = self.env['aas.mes.workticket.commit.wizard'].create(wizardvals)
        view_form = self.env.ref('aas_mes.view_form_aas_mes_workticket_commit_wizard')
        return {
            'name': u"生产报工",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.workticket.commit.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }


    @api.one
    def action_doing_commit(self, commit_qty, badmode_lines=[], container_id=False):
        ticketvals, product_output_qty = {'output_qty': self.output_qty + commit_qty}, commit_qty
        if self.islastworkcenter():
            if not container_id:
                raise UserError(u'当前工序是最后一道工序，需要先添加产出容器！')
            else:
                ticketvals['container_id'] = container_id
        if badmode_lines and len(badmode_lines) > 0:
            badmodelist, badmode_qty = [], 0.0
            for badmode in badmode_lines:
                badmodelist.append((0, 0, badmode))
                badmode_qty += badmode['badmode_qty']
            ticketvals['badmode_lines'] = badmodelist
            product_output_qty -= badmode_qty
            ticketvals['output_qty'] -= badmode_qty
            ticketvals['badmode_qty'] = badmode_qty + self.badmode_qty
        self.write(ticketvals)
        # 添加追溯信息
        temptrace = self.action_commit_tracing()
        # 消耗物料
        self.action_material_consume(temptrace, commit_qty)
        # 工单报工善后
        self.action_after_commit(temptrace, product_output_qty)



    @api.multi
    def action_commit_tracing(self):
        """
        报工信息追溯
        :return:
        """
        self.ensure_one()
        workstation = self.workcenter_id.workstation_id
        tracevals = {
            'workorder_id': self.workorder_id.id, 'workcenter_id': self.workcenter_id.id,
            'workstation_id': workstation.id, 'product_id': self.product_id.id, 'mesline_id': self.mesline_id.id,
            'schedule_id': False if not self.mesline_id.schedule_id else self.mesline_id.schedule_id.id,
            'mainorder_id': False if not self.mainorder_id else self.mainorder_id.id,
            'date_start': self.time_start if not self.time_finish else self.time_finish,
            'date_finish': fields.Datetime.now(),
            'employeelist': workstation.action_get_employeestr(self.mesline_id.id, workstation.id),
            'equipmentlist': workstation.action_get_equipmentstr(self.mesline_id.id, workstation.id)
        }
        return self.env['aas.mes.tracing'].create(tracevals)


    @api.one
    def action_material_consume(self, trace, commit_qty):
        """
        计算物料消耗
        :param trace:
        :param commit_qty:
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
        movevallist, consumelines, materiallist, movelist = [], [], [], self.env['stock.move']
        for tempconsume in consumelist:
            want_qty, material = tempconsume.consume_unit * commit_qty, tempconsume.material_id
            feeddomain = [('workstation_id', '=', workstation.id), ('material_id', '=', material.id), ('mesline_id', '=', self.mesline_id.id)]
            feedmateriallist = self.env['aas.mes.feedmaterial'].search(feeddomain)
            if not feedmateriallist or len(feedmateriallist) <= 0:
                raise UserError(u'当前工位上原料%s还没投料，请先投料再继续操作！'% material.default_code)
            quant_qty, quantdict = 0.0, {}
            for feedmaterial in feedmateriallist:
                if float_compare(want_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                    break
                quants = feedmaterial.action_checking_quants()
                quant_qty += feedmaterial.material_qty
                if quants and len(quants) > 0:
                    for quant in quants:
                        qkey = 'Q-'+str(quant.location_id.id)+'-'+str(quant.lot_id.id)
                        if qkey in quantdict:
                            quantdict[qkey]['product_qty'] += quant.qty
                        else:
                            quantdict[qkey] = {
                                'material_id': quant.product_id.id, 'material_uom': quant.product_id.uom_id.id,
                                'location_id': quant.location_id.id, 'product_lot': quant.lot_id.id, 'product_qty': quant.qty,
                                'material_code': quant.product_id.default_code, 'lot_name': quant.lot_id.name
                            }
            if float_compare(quant_qty, want_qty, precision_rounding=0.000001) < 0.0:
                raise UserError(u'当前工位上原料%s投料不足，请先继续投料再进行其他操作！'% material.default_code)
            #更新消耗信息
            consumelines.append((1, tempconsume.id, {'consume_qty': tempconsume.consume_qty+want_qty}))
            # 添加库存消耗移库信息
            for qkey, qval in quantdict.items():
                if float_compare(want_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                    break
                if float_compare(want_qty, qval['product_qty'], precision_rounding=0.000001) <= 0.0:
                    tempqty = want_qty
                else:
                    tempqty = qval['product_qty']
                materiallist.append(qval['material_code']+'['+qval['lot_name']+']')
                moveval = {
                    'name': self.name, 'product_id': qval['material_id'],
                    'company_id': companyid, 'trace_id': trace.id,
                    'product_uom': qval['material_uom'], 'create_date': fields.Datetime.now(),
                    'location_id': qval['location_id'], 'location_dest_id': destlocationid,
                    'restrict_lot_id': qval['product_lot'], 'product_uom_qty': tempqty
                }
                movevallist.append(moveval)
                want_qty -= tempqty
        if movevallist and len(movevallist) > 0:
            for moveval in movevallist:
                moverecord = self.env['stock.move'].create(moveval)
                # 如果来源库位是一个容器则需要更新容器库存信息
                tcontainer = moverecord.location_id.container_id
                if tcontainer:
                    tproduct_qty = moverecord.product_uom_qty
                    tproduct_id, tproduct_lot = moverecord.product_id.id, moverecord.restrict_lot_id.id
                    tcontainer.action_consume(tproduct_id, tproduct_lot, tproduct_qty)
                movelist |= moverecord
        if movelist and len(movelist) > 0:
            movelist.action_done()
        if materiallist and len(materiallist) > 0:
            trace.write({'materiallist': ','.join(materiallist)})
        workorder.write({'consume_lines': consumelines})
        # 刷新上料记录库存
        feeddomain = [('workstation_id', '=', workstation.id), ('mesline_id', '=', self.mesline_id.id)]
        feedmateriallist = self.env['aas.mes.feedmaterial'].search(feeddomain)
        if feedmateriallist and len(feedmateriallist) > 0:
            for feedmaterial in feedmateriallist:
                feedmaterial.action_refresh_stock()


    @api.one
    def action_after_commit(self, trace, output_qty):
        self.write({'time_finish': fields.Datetime.now()})
        workorder, mesline, product = self.workorder_id, self.workorder_id.mesline_id, self.product_id
        if not mesline.workdate:
            mesline.action_refresh_schedule()
        lotname = mesline.workdate.replace('-', '')
        product_lot = self.env['stock.production.lot'].action_checkout_lot(product.id, lotname)
        if self.islastworkcenter() and self.container_id:
            self.env['aas.mes.workorder.product'].create({
                'workorder_id': workorder.id, 'mesline_id': mesline.id, 'product_id': product.id,
                'product_lot': product_lot.id, 'product_qty': output_qty, 'output_date': mesline.workdate,
                'container_id': self.container_id.id,
                'schedule_id': False if not mesline.schedule_id else mesline.schedule_id.id
            })
            stockdomain = [('container_id', '=', self.container_id.id), ('product_id', '=', product.id)]
            stockdomain.extend([('product_lot', '=', product_lot.id), ('label_id', '=', False)])
            containerstock = self.env['aas.container.product'].search(stockdomain, limit=1)
            if not containerstock:
                containerstock = self.env['aas.container.product'].create({
                    'container_id': self.container_id.id, 'product_id': product.id,
                    'product_lot': product_lot.id, 'temp_qty': output_qty
                })
            else:
                containerstock.write({'temp_qty': containerstock.temp_qty+output_qty})
            containerstock.action_stock(output_qty)
        trace.write({'product_lot': product_lot.id, 'product_lot_name': product_lot.name})
        if float_compare(self.output_qty + self.badmode_qty, self.input_qty, precision_rounding=0.000001) < 0.0:
            return
        self.write({'state': 'done'})
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
            self.workorder_id.action_done()

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


    @api.model
    def get_workstation_workticket(self, equipment_code, barcode):
        """
        当前工位上获取工票
        :param equipment_code: 设备编码
        :param barcode: 子工单条码
        :return:
        """
        values = {'success': True, 'message': ''}
        equipment = self.env['aas.equipment.equipment'].search([('code', '=', equipment_code)], limit=1)
        if not equipment:
            values.update({'success': False, 'message': u'设备编码异常，未搜索到相应编码的设备；请仔细检查！'})
            return values
        values.update({'equipment_id': equipment.id, 'equipment_code': equipment_code})
        mesline, workstation = equipment.mesline_id, equipment.workstation_id
        if not mesline:
            values.update({'success': False, 'message': u'设备还未绑定产线，请联系相关人员设置！'})
            return values
        if not mesline.location_production_id or (not mesline.location_material_list or len(mesline.location_material_list)<= 0):
            values.update({'success': False, 'message': u'产线%s还未设置成品原料库位，请联系相关人员设置！'})
            return values
        if not workstation:
            values.update({'success': False, 'message': u'设备还未绑定工位，请联系相关人员设置！'})
            return values
        workorder = self.env['aas.mes.workorder'].search([('barcode', '=', barcode)], limit=1)
        if not workorder:
            values.update({'success': False, 'message': u'系统中未搜索到此工单，请仔细检查！'})
            return values
        if workorder.state == 'draft':
            values.update({'success': False, 'message': u'工单%s还未投入生产，请不要扫描此工单'% workorder.name})
            return values
        if workorder.state == 'done':
            values.update({'success': False, 'message': u'工单%s已完成，请不要扫描此工单'% workorder.name})
            return values
        if not workorder.workticket_lines or len(workorder.workticket_lines) <= 0:
            values.update({'success': False, 'message': u'工单异常，工单%s没有工票清单，请仔细检查！'% workorder.name})
            return values
        routing = workorder.routing_id
        workcenter = self.env['aas.mes.routing.line'].search([('routing_id', '=', routing.id), ('workstation_id', '=', workstation.id)], limit=1)
        if not workcenter:
            values.update({'success': False, 'message': u'工艺异常，可能未将工位%s设置到工艺路线中,请仔细检查！'% workstation.code})
            return values
        workticket = workorder.workcenter_id
        if workticket.workcenter_id.id != workcenter.id:
            values.update({'success': False, 'message': u'工艺异常，工位的工序和工单的工艺工序冲突，请仔细检查！'})
            return values
        actual_qty = workticket.output_qty + workticket.badmode_qty
        todo_qty = workticket.input_qty - actual_qty
        if float_compare(todo_qty, 0.0, precision_rounding=0.000001) < 0.0:
            todo_qty = 0.0
        values.update({
            'workticket_id': workticket.id, 'workticket_name': workticket.name,
            'workcenter_id': workcenter.id,'workcenter_name': workcenter.name,
            'state': TICKETSTATEDICT[workticket.state], 'sequence': workticket.sequence,
            'input_qty': workticket.input_qty, 'output_qty': workticket.output_qty, 'badmode_qty': workticket.badmode_qty,
            'actual_qty': actual_qty, 'todo_qty': todo_qty, 'lastworkcenter': workticket.islastworkcenter(),
            'schedule_name': '' if not workticket.schedule_id else workticket.schedule_id.name,
            'product_code': workticket.product_id.default_code, 'mesline_name': workticket.mesline_name,
            'time_start': '' if not workticket.time_start else fields.Datetime.to_timezone_string(workticket.time_start, 'Asia/Shanghai'),
            'time_finish': '' if not workticket.time_finish else fields.Datetime.to_timezone_string(workticket.time_finish, 'Asia/Shanghai')
        })
        return values

    @api.model
    def action_workticket_start_onstationclient(self, workticket_id, equipment_id):
        """
        工控工位客户端上开工
        :param workticket_id:
        :param equipment_id:
        :return:
        """
        values = {'success': True, 'message': ''}
        equipment = self.env['aas.equipment.equipment'].browse(equipment_id)
        mesline, workstation = equipment.mesline_id, equipment.workstation_id
        wemployees = self.env['aas.mes.workstation.employee'].search([('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)])
        if not wemployees or len(wemployees) <= 0:
            values.update({'success': False, 'message': u'当前工位上还没有员工上岗，请先让员工上岗再进行其他操作！'})
            return values
        workticket = self.env['aas.mes.workticket'].browse(workticket_id)
        workticket.action_doing_start()
        return values

    @api.model
    def action_workticket_finish_onstationclient(self, workticket_id, equipment_id, commit_qty, badmode_lines=[], container_id=False):
        """
        工控工位客户端上报工
        :param workticket_id:
        :param equipment_id:
        :param badmode_lines:
        :param container_id:
        :return:
        """
        values = {'success': True, 'message': ''}
        equipment = self.env['aas.equipment.equipment'].browse(equipment_id)
        mesline, workstation = equipment.mesline_id, equipment.workstation_id
        wemployees = self.env['aas.mes.workstation.employee'].search([('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)])
        if not wemployees or len(wemployees) <= 0:
            values.update({'success': False, 'message': u'当前工位上还没有员工上岗，请先让员工上岗再进行其他操作！'})
            return values
        workticket = self.env['aas.mes.workticket'].browse(workticket_id)
        # 更新容器或不良模式
        ticketvals = {}
        if workticket.islastworkcenter():
            if not container_id:
                values.update({'success': False, 'message': u'当前工序是工艺中最后一道工序，需要扫描产出容器！'})
                return values
            else:
                ticketvals['container_id'] = container_id
        if badmode_lines and len(badmode_lines) > 0:
            ticketvals['badmode_lines'] = [(0, 0, badmode) for badmode in badmode_lines]
        if ticketvals and len(ticketvals) > 0:
            workticket.write(ticketvals)
        # 验证物料消耗
        workorder = workticket.workorder_id
        cresult = workorder.action_validate_consume(workorder.id, workticket.product_id.id, commit_qty, workstation.id, workticket.workcenter_id.id)
        if not cresult['success']:
            values.update(cresult)
            return values
        # 消耗物料并产出
        try:
            workticket.action_doing_commit(commit_qty, badmode_lines, container_id)
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        return values









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
class AASMESWorkticketCommitWizard(models.TransientModel):
    _name = 'aas.mes.workticket.commit.wizard'
    _description = 'AAS MES Workstation Commit Wizard'


    workticket_id = fields.Many2one(comodel_name='aas.mes.workticket', string=u'工票', ondelete='cascade')
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位')
    waiting_qty = fields.Float(string=u'待产数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    commit_qty = fields.Float(string=u'报工数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    badmode_lines = fields.One2many(comodel_name='aas.mes.workticket.badmode.wizard', inverse_name='wizard_id', string=u'不良信息')

    need_container = fields.Boolean(string=u'需要容器', default=False, copy=False)
    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='restrict')

    @api.one
    def action_done(self):
        if float_compare(self.commit_qty, self.waiting_qty, precision_rounding=0.000001) > 0.0:
            raise UserError(u'报工数量不可以大于待产数量！')
        if float_compare(self.commit_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise UserError(u'报工数量必须是一个大于零的数！')
        container_id = False if not self.container_id else self.container_id.id
        if self.need_container and (not container_id):
            raise UserError(u'当前工序是最后一道工序，必须添加产出容器！')
        badmode_qty, badmode_lines = 0.0, []
        if self.badmode_lines and len(self.badmode_lines) > 0:
            for bline in self.badmode_lines:
                badmode_qty += bline.badmode_qty
                badmode = bline.badmode_id.badmode_id
                badmode_lines.append({'badmode_id': badmode.id, 'badmode_qty': bline.badmode_qty})
        if float_compare(badmode_qty, self.commit_qty, precision_rounding=0.000001) > 0.0:
            raise UserError(u'不良数量的总和不可以大于报工数量！')
        workorder, workcenter = self.workticket_id.workorder_id, self.workticket_id.workcenter_id
        workstation, product = workcenter.workstation_id, self.workticket_id.product_id
        cresult = workorder.action_validate_consume(workorder.id, product.id, self.commit_qty, workstation.id, workcenter.id)
        if not cresult['success']:
            raise UserError(cresult['message'])
        self.workticket_id.action_doing_commit(self.commit_qty, badmode_lines, container_id)

class AASMESWorkticketBadmodeWizard(models.TransientModel):
    _name = 'aas.mes.workticket.badmode.wizard'
    _description = 'AAS MES Workticket Badmode Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.mes.workticket.commit.wizard', string=u'完工向导', ondelete='cascade')
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








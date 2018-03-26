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

    # 最后一次产出的容器
    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='restrict')
    # 最后一次产出的标签
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

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
            # 子工单状态更新，开始生产
            self.workorder_id.write({
                'state': 'producing',
                'produce_start': fields.Datetime.now(), 'produce_date': fields.Datetime.to_china_today()
            })
            # 主工单状态更新，开始生产
            if self.mainorder_id and self.mainorder_id.state == 'splited':
                self.mainorder_id.write({'state': 'producing', 'produce_start': fields.Datetime.now()})



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
        badmodelist = workstation.get_badmode_list(workstation.id)
        if badmodelist and len(badmodelist) > 0:
            wizardvals['badmode_lines'] = [(0, 0, {'badmode_id': badmode.id}) for badmode in badmodelist]
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
    def action_doing_commit(self, commit_qty, badmode_lines=[], container_id=False, equipment=False):
        _logger.info(u'工票%s开始报工;当前时间：%s', self.name, fields.Datetime.now())
        ticketvals, output_qty, badmode_qty = {'output_qty': self.output_qty + commit_qty}, commit_qty, 0.0
        if badmode_lines and len(badmode_lines) > 0:
            badmodelist = []
            for badmode in badmode_lines:
                badmodelist.append((0, 0, badmode))
                badmode_qty += badmode['badmode_qty']
            ticketvals['badmode_lines'] = badmodelist
            output_qty -= badmode_qty
            ticketvals['output_qty'] -= badmode_qty
            ticketvals['badmode_qty'] = badmode_qty + self.badmode_qty
        needcontainer = self.islastworkcenter() and self.workorder_id.output_manner == 'container'
        if needcontainer:
            if not container_id and float_compare(commit_qty, badmode_qty, precision_rounding=0.000001) > 0.0:
                raise UserError(u'当前工序是最后一道工序，需要先添加产出容器！')
            else:
                self.write({'container_id': container_id})
        if float_compare(badmode_qty, commit_qty, precision_rounding=0.000001) > 0:
            raise UserError(u'不良数量不能超过上报总数！')
        # 添加追溯信息
        workcenter, mesline = self.workcenter_id, self.mesline_id
        workstation, workorder = workcenter.workstation_id, self.workorder_id
        temptrace = self.env['aas.mes.tracing'].create({
            'workorder_id': workorder.id, 'workcenter_id': workcenter.id,
            'workstation_id': workstation.id, 'product_id': self.product_id.id, 'mesline_id': mesline.id,
            'schedule_id': False if not mesline.schedule_id else mesline.schedule_id.id,
            'mainorder_id': False if not self.mainorder_id else self.mainorder_id.id,
            'date_start': self.time_start if not self.time_finish else self.time_finish,
            'date_finish': fields.Datetime.now(),
            'employeelist': workstation.action_get_employeestr(mesline.id, workstation.id),
            'equipmentlist': workstation.action_get_equipmentstr(mesline.id, workstation.id)
        })
        try:
            # 物料消耗
            self.action_workticket_consume(temptrace, commit_qty)
            # 工票产出
            self.action_workticket_output(temptrace, output_qty, badmode_qty, equipment=equipment)
            self.write(ticketvals)
            _logger.info(u'工票%s更新产出信息;当前时间：%s;产出数量%s,不良数量%s', self.name, fields.Datetime.now(), output_qty, badmode_qty)
        except UserError, ue:
            raise UserError(ue.name)
        except ValidationError, ve:
            raise ValidationError(ve.name)
        _logger.info(u'工票%s报工结束;当前时间：%s', self.name, fields.Datetime.now())


    @api.multi
    def action_workticket_consume(self, trace, commit_qty):
        """
        计算物料消耗
        :param trace:
        :param commit_qty:
        :return:
        """
        self.ensure_one()
        values = {'success': True, 'message': '', 'moveids': []}
        _logger.info(u'工票%s开始物料消耗;当前时间：%s;待消耗数量%s', self.name, fields.Datetime.now(), commit_qty)
        workorder, workcenter = self.workorder_id, self.workcenter_id
        product, workstation, mesline = self.product_id, workcenter.workstation_id, self.mesline_id
        if not workstation:
            raise UserError(u'还未设置工位，请先设置工序工位！')
        employeedomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        if self.env['aas.mes.workstation.employee'].search_count(employeedomain) <= 0:
            raise UserError(u'%s工位还没有员工在岗，请员工先上岗再继续操作！'% workstation.name)
        consumedomain = [
            ('workorder_id', '=', workorder.id), ('workcenter_id', '=', workcenter.id), ('product_id', '=', product.id)
        ]
        consumelist = self.env['aas.mes.workorder.consume'].search(consumedomain)
        if not consumelist or len(consumelist) <= 0:
            return
        materialids, materiallist = [], []
        movevallist, consumelines, movelist, moveids = [], [], self.env['stock.move'], []
        destlocationid, companyid = self.env.ref('stock.location_production').id, self.env.user.company_id.id
        for tempconsume in consumelist:
            want_qty, material = tempconsume.consume_unit * commit_qty, tempconsume.material_id
            feeddomain = [('mesline_id', '=', mesline.id), ('material_id', '=', material.id)]
            feedmateriallist = self.env['aas.mes.feedmaterial'].search(feeddomain)
            if not feedmateriallist or len(feedmateriallist) <= 0:
                raise UserError(u'当前工位上原料%s还没投料，请先投料再继续操作！'% material.default_code)
            materialids.append(material.id)
            quant_qty, quantdict = 0.0, {}
            for feedmaterial in feedmateriallist:
                if float_compare(want_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                    break
                quants = feedmaterial.action_checking_quants()
                quant_qty += feedmaterial.material_qty
                if quants and len(quants) > 0:
                    for quant in quants:
                        qkey = 'Q-'+str(quant.location_id.id)+'-'+str(quant.lot_id.id)
                        product, quantlot = quant.product_id, quant.lot_id
                        if qkey in quantdict:
                            quantdict[qkey]['product_qty'] += quant.qty
                        else:
                            quantdict[qkey] = {
                                'material_id': product.id, 'material_uom': product.uom_id.id,
                                'material_code': product.default_code, 'product_lot': quantlot.id,
                                'lot_name': quantlot.name, 'product_qty': quant.qty, 'location_id': quant.location_id.id
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
        _logger.info(u'工票%s消耗明细计算结束;当前时间：%s', self.name, fields.Datetime.now())
        if movevallist and len(movevallist) > 0:
            for moveval in movevallist:
                tmove = self.env['stock.move'].create(moveval)
                movelist |= tmove
                moveids.append(tmove.id)
        if movelist and len(movelist) > 0:
            movelist.action_done()
            _logger.info(u'工票%s库存已消耗;当前时间：%s', self.name, fields.Datetime.now())
        if materiallist and len(materiallist) > 0:
            trace.write({'materiallist': ','.join(materiallist)})
        workorder.write({'consume_lines': consumelines})
        _logger.info(u'工票%s更新消耗明细;当前时间：%s', self.name, fields.Datetime.now())
        # 刷新上料记录库存
        feeddomain = [('mesline_id', '=', mesline.id), ('material_id', 'in', materialids)]
        feedmateriallist = self.env['aas.mes.feedmaterial'].search(feeddomain)
        if feedmateriallist and len(feedmateriallist) > 0:
            feedmateriallist.action_freshandclear()
        _logger.info(u'工票%s结束物料消耗;当前时间：%s', self.name, fields.Datetime.now())
        values['moveids'] = moveids
        return values


    @api.one
    def action_workticket_output(self, trace, output_qty, badmode_qty, equipment=False):
        """工票产出和结单
        :param trace:
        :param output_qty:
        :param badmode_qty:
        :param equipment:
        :return:
        """
        _logger.info(u'工票%s开始产出;当前时间：%s;产出数量%s;不良数量%s', self.name, fields.Datetime.now(), output_qty, badmode_qty)
        workorder, mesline, product = self.workorder_id, self.workorder_id.mesline_id, self.product_id
        if not mesline.workdate:
            mesline.action_refresh_schedule()
        # 再次判断是否还是没有工作日
        if not mesline.workdate:
            lotname = fields.Datetime.to_china_today().replace('-', '')
        else:
            lotname = mesline.workdate.replace('-', '')
        if equipment and equipment.sequenceno:
            lotname += equipment.sequenceno
        product_lot = self.env['stock.production.lot'].action_checkout_lot(product.id, lotname)
        trace.write({'product_lot': product_lot.id, 'product_lot_name': product_lot.name})
        if self.islastworkcenter():
            if workorder.output_manner == 'container' and self.container_id:
                self.action_output2container(product_lot, output_qty, self.container_id.id, badmode_qty)
            if workorder.output_manner == 'label':
                self.action_output2label(product_lot, output_qty, badmode_qty)
        # 根据结单方式判断什么时候自动结单
        closeorder = self.env['ir.values'].sudo().get_default('aas.mes.settings', 'closeorder_method')
        if closeorder == 'equal':
            if float_compare(self.output_qty, self.input_qty, precision_rounding=0.000001) >= 0.0:
                self.action_workticket_done()
        else:  # total
            total_qty = self.output_qty + self.badmode_qty
            if float_compare(total_qty, self.input_qty, precision_rounding=0.000001) >= 0.0:
                self.action_workticket_done()
        _logger.info(u'工票%s产出结束;当前时间：%s', self.name, fields.Datetime.now())
        # 产出优率记录 #############################################################
        self.action_update_productionout(product.id, self.workcenter_id.workstation_id.id, mesline, output_qty, badmode_qty)

    @api.model
    def action_update_productionout(self, productid, workstationid, mesline, output_qty, badmode_qty):
        """更新产出优率记录
        :param productid:
        :param workstationid:
        :param mesline:
        :param output_qty:
        :param badmode_qty:
        :return:
        """
        employeeid, employeename, equipmentid = False, False, False
        scheduleid = False if not mesline.schedule_id else mesline.schedule_id.id
        stationdomain = [('workstation_id', '=', workstationid), ('mesline_id', '=', mesline.id)]
        temployee = self.env['aas.mes.workstation.employee'].search(stationdomain, limit=1)
        if temployee:
            employeeid, employeename = temployee.employee_id.id, temployee.employee_id.name
        tequipment = self.env['aas.mes.workstation.equipment'].search(stationdomain, limit=1)
        if tequipment:
            equipmentid = tequipment.equipment_id.id
        if float_compare(output_qty, 0.0, precision_rounding=0.000001) > 0.0:
            self.env['aas.mes.production.output'].create({
                'product_id': productid, 'output_date': mesline.workdate, 'output_qty': output_qty,
                'mesline_id': mesline.id, 'schedule_id': scheduleid, 'workstation_id': workstationid,
                'qualified': True, 'pass_onetime': True, 'equipment_id': equipmentid, 'employee_id': employeeid,
                'employee_name': employeename
            })
        if float_compare(badmode_qty, 0.0, precision_rounding=0.000001) > 0.0:
            self.env['aas.mes.production.output'].create({
                'product_id': productid, 'output_date': mesline.workdate, 'output_qty': badmode_qty,
                'mesline_id': mesline.id, 'schedule_id': scheduleid, 'workstation_id': workstationid,
                'qualified': False, 'pass_onetime': False, 'equipment_id': equipmentid, 'employee_id': employeeid,
                'employee_name': employeename
            })


    @api.one
    def action_output2container(self, product_lot, output_qty, container_id, badmode_qty=0.0):
        """产出到容器
        :param product_lot:
        :param output_qty:
        :param container_id:
        :return:
        """
        _logger.info(u'工票%s容器产出;当前时间：%s', self.name, fields.Datetime.now())
        workorder = self.workorder_id
        mesline, product = workorder.mesline_id, workorder.product_id
        scheduleid = False if not mesline.schedule_id else mesline.schedule_id.id
        tempoutput = self.env['aas.mes.workorder.product'].create({
            'workorder_id': workorder.id, 'mesline_id': mesline.id,
            'product_id': product.id, 'product_lot': product_lot.id,
            'product_qty': output_qty, 'output_date': mesline.workdate,
            'schedule_id': scheduleid, 'badmode_qty': badmode_qty
        })
        if float_compare(output_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            return
        tempcontainer = self.env['aas.container'].browse(container_id)
        if tempcontainer.location_id.id != mesline.location_production_id.id:
            tempcontainer.action_domove(mesline.location_production_id.id, movenote=u'成品产出容器自动调拨库位！')
        stockdomain = [('container_id', '=', container_id)]
        stockdomain += [('product_id', '=', product.id), ('product_lot', '=', product_lot.id)]
        containerstock = self.env['aas.container.product'].search(stockdomain, limit=1)
        if not containerstock:
            containerstock = self.env['aas.container.product'].create({
                'container_id': self.container_id.id, 'product_id': product.id,
                'product_lot': product_lot.id, 'temp_qty': output_qty
            })
        else:
            containerstock.write({'temp_qty': containerstock.temp_qty+output_qty})
        containerstock.action_stock(output_qty)
        tempoutput.write({'container_id': container_id})
        _logger.info(u'工票%s容器产出到容器;当前容器：%s', self.name, tempoutput.container_id.name)




    @api.one
    def action_output2label(self, product_lot, output_qty, badmode_qty=0.0):
        """产出到标签
        :param product_lot:
        :param output_qty:
        :return:
        """
        _logger.info(u'工票%s标签产出;当前时间：%s', self.name, fields.Datetime.now())
        workorder = self.workorder_id
        mesline, product = workorder.mesline_id, workorder.product_id
        scheduleid = False if not mesline.schedule_id else mesline.schedule_id.id
        tempoutput = self.env['aas.mes.workorder.product'].create({
            'workorder_id': workorder.id, 'mesline_id': mesline.id,
            'product_id': product.id, 'product_lot': product_lot.id,
            'product_qty': output_qty, 'output_date': mesline.workdate,
            'schedule_id': scheduleid, 'badmode_qty': badmode_qty
        })
        if float_compare(output_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            return
        label = self.env['aas.product.label'].create({
            'product_id': product.id, 'product_lot': product_lot.id, 'stocked': True,
            'product_qty': output_qty, 'location_id': mesline.location_production_id.id
        })
        label.action_stock(self.env.ref('stock.location_production').id)
        tempoutput.write({'label_id': label.id})
        self.write({'label_id': label.id})
        _logger.info(u'工票%s容器产出到标签;当前标签：%s', self.name, label.name)


    @api.one
    def action_workticket_done(self):
        """结束当前工票
        :return:
        """
        _logger.info(u'工票%s完工;当前时间：%s', self.name, fields.Datetime.now())
        self.write({'state': 'done', 'time_finish': fields.Datetime.now()})
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
            _logger.info(u'工票%s完工创建新工票%s;当前时间：%s', self.name, tempworkcenter.name, fields.Datetime.now())
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
            workorder.action_done()
            _logger.info(u'工票%s完工;工单%s完工;当前时间：%s', self.name, workorder.name, fields.Datetime.now())




    @api.multi
    def islastworkcenter(self):
        """
        验证是否是最后一道工序
        :return:
        """
        self.ensure_one()
        routing_id, sequence = self.routing_id.id, self.sequence
        tempdomain = [('routing_id', '=', routing_id), ('sequence', '>', sequence)]
        workcenterlist = self.env['aas.mes.routing.line'].search(tempdomain)
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
            'workorder_id': workorder.id, 'workorder_name': workorder.name,
            'workcenter_id': workcenter.id,'workcenter_name': workcenter.name,
            'workticket_id': workticket.id, 'workticket_name': workticket.name,
            'state': TICKETSTATEDICT[workticket.state], 'sequence': workticket.sequence,
            'mainorder_id': 0 if not workorder.mainorder_id else workorder.mainorder_id.id,
            'mainorder_name': '' if not workorder.mainorder_id else  workorder.mainorder_id.name,
            'input_qty': workticket.input_qty, 'output_qty': workticket.output_qty, 'badmode_qty': workticket.badmode_qty,
            'actual_qty': actual_qty, 'todo_qty': todo_qty, 'lastworkcenter': workticket.islastworkcenter(),
            'schedule_name': '' if not workticket.schedule_id else workticket.schedule_id.name,
            'product_code': workticket.product_id.default_code, 'mesline_name': workticket.mesline_name,
            'time_start': fields.Datetime.to_china_string(workticket.time_start),
            'time_finish': fields.Datetime.to_china_string(workticket.time_finish),
            'output_manner': workorder.output_manner,
            'finalproduct_id': workticket.product_id.id,
            'finalproduct_code': workticket.product_id.default_code
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
        if workticket.state == 'producing':
            values.update({'success': False, 'message': u'当前工票已经开工，请不要重复操作！'})
            return values
        workticket.action_doing_start()
        return values

    @api.model
    def action_workticket_finish_onstationclient(self, workticket_id, equipment_id, commit_qty,
                                                 badmode_lines=[], container_id=False):
        """
        工控工位客户端上报工
        :param workticket_id:
        :param equipment_id:
        :param badmode_lines:
        :param container_id:
        :return:
        """
        values = {'success': True, 'message': '', 'label_id': 0}
        equipment = self.env['aas.equipment.equipment'].browse(equipment_id)
        meslineid, workstationid = equipment.mesline_id.id, equipment.workstation_id.id
        tempdomain = [('mesline_id', '=', meslineid), ('workstation_id', '=', workstationid)]
        wemployees = self.env['aas.mes.workstation.employee'].search(tempdomain)
        if not wemployees or len(wemployees) <= 0:
            values.update({'success': False, 'message': u'当前工位上还没有员工上岗，请先让员工上岗再进行其他操作！'})
            return values
        workticket = self.env['aas.mes.workticket'].browse(workticket_id)
        if not workticket:
            values.update({'success': False, 'message': u'工票%s异常，可能已删除！'% workticket.name})
            return values
        # 消耗物料并产出
        try:
            workticket.action_doing_commit(commit_qty, badmode_lines, container_id=container_id, equipment=equipment)
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        except ValidationError, ve:
            values.update({'success': False, 'message': ve.name})
            return values
        if workticket.label_id:
            values['label_id'] = workticket.label_id.id
        return values


class AASMESWorkticketBadmode(models.Model):
    _name = 'aas.mes.workticket.badmode'
    _description = 'AAS MES Workticket Badmode'
    _rec_name = 'badmode_id'


    workticket_id = fields.Many2one(comodel_name='aas.mes.workticket', string=u'工票', ondelete='cascade', index=True)
    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', ondelete='cascade', index=True)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade', index=True)
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade', index=True)
    badmode_id = fields.Many2one(comodel_name='aas.mes.badmode', string=u'不良模式', ondelete='restrict')
    badmode_qty = fields.Float(string=u'不良数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    @api.model
    def create(self, vals):
        record = super(AASMESWorkticketBadmode, self).create(vals)
        tempworkticket = record.workticket_id
        if tempworkticket:
            record.write({
                'workorder_id': tempworkticket.workorder_id.id, 'product_id': tempworkticket.product_id.id,
                'workcenter_id': tempworkticket.workcenter_id.id,
                'workstation_id': tempworkticket.workcenter_id.workstation_id.id,
                'mesline_id': tempworkticket.workorder_id.mesline_id.id
            })
        return record







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
        self.workticket_id.action_doing_start()



# 完工向导
class AASMESWorkticketCommitWizard(models.TransientModel):
    _name = 'aas.mes.workticket.commit.wizard'
    _description = 'AAS MES Workstation Commit Wizard'


    workticket_id = fields.Many2one(comodel_name='aas.mes.workticket', string=u'工票', ondelete='cascade')
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='cascade')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位')
    waiting_qty = fields.Float(string=u'待产数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    commit_qty = fields.Float(string=u'报工数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    badmode_lines = fields.One2many(comodel_name='aas.mes.workticket.badmode.wizard', inverse_name='wizard_id', string=u'不良信息')
    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='restrict')

    @api.one
    def action_done(self):
        if float_compare(self.commit_qty, self.waiting_qty, precision_rounding=0.000001) > 0.0:
            raise UserError(u'报工数量不可以大于待产数量！')
        if float_compare(self.commit_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise UserError(u'报工数量必须是一个大于零的数！')

        container_id = False if not self.container_id else self.container_id.id
        workticket = self.workticket_id
        workorder, workcenter = workticket.workorder_id, workticket.workcenter_id
        if workticket.islastworkcenter():
            manner = workorder.output_manner
            if not manner:
                raise UserError(u'请先在工单上设置产出方式！')
            if not container_id and manner == 'container':
                raise UserError(u'当前工序是最后一道工序，需要产出到容器，请先设置容器！')
        badmode_qty, badmode_lines = 0.0, []
        if self.badmode_lines and len(self.badmode_lines) > 0:
            for bline in self.badmode_lines:
                if float_compare(bline.badmode_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                    continue
                badmode_qty += bline.badmode_qty
                badmode = bline.badmode_id.badmode_id
                badmode_lines.append({'badmode_id': badmode.id, 'badmode_qty': bline.badmode_qty})
        if float_compare(badmode_qty, self.commit_qty, precision_rounding=0.000001) > 0.0:
            raise UserError(u'不良数量的总和不可以大于报工数量！')
        workstationid, productid = workcenter.workstation_id.id, workticket.product_id.id
        workorderid, workcenterid, commitqty = workorder.id, workcenter.id, self.commit_qty
        cresult = workorder.action_validate_consume(workorderid, productid, commitqty, workcenter_id=workcenterid)
        if not cresult.get('success', False):
            raise UserError(cresult['message'])
        workticket.action_doing_commit(commitqty, badmode_lines, container_id=container_id)

class AASMESWorkticketBadmodeWizard(models.TransientModel):
    _name = 'aas.mes.workticket.badmode.wizard'
    _description = 'AAS MES Workticket Badmode Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.mes.workticket.commit.wizard', string=u'完工向导', ondelete='cascade')
    badmode_id = fields.Many2one(comodel_name='aas.mes.badmode', string=u'不良模式', ondelete='cascade')
    badmode_qty = fields.Float(string=u'不良数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    _sql_constraints = [
        ('uniq_badmode', 'unique (wizard_id, badmode_id)', u'请不要重复添加同一个不良模式！')
    ]

    @api.one
    @api.constrains('badmode_qty')
    def action_check_badmode_qty(self):
        if self.badmode_qty and float_compare(self.badmode_qty, 0.0, precision_rounding=0.000001) < 0.0:
            raise ValidationError(u'不良数量不能小于零的数！')








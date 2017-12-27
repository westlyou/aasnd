# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-9-21 14:47
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError
from . import MESLINETYPE

import logging

_logger = logging.getLogger(__name__)

# 子工单

ORDERSTATES = [('draft', u'草稿'), ('confirm', u'确认'), ('producing', u'生产'), ('pause', u'暂停'), ('done', u'完成')]

class AASMESWorkorder(models.Model):
    _name = 'aas.mes.workorder'
    _description = 'AAS MES Work Order'
    _order = 'id desc'

    name = fields.Char(string=u'名称', required=True, copy=False, index=True)
    barcode = fields.Char(string=u'条码', compute='_compute_barcode', store=True, index=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', required=True, index=True)
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    input_qty = fields.Float(string=u'计划数量', digits=dp.get_precision('Product Unit of Measure'), default=1.0)
    aas_bom_id = fields.Many2one(comodel_name='aas.mes.bom', string=u'物料清单', ondelete='restrict', index=True)
    routing_id = fields.Many2one(comodel_name='aas.mes.routing', string=u'工艺路线', ondelete='restrict', index=True)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict', index=True)
    time_create = fields.Datetime(string=u'创建时间', default=fields.Datetime.now, copy=False)
    time_finish = fields.Datetime(string=u'完成时间', copy=False)
    creator_id = fields.Many2one(comodel_name='res.users', string=u'创建人', ondelete='restrict', default=lambda self: self.env.user)
    state = fields.Selection(selection=ORDERSTATES, string=u'状态', default='draft', copy=False)
    produce_start = fields.Datetime(string=u'开始生产', copy=False)
    produce_finish = fields.Datetime(string=u'结束生产', copy=False)
    date_code = fields.Char(string='DateCode')
    mainorder_id = fields.Many2one(comodel_name='aas.mes.mainorder', string=u'主工单', ondelete='cascade', index=True)
    wireorder_id = fields.Many2one(comodel_name='aas.mes.wireorder', string=u'线材工单', ondelete='cascade', index=True)
    mesline_type = fields.Selection(selection=MESLINETYPE, string=u'产线类型', compute='_compute_mesline', store=True)
    mesline_name = fields.Char(string=u'产线名称', compute='_compute_mesline', store=True)
    mainorder_name = fields.Char(string=u'主工单', compute='_compute_mainorder', store=True)
    product_code = fields.Char(string=u'产品编码', copy=False)
    workcenter_id = fields.Many2one(comodel_name='aas.mes.workticket', string=u'当前工序', ondelete='restrict')
    workcenter_name = fields.Char(string=u'当前工序名称', copy=False)
    workcenter_start = fields.Many2one(comodel_name='aas.mes.workticket', string=u'开始工序', ondelete='restrict')
    workcenter_finish = fields.Many2one(comodel_name='aas.mes.workticket', string=u'结束工序', ondelete='restrict')
    isproducing = fields.Boolean(string=u'正在生产', default=False, copy=False, help=u'当前工单在相应的产线上正在生产')
    output_qty = fields.Float(string=u'产出数量', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_orderoutput', store=True)
    waitconsume = fields.Boolean(string=u'等待物料', copy=False, compute='_compute_orderoutput', store=True, help=u'已经成品产出，因原料不足等待中')
    closer_id = fields.Many2one(comodel_name='res.users', string=u'手工关单员', ondelete='restrict', copy=False)
    output_time = fields.Datetime(string=u'产出时间', copy=False, help=u'最近一次产出的时间')
    scrap_qty = fields.Float(string=u'报废数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    workticket_lines = fields.One2many(comodel_name='aas.mes.workticket', inverse_name='workorder_id', string=u'工票明细')
    product_lines = fields.One2many(comodel_name='aas.mes.workorder.product', inverse_name='workorder_id', string=u'成品明细')
    consume_lines = fields.One2many(comodel_name='aas.mes.workorder.consume', inverse_name='workorder_id', string=u'消耗明细')

    _sql_constraints = [
        ('uniq_name', 'unique (name)', u'子工单名称不可以重复！')
    ]

    @api.model
    def default_get(self, fields_list):
        defaults = super(AASMESWorkorder,self).default_get(fields_list)
        defaults['name'] = fields.Datetime.to_timezone_time(fields.Datetime.now(), 'Asia/Shanghai').strftime('%Y%m%d%H%M%S')
        return defaults

    @api.depends('mesline_id')
    def _compute_mesline(self):
        for record in self:
            record.mesline_type = record.mesline_id.line_type
            record.mesline_name = record.mesline_id.name

    @api.depends('name')
    def _compute_barcode(self):
        for record in self:
            record.barcode = 'AQ'+record.name

    @api.depends('mainorder_id')
    def _compute_mainorder(self):
        for record in self:
            record.mainorder_name = record.mainorder_id.name

    @api.depends('product_lines.waiting_qty')
    def _compute_orderoutput(self):
        for record in self:
            tempqty, waitconsume = 0.0, False
            if record.product_lines and len(record.product_lines) > 0:
                for pline in record.product_lines:
                    if pline.product_id.id == record.product_id.id:
                        tempqty += pline.product_qty
                    if float_compare(pline.waiting_qty, 0.0, precision_rounding=0.000001) > 0.0:
                        waitconsume = True
            record.output_qty = tempqty
            record.waitconsume = waitconsume


    @api.one
    @api.constrains('aas_bom_id', 'input_qty')
    def action_check_mainorder(self):
        if not self.input_qty or float_compare(self.input_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise ValidationError(u'投入数量必须是一个有效的正数！')
        if self.aas_bom_id and self.aas_bom_id.product_id.id != self.product_id.id:
            raise ValidationError(u'请仔细检查，当前物料清单和产品不匹配！')

    @api.onchange('product_id')
    def action_change_product(self):
        if not self.product_id:
            self.product_code = False
            self.product_uom, self.aas_bom_id, self.routing_id = False, False, False
        else:
            self.product_uom = self.product_id.uom_id.id
            self.product_code = self.product_id.default_code
            aasbom = self.env['aas.mes.bom'].search([('product_id', '=', self.product_id.id)], order='create_time desc', limit=1)
            if aasbom:
                self.aas_bom_id = aasbom.id
                if aasbom.routing_id:
                    self.routing_id = aasbom.routing_id.id

    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        return super(AASMESWorkorder, self).create(vals)

    @api.model
    def action_before_create(self, vals):
        product = self.env['product.product'].browse(vals.get('product_id'))
        if not vals.get('product_code', False):
            vals['product_code'] = product.default_code
        if not vals.get('product_uom', False):
                vals['product_uom'] = product.uom_id.id
        if not vals.get('aas_bom_id', False):
            bomdomain = [('product_id', '=', self.product_id.id), ('state', '=', 'normal')]
            aasbom = self.env['aas.mes.bom'].search(bomdomain, order='create_time desc', limit=1)
            if aasbom:
                vals['aas_bom_id'] = aasbom.id
                if aasbom.routing_id:
                    vals['routing_id'] = aasbom.routing_id.id
        if not vals.get('routing_id', False):
            if vals.get('aas_bom_id', False):
                aasbom = self.env['aas.mes.bom'].browse(vals.get('aas_bom_id'))
                if aasbom.routing_id:
                    vals['routing_id'] = aasbom.routing_id.id

    @api.multi
    def write(self, vals):
        if vals.get('product_id', False):
            raise UserError(u'您可以删除并重新创建工单，但是不要修改产品信息！')
        return super(AASMESWorkorder, self).write(vals)

    @api.multi
    def unlink(self):
        for record in self:
            if record.state not in ['draft', 'confirm']:
                raise UserError(u'工单%s已经开始执行或已经完成，请不要删除！'% record.name)
        return super(AASMESWorkorder, self).unlink()

    @api.one
    def action_pause(self):
        self.write({'state': 'pause'})

    @api.one
    def action_confirm(self):
        """
        确认工单；工位式生产工单需要生成首道工序工票；生成物料消耗清单
        :return:
        """
        self.write({'state': 'confirm'})
        self.action_build_first_workticket()
        self.action_build_consumelist()


    @api.one
    def action_build_first_workticket(self):
        """
        工位式生产的工单生成首道工序的工票
        :return:
        """
        if not self.routing_id or self.mesline_type != 'station':
            return
        domain = [('routing_id', '=', self.routing_id.id)]
        routline = self.env['aas.mes.routing.line'].search(domain, order='sequence', limit=1)
        workticket = self.env['aas.mes.workticket'].create({
            'name': self.name+'-'+str(routline.sequence), 'sequence': routline.sequence,
            'workcenter_id': routline.id, 'workcenter_name': routline.name,
            'product_id': self.product_id.id, 'product_uom': self.product_uom.id,
            'input_qty': self.input_qty, 'state': 'waiting', 'time_wait': fields.Datetime.now(),
            'workorder_id': self.id, 'workorder_name': self.name, 'mesline_id': self.mesline_id.id,
            'mesline_name': self.mesline_id.name, 'routing_id': self.routing_id.id,
            'mainorder_id': False if not self.mainorder_id else self.mainorder_id.id,
            'mainorder_name': False if not self.mainorder_name else self.mainorder_name
        })
        self.write({
            'workcenter_id': workticket.id, 'workcenter_name': routline.name, 'workcenter_start': workticket.id
        })

    @api.one
    def action_build_consumelist(self):
        """
        生成物料消耗清单
        :return:
        """
        if not self.aas_bom_id:
            raise UserError(u'请先设置工单成品的BOM清单，否则无法计算原料消耗！')
        if not self.aas_bom_id.workcenter_lines or len(self.aas_bom_id.workcenter_lines) <= 0:
            raise UserError(u'请先仔细检查BOM清单是否正确设置！')
        consumelist = []
        bomlines = self.aas_bom_id.workcenter_lines
        for bomline in bomlines:
            tempmaterial = bomline.product_id
            consume_unit = bomline.product_qty / bomline.bom_id.product_qty
            if tempmaterial.virtual_material:
                virtualbom = self.env['aas.mes.bom'].search([('product_id', '=', tempmaterial.id), ('active', '=', True)], limit=1)
                if not virtualbom:
                    raise UserError(u'虚拟物料%s还未设置有效BOM清单，请通知相关人员设置BOM清单！'% tempmaterial.default_code)
                if not virtualbom.bom_lines or len(virtualbom.bom_lines) <= 0:
                    raise UserError(u'请先仔细检查虚拟物料%s的BOM清单是否正确设置！'% tempmaterial.default_code)
                for virtualbomline in virtualbom.bom_lines:
                    if virtualbomline.product_id.virtual_material:
                        continue
                    virtual_consume_unit = virtualbomline.product_qty / virtualbom.product_qty
                    total_consume_unit = consume_unit * virtual_consume_unit
                    consumelist.append((0, 0, {
                        'product_id': tempmaterial.id, 'material_id': virtualbomline.product_id.id,
                        'consume_unit': virtual_consume_unit, 'input_qty': self.input_qty * total_consume_unit,
                        'workcenter_id': False if not bomline.workcenter_id else bomline.workcenter_id.id
                    }))
            else:
                consumelist.append((0, 0, {
                    'product_id': self.product_id.id, 'material_id': tempmaterial.id,
                    'consume_unit': consume_unit, 'input_qty': self.input_qty * consume_unit,
                    'workcenter_id': False if not bomline.workcenter_id else bomline.workcenter_id.id
                }))
        if not consumelist or len(consumelist) <= 0:
            raise UserError(u'请仔细检查BOM清单设置，无法生成消耗明细清单')
        self.write({'consume_lines': consumelist})


    @api.multi
    def action_producing(self):
        """
        设置当前工单为相应产线的即将生产的工单
        :return:
        """
        self.ensure_one()
        if self.mesline_type == 'station':
            return False
        action_message = u"您确认接下来开始生产当前工单吗？"
        if self.mesline_id.workorder_id:
            action_message = u"当前产线上工单：%s正在生产，您确认切换到当前工单吗？"% self.mesline_id.workorder_id.name
        wizard = self.env['aas.mes.workorder.producing.wizard'].create({'workorder_id': self.id, 'action_message': action_message})
        view_form = self.env.ref('aas_mes.view_form_aas_mes_workorder_producing_wizard')
        return {
            'name': u"工单开工",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.workorder.producing.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }


    @api.one
    def action_done(self):
        if self.waitconsume:
            raise UserError(u'当前工单仍有产出的产品还未消耗原料，请先扣除相关原料消耗才能关闭工单！')
        currenttime = fields.Datetime.now()
        self.write({'state': 'done', 'produce_finish': currenttime, 'time_finish': currenttime})
        if self.mainorder_id:
            if self.env['aas.mes.workorder'].search_count([('mainorder_id', '=', self.mainorder_id.id), ('state', '!=', 'done')]) <= 0:
               self.mainorder_id.write({'state': 'done', 'produce_finish': currenttime})

    @api.one
    def action_waitconsume(self):
        """
        手工原料消耗
        :return:
        """
        outputdomain = [('workorder_id', '=', self.id), ('waiting_qty', '>', 0.0)]
        outputlist = self.env['aas.mes.workorder.product'].search(outputdomain)
        if outputlist and len(outputlist) > 0:
            for output in outputlist:
                result = output.action_output_consume(output)
                if not result['success']:
                    raise UserError(result['message'])


    @api.multi
    def action_close(self):
        """
        手工关闭工单
        :return:
        """
        self.ensure_one()
        if self.waitconsume:
            raise UserError(u'当前工单仍有产出的产品还未消耗原料，请先扣除相关原料消耗才能关闭工单！')
        if float_compare(self.output_qty, self.input_qty, precision_rounding=0.000001) >= 0.0:
            self.action_done()
            self.write({'time_finish': fields.Datetime.now(), 'closer_id': self.env.user.id})
        else:
            action_message = u"当前工单产出数量还未达到计划的生产数量，确认要关闭工单吗？"
            wizard = self.env['aas.mes.workorder.close.wizard'].create({'workorder_id': self.id, 'action_message': action_message})
            view_form = self.env.ref('aas_mes.view_form_aas_mes_workorder_close_wizard')
            return {
                'name': u"关闭工单",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'aas.mes.workorder.close.wizard',
                'views': [(view_form.id, 'form')],
                'view_id': view_form.id,
                'target': 'new',
                'res_id': wizard.id,
                'context': self.env.context
            }



    @api.model
    def action_output(self, workorder_id, product_id, output_qty, container_id=None, serialnumber=None):
        """工单产出
        :param workorder_id:
        :param product_id:
        :param output_qty:
        :param container_id:
        :param serialnumber:
        :return:
        """
        result = {'success': True, 'message': '', 'outputrecord': False, 'containerproduct': False}
        workorder = self.env['aas.mes.workorder'].browse(workorder_id)
        if not workorder.aas_bom_id:
            result.update({'success': False, 'message': u'工单未设置BOM清单，请仔细检查！'})
            return result
        if workorder.state == 'draft':
            result.update({'success': False, 'message': u'工单还未确认，请先确认工单才可以继续生产！'})
            return result
        if product_id != workorder.product_id.id:
            tempdomain = [('workorder_id', '=', workorder.id), ('product_id', '=', product_id)]
            if self.env['aas.mes.workorder.consume'].search_count(tempdomain) <= 0:
                result.update({'success': False, 'message': u'成品产出异常，可能不是当前工单产物！'})
                return result
        if not workorder.mesline_id.workdate:
            workorder.mesline_id.action_refresh_schedule()
        output_date = workorder.mesline_id.workdate
        lot_name = output_date.replace('-', '')
        # 成品批次
        product_lot = False if serialnumber else self.env['stock.production.lot'].action_checkout_lot(product_id, lot_name).id
        container_id = False if not container_id else container_id
        outputdomain = [('workorder_id', '=', workorder_id), ('output_date', '=', output_date), ('container_id', '=', container_id)]
        outputdomain.extend([('product_id', '=', product_id), ('product_lot', '=', product_lot)])
        outputdomain.append(('mesline_id', '=', workorder.mesline_id.id))
        if workorder.mesline_id.schedule_id:
            outputdomain.append(('schedule_id', '=', workorder.mesline_id.schedule_id.id))
        outputrecord = self.env['aas.mes.workorder.product'].search(outputdomain, limit=1)
        if not outputrecord:
            outputvals = {'workorder_id': workorder_id, 'product_id': product_id, 'product_lot': product_lot}
            outputvals.update({'output_date': output_date, 'mesline_id': workorder.mesline_id.id})
            if workorder.mesline_id.schedule_id:
                outputvals['schedule_id'] = workorder.mesline_id.schedule_id.id
            outputrecord = self.env['aas.mes.workorder.product'].create(outputvals)
        outputrecord.write({'waiting_qty': outputrecord.waiting_qty + output_qty})
        result['outputrecord'] = outputrecord
        if serialnumber:
            # 更新序列号产出信息
            serialrecord = self.env['aas.mes.serialnumber'].search([('name', '=', serialnumber)], limit=1)
            if not serialrecord:
                result.update({'success': False, 'message': u'序列号异常，无法产出！'})
                return result
            mesline, output_time = workorder.mesline_id, fields.Datetime.now()
            outputvals = {
                'output_time': output_time, 'outputuser_id': self.env.user.id, 'workorder_id': workorder_id,
                'outputrecord_id': outputrecord.id
            }
            if mesline.serialnumber_id:
                outputvals['lastone_id'] = mesline.serialnumber_id.id
                currenttime = fields.Datetime.from_string(output_time)
                lasttime = fields.Datetime.from_string(mesline.serialnumber_id.output_time)
                outputvals['output_internal'] = (currenttime - lasttime).seconds / 3600.0
            serialrecord.write(outputvals)
            mesline.write({'serialnumber_id': serialrecord.id})
        if container_id:
            # 更新容器中物品清单信息
            cdomain = [('container_id', '=', container_id), ('product_id', '=', product_id), ('product_lot', '=', product_lot)]
            productline = self.env['aas.container.product'].search(cdomain, limit=1)
            if productline:
                productline.write({'temp_qty': productline.temp_qty+output_qty})
            else:
                productline = self.env['aas.container.product'].create({
                    'container_id': container_id, 'product_id': product_id, 'product_lot': product_lot, 'temp_qty': output_qty
                })
            result['containerproduct'] = productline
        # 更新工单信息
        workordervals = {}
        if workorder.state != 'producing':
            workordervals['state'] = 'producing'
        if not workorder.produce_start:
            workordervals['produce_start'] = fields.Datetime.now()
        if workordervals and len(workordervals) > 0:
            workorder.write(workordervals)
        return result

    @api.model
    def action_consume(self, workorder_id, product_id):
        """
        工单消耗
        :param workorder_id:
        :param product_id:
        :return:
        """
        values = {'success': True, 'message': '', 'tracelist':[]}
        outputmodel = self.env['aas.mes.workorder.product']
        outputdomain = [('workorder_id', '=', workorder_id), ('product_id', '=', product_id)]
        outputdomain.append(('waiting_qty', '>', 0.0))
        outputlist = outputmodel.search(outputdomain)
        if outputlist and len(outputlist) > 0:
            meslineids  = []
            for output in outputlist:
                meslineids.append(output.mesline_id.id)
                result = outputmodel.action_output_consume(output)
                if result['tracelist'] and len(result['tracelist']) > 0:
                    values['tracelist'].extend(result['tracelist'])
                if not result['success']:
                    values.update(result)
                    return values
            if meslineids and len(meslineids) > 0:
                # 刷新一下上料清单库存
                feedmateriallist = self.env['aas.mes.feedmaterial'].search([('mesline_id', 'in', meslineids)])
                if feedmateriallist and len(feedmateriallist) > 0:
                    for feedmaterial in feedmateriallist:
                        feedmaterial.action_refresh_stock()
        return values


    @api.model
    def action_validate_consume(self, workorder_id, product_id, product_qty, workstation_id, workcenter_id=False):
        """
        物料消耗验证
        :param workorder_id:
        :param product_id:
        :param product_qty:
        :param workstation_id:
        :param workcenter_id:
        :return:
        """
        values = {'success': True, 'message': ''}
        workorder = self.env['aas.mes.workorder'].browse(workorder_id)
        workstation = self.env['aas.mes.workstation'].browse(workstation_id)
        mesline = workorder.mesline_id
        consumedomain = [('workorder_id', '=', workorder_id), ('product_id', '=', product_id)]
        if workcenter_id:
            consumedomain.append(('workcenter_id', '=', workcenter_id))
        consumelist = self.env['aas.mes.workorder.consume'].search(consumedomain)
        if consumelist and len(consumelist) > 0:
            consumedict, feedmaterialdict = {}, {}
            for tempconsume in consumelist:
                pkey = 'P-'+str(tempconsume.material_id.id)
                consume_qty = tempconsume.consume_unit * product_qty
                if pkey not in consumedict:
                    consumedict[pkey] = {'code': tempconsume.material_id.default_code, 'qty': consume_qty}
                else:
                    consumedict[pkey]['qty'] += consume_qty
            feeddomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation_id)]
            feedmateriallist = self.env['aas.mes.feedmaterial'].search(feeddomain)
            if not feedmateriallist or len(feedmateriallist) <= 0:
                values.update({'success': False, 'message': u'工位%s还未上料，请联系上料员上料！'% workstation.name})
                return values
            for feedmaterial in feedmateriallist:
                pkey = 'P-'+str(feedmaterial.material_id.id)
                if pkey in feedmaterialdict:
                    feedmaterialdict[pkey] += feedmaterial.material_qty
                else:
                    feedmaterialdict[pkey] = feedmaterial.material_qty
            lesslist, nonelist = [], []
            for ckey, cval in consumedict.items():
                if ckey not in feedmaterialdict:
                    nonelist.append(cval['code'])
                    continue
                consume_qty, feed_qty = cval['qty'], feedmaterialdict[ckey]
                if float_compare(feed_qty, consume_qty, precision_rounding=0.000001) < 0.0:
                    lesslist.append(cval['code'])
            if nonelist and len(nonelist) > 0:
                values['success'] = False
                values['message'] = '原料%s未投料；'% ','.join(nonelist)
            if lesslist and len(lesslist) > 0:
                values['success'] = False
                values['message'] = values['message'] + ('原料%s投料不足'% ','.join(lesslist))
        return values

    @api.model
    def get_virtual_materiallist(self, equipment_code):
        """
        获取工位上虚拟件的消耗清单
        :param equipment_code:
        :return:
        """
        values = {'success': True, 'message': ''}
        equipment = self.env['aas.equipment.equipment'].search([('code', '=', equipment_code)], limit=1)
        if not equipment:
            values.update({'success': False, 'message': u'设备编码异常，未搜索到相应编码的设备；请仔细检查！'})
            return values
        mesline, workstation = equipment.mesline_id, equipment.workstation_id
        if not mesline:
            values.update({'success': False, 'message': u'设备还未绑定产线，请联系相关人员设置！'})
            return values
        if not workstation:
            values.update({'success': False, 'message': u'设备还未绑定工位，请联系相关人员设置！'})
            return values
        workorder = mesline.workorder_id
        if not workorder:
            values.update({'success': False, 'message': u'设备产线还未指定生产工单，请联系领班设置工单！'})
            return values
        values.update({
            'workorder_id': workorder.id, 'workorder_name': workorder.name, 'product_id': workorder.product_id.id,
            'product_code': workorder.product_id.default_code, 'input_qty': workorder.input_qty, 'virtuallist': [],
            'mainorder_id': 0 if not workorder.mainorder_id else workorder.mainorder_id.id,
            'mainorder_name': '' if not workorder.mainorder_id else workorder.mainorder_id.name
        })
        routing = workorder.routing_id
        if not routing:
            values.update({'success': False, 'message': u'工单%s上未设置工艺路线，请仔细检查！'% workorder.name})
            return values
        workcenter = self.env['aas.mes.routing.line'].search([('routing_id', '=', routing.id), ('workstation_id', '=', workstation.id)], limit=1)
        if not workcenter:
            values.update({'success': False, 'message': u'工位%s上未设置相应工序，请仔细检查！'% workcenter.name})
            return values
        # 获取BOM上虚拟件信息
        productdict = {}
        bomdomain = [('bom_id', '=', workorder.aas_bom_id.id), ('workcenter_id', '=', workcenter.id)]
        bomworkcenters = self.env['aas.mes.bom.workcenter'].search(bomdomain)
        if bomworkcenters and len(bomworkcenters):
            for tempbom in bomworkcenters:
                if not tempbom.product_id.virtual_material:
                    continue
                pkey = 'P-'+str(tempbom.product_id.id)
                productdict[pkey] = {
                    'product_id': tempbom.product_id.id, 'product_code': tempbom.product_id.default_code,
                    'input_qty': (tempbom.product_qty / tempbom.bom_id.product_qty) * workorder.input_qty, 'output_qty': 0.0,
                    'badmode_qty': 0.0, 'actual_qty': 0.0, 'todo_qty': 0.0, 'materiallist': [], 'weld_count': tempbom.product_id.weld_count
                }
        # 获取虚拟件消耗明细
        materialdomain = [('workorder_id', '=', workorder.id), ('workcenter_id', '=', workcenter.id)]
        materialdomain.append(('product_id', '!=', workorder.product_id.id))
        consumelist = self.env['aas.mes.workorder.consume'].search(materialdomain)
        if consumelist and len(consumelist) > 0:
            for tconsume in consumelist:
                pkey = 'P-'+str(tconsume.product_id.id)
                if pkey in productdict:
                    productdict[pkey]['materiallist'].append({
                        'product_id': productdict[pkey]['product_id'], 'product_code': productdict[pkey]['product_code'],
                        'material_id': tconsume.material_id.id, 'material_code': tconsume.material_id.default_code,
                        'consume_unit': tconsume.consume_unit, 'input_qty': tconsume.input_qty,
                        'consume_qty': tconsume.consume_qty, 'leave_qty': tconsume.leave_qty
                    })
        # 获取虚拟件产出
        outputdict = {}
        outputdomain = [('workorder_id', '=', workorder.id), ('product_id', '!=', workorder.product_id.id)]
        outputlist = self.env['aas.mes.workorder.product'].search(outputdomain)
        if outputlist and len(outputlist) > 0:
            for tempout in outputlist:
                pkey = 'P-'+str(tempout.product_id.id)
                if pkey in outputdict:
                    outputdict[pkey] += tempout.total_qty
                else:
                    outputdict[pkey] = tempout.total_qty
        for tkey, tval in productdict.items():
            temp_qty = tval['output_qty']
            if tkey in outputdict:
                temp_qty = outputdict[tkey]
            tval['output_qty'] = temp_qty
            tval['actual_qty'] = temp_qty
            tval['todo_qty'] = tval['input_qty'] - temp_qty
            values['virtuallist'].append(tval)
        return values

    @api.model
    def action_vtproduct_output(self, workstation_id, workorder_id, product_id, output_qty):
        """虚拟件半成品产出
        :param workstation_id:
        :param workorder_id:
        :param product_id:
        :param output_qty:
        :return:
        """
        values = {'success': True, 'message': ''}
        vdvalues = self.action_validate_consume(workorder_id, product_id, output_qty, workstation_id)
        if not vdvalues.get('success', False):
            values.update(vdvalues)
            return values
        opvalues = self.action_output(workorder_id, product_id, output_qty)
        if not opvalues.get('success', False):
            values.update({'success': False, 'message': opvalues['message']})
            return values
        else:
            values.update({'success': True, 'message': opvalues['message']})
        csvalues = self.action_consume(workorder_id, product_id)
        if not csvalues.get('success', False):
            values.update(csvalues)
        return values


    @api.model
    def action_print_label(self, printer_id, ids=[], domain=[]):
        values = {'success': True, 'message': ''}
        printer = self.env['aas.label.printer'].browse(printer_id)
        if not printer.field_lines or len(printer.field_lines) <= 0:
            values.update({'success': False, 'message': u'请联系管理员标签打印未指定具体打印内容！'})
            return values
        values.update({'printer': printer.name, 'serverurl': printer.serverurl})
        field_list = [fline.field_name for fline in printer.field_lines]
        if ids and len(ids) > 0:
            labeldomain = [('id', 'in', ids)]
        else:
            labeldomain = domain
        if not labeldomain or len(labeldomain) <= 0:
            return {'success': False, 'message': u'您可能已经选择了所有工单或未选择任何工单，请选中需要打印的工单！'}
        records = self.search_read(domain=labeldomain, fields=field_list)
        if not records or len(records) <= 0:
            values.update({'success': False, 'message': u'未搜索到需要打印的工单！'})
            return values
        records = printer.action_correct_records(records)
        values['records'] = records
        return values


    @api.model
    def action_flowingline_output(self, workorder, mesline, workstation, serialnumber):
        """流水线产出
        :param workorder:
        :param mesline:
        :param workstation:
        :param serialnumber:
        :return:
        """
        values = {'success': True, 'message': ''}
        outputresult = workorder.action_output(workorder.id, workorder.product_id.id, 1, serialnumber=serialnumber)
        if not outputresult.get('success', False):
            values.update({'success': False, 'message': outputresult.get('message', '')})
            return values
        toperation = self.env['aas.mes.operation'].search([('serialnumber_name', '=', serialnumber)], limit=1)
        if not toperation:
            return values
        toperation.action_finalcheck(mesline, workstation)
        return values





# 工单产出
class AASMESWorkorderProduct(models.Model):
    _name = 'aas.mes.workorder.product'
    _description = 'AAS MES Work Order Product'
    _rec_name = 'product_id'

    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', ondelete='cascade', index=True)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict', index=True)
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次', ondelete='restrict', index=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict', index=True)
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict', index=True)
    product_qty = fields.Float(string=u'已产出数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    waiting_qty = fields.Float(string=u'待消耗数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    output_date = fields.Char(string=u'产出日期', copy=False)
    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='restrict')
    total_qty = fields.Float(string=u'总数量', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_total_qty', store=True)

    @api.depends('product_qty', 'waiting_qty')
    def _compute_total_qty(self):
        for record in self:
            record.total_qty = record.product_qty + record.waiting_qty




    @api.model
    def action_output_consume(self, outputrecord):
        """产出物料消耗
        :return:
        """
        values = {'success': True, 'message': '', 'tracelist': []}
        buildresult = self.action_build_consumerecords(outputrecord)
        if not buildresult['success']:
            values.update(buildresult)
            return values
        consumerecords = buildresult['records']
        if not consumerecords or len(consumerecords) <= 0:
            return values
        workorder, companyid = outputrecord.workorder_id, self.env.user.company_id.id
        destlocationid = self.env.ref('stock.location_production').id
        date_start, date_finish = False, False
        tempserialdomain = [('outputrecord_id', '=', outputrecord.id)]
        firstserial = self.env['aas.mes.serialnumber'].search(tempserialdomain, order='output_time asc', limit=1)
        if firstserial:
            date_start = firstserial.output_time if not firstserial.lastone_id else firstserial.lastone_id.output_time
            lastserial = self.env['aas.mes.serialnumber'].search(tempserialdomain, order='output_time desc', limit=1)
            date_finish = lastserial.output_time
        for tempconsume in consumerecords:
            tracevals = {
                'mesline_id': tempconsume['mesline_id'], 'product_id': tempconsume['product_id'],
                'workorder_id': tempconsume['workorder_id'], 'mainorder_id': tempconsume.get('mainorder_id', False),
                'serialnumbers': tempconsume.get('serialnumbers', False), 'schedule_id': tempconsume.get('schedule_id', False),
                'product_lot': tempconsume.get('product_lot', False), 'employeelist': tempconsume.get('employeelist', False),
                'equipmentlist': tempconsume.get('equipmentlist', False), 'date_start': date_start, 'date_finish': date_finish
            }
            workstation_id, workcenter_id = tempconsume.get('workstation_id', 0), tempconsume.get('workcenter_id', 0)
            if workstation_id and workstation_id > 0:
                tracevals['workstation_id'] = workstation_id
            if workcenter_id and workcenter_id > 0:
                tracevals['workcenter_id'] = workcenter_id
            # 创建追溯信息
            tracerecord = self.env['aas.mes.tracing'].create(tracevals)
            materiallist, movevallist, movelist = [], [], self.env['stock.move']
            for tempmaterial in tempconsume['materiallines']:
                material_id = tempmaterial['material_id']
                material_uom, material_code = tempmaterial['material_uom'], tempmaterial['material_code']
                for tempmove in tempmaterial['movelines']:
                    materiallist.append(material_code+'['+tempmove['material_lot_name']+']')
                    # 库存移动
                    moverecord = self.env['stock.move'].create({
                        'name': workorder.name, 'product_id': material_id,
                        'company_id': companyid, 'trace_id': tracerecord.id,
                        'product_uom': material_uom, 'create_date': fields.Datetime.now(),
                        'location_id': tempmove['location_id'], 'location_dest_id': destlocationid,
                        'restrict_lot_id': tempmove['material_lot'], 'product_uom_qty': tempmove['product_qty']
                    })
                    # 如果来源库位是一个容器则需要更新容器库存信息
                    tcontainer = moverecord.location_id.container_id
                    if tcontainer:
                        tproduct_qty = moverecord.product_uom_qty
                        tproduct_id, tproduct_lot = moverecord.product_id.id, moverecord.restrict_lot_id.id
                        tcontainer.action_consume(tproduct_id, tproduct_lot, tproduct_qty)
                    movelist |= moverecord
            movelist.action_done()
            tracerecord.write({'materiallist': ','.join(materiallist)})
            values['tracelist'].append(tracerecord.id)
        # 更新产出记录信息
        product_id, output_qty = outputrecord.product_id.id, outputrecord.waiting_qty
        product_qty = outputrecord.product_qty + outputrecord.waiting_qty
        workordervals = {'product_lines': [(1, outputrecord.id, {'product_qty': product_qty, 'waiting_qty': 0.0})]}
        consumelist = []
        consumedomain = [('workorder_id', '=', workorder.id), ('product_id', '=', product_id)]
        workorder_consume_list = self.env['aas.mes.workorder.consume'].search(consumedomain)
        for wkconsume in workorder_consume_list:
            consume_qty = wkconsume.consume_qty + (wkconsume.consume_unit * output_qty)
            consumelist.append((1, wkconsume.id, {'consume_qty': consume_qty}))
        workordervals['consume_lines'] = consumelist
        workorder.write(workordervals)
        # 序列号设置为已追溯
        seriallist = self.env['aas.mes.serialnumber'].search([('outputrecord_id', '=', outputrecord.id), ('traced', '=', False)])
        if seriallist and len(seriallist) > 0:
            seriallist.write({'traced': True})
        if outputrecord.container_id:
            # 容器中相应数量物品入库存
            productdomain = [('container_id', '=', outputrecord.container_id.id), ('product_id', '=', outputrecord.product_id.id)]
            productdomain.append(('product_lot', '=', False if not outputrecord.product_lot else outputrecord.product_lot.id))
            productline = self.env['aas.container.product'].search(productdomain, limit=1)
            if productline:
                productline.action_stock(outputrecord.waiting_qty)
        return values


    @api.model
    def action_build_consumerecords(self, outputrecord):
        """
        获取消耗记录
        :param outputrecord:
        :return:
        """
        values = {'success': True, 'message': '', 'records': []}
        waiting_qty, recordlist = outputrecord.waiting_qty, []
        if float_is_zero(waiting_qty, precision_rounding=0.000001):
            return values
        workorder, mesline, product = outputrecord.workorder_id, outputrecord.mesline_id, outputrecord.product_id
        consumedomain = [('workorder_id', '=', workorder.id), ('product_id', '=', product.id)]
        workorder_consume_list = self.env['aas.mes.workorder.consume'].search(consumedomain)
        if not workorder_consume_list or len(workorder_consume_list) <= 0:
            return values
        maintracevals = {'mesline_id': mesline.id, 'product_id': product.id, 'workorder_id': workorder.id}
        serialdomain = [('outputrecord_id', '=', outputrecord.id), ('traced', '=', False)]
        serialnumberlist = self.env['aas.mes.serialnumber'].search_read(serialdomain, fields=['name'])
        if serialnumberlist and len(serialnumberlist) > 0:
            maintracevals['serialnumbers'] = ','.join([serialrecord.get('name') for serialrecord in serialnumberlist])
        if workorder.mainorder_id:
            maintracevals['mainorder_id'] = workorder.mainorder_id.id
        if mesline.schedule_id:
            maintracevals['schedule_id'] = mesline.schedule_id.id
        if outputrecord.product_lot:
            maintracevals['product_lot'] = outputrecord.product_lot.id
        workstationdict = {}
        for tempconsume in workorder_consume_list:
            material, want_qty = tempconsume.material_id, waiting_qty * tempconsume.consume_unit
            workcenter, workcenter_id, workstation, workstation_id = False, 0, False, 0
            feeddomain = [('mesline_id', '=', mesline.id), ('material_id', '=', material.id)]
            if tempconsume.workcenter_id:
                workcenter, workcenter_id = tempconsume.workcenter_id, tempconsume.workcenter_id.id
                if workcenter.workstation_id:
                    workstation, workstation_id = workcenter.workstation_id, workcenter.workstation_id.id
                    feeddomain.append(('workstation_id', '=', workstation_id))
            if workstation_id not in workstationdict:
                stationvals = {'workstation_id': workstation_id, 'workcenter_id': workcenter_id, 'materiallines': []}
                stationvals.update(maintracevals)
                workstationdict[workstation_id] = stationvals
            workstationvals = workstationdict[workstation_id]
            materialvals = {
                'material_id': material.id,
                'material_uom': material.uom_id.id,
                'material_code': material.default_code,
            }
            # 检查投料明细
            feedmateriallist = self.env['aas.mes.feedmaterial'].search(feeddomain)
            if not feedmateriallist or len(feedmateriallist) <= 0:
                message = u'原料%s还没有投料记录！'% material.default_code
                if workstation:
                    message = (u'工位%s,'% workstation.name) + message
                values.update({'success': False, 'message': message})
                return values
            feed_qty, quantdict = 0.0, {}
            for feedmaterial in feedmateriallist:
                # 刷新线边库库存
                quants = feedmaterial.action_checking_quants()
                if quants and len(quants) > 0:
                    for tempquant in quants:
                        qkey = 'Q-'+str(tempquant.lot_id.id)+'-'+str(tempquant.location_id.id)
                        if qkey in quantdict:
                            quantdict['qkey']['product_qty'] += tempquant.qty
                        else:
                            quantdict['qkey'] = {
                                'location_id': tempquant.location_id.id, 'product_qty': tempquant.qty,
                                'material_lot': tempquant.lot_id.id, 'material_lot_name': tempquant.lot_id.name
                            }
                feed_qty += feedmaterial.material_qty
            if float_compare(feed_qty, want_qty, precision_rounding=0.000001) < 0.0:
                message = u'原料%s投入量不足！'% material.default_code
                if workstation:
                    message = (u'工位%s,'% workstation.name) + message
                values.update({'success': False, 'message': message})
                return values
            schedule_id = 0 if not mesline.schedule_id else mesline.schedule_id.id
            employees_equipments = self.env['aas.mes.work.attendance'].action_trace_employees_equipments(mesline.id,
                schedule_id, workstation_id, outputrecord.output_date)
            workstationvals.update({
                'employeelist': employees_equipments.get('employeelist', False),
                'equipmentlist': employees_equipments.get('equipmentlist', False)
            })
            # 库存分配
            tempmovedict = {}
            for qkey, qval in quantdict.items():
                if float_compare(want_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                    break
                lkey = 'L-'+str(qval['material_lot'])+'-'+str(qval['location_id'])
                if float_compare(want_qty, qval['product_qty'], precision_rounding=0.000001) >= 0.0:
                    tempqty = qval['product_qty']
                else:
                    tempqty = want_qty
                if lkey in tempmovedict:
                    tempmovedict[lkey]['product_qty'] += tempqty
                else:
                    tempmovedict[lkey] = {
                        'location_id': qval['location_id'], 'product_qty': tempqty,
                        'material_lot': qval['material_lot'], 'material_lot_name': qval['material_lot_name']
                    }
                want_qty -= tempqty
            materialvals['movelines'] = tempmovedict.values()
            workstationvals['materiallines'].append(materialvals)
        values['records'] = workstationdict.values()
        return values



class AASMESWorkorderConsume(models.Model):
    _name = 'aas.mes.workorder.consume'
    _description = 'AAS MES Work Order Consume'

    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', ondelete='cascade')
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'成品', ondelete='restrict')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料', ondelete='restrict')
    consume_unit = fields.Float(string=u'单位消耗', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    input_qty = fields.Float(string=u'计划数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    consume_qty = fields.Float(string=u'已消耗量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    leave_qty = fields.Float(string=u'剩余数量', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_leave_qty', store=True)

    @api.depends('input_qty', 'consume_qty')
    def _compute_leave_qty(self):
        for record in self:
            leave_qty = record.input_qty - record.consume_qty
            if float_compare(leave_qty, 0.0, precision_rounding=0.000001) < 0.0:
                leave_qty = 0.0
            record.leave_qty = leave_qty

    @api.model
    def loading_consumelist_onclient(self, workorder_id, workcenter_id=False):
        values = {'success': True, 'message': '', 'consumelist': []}
        temdomain = [('workorder_id', '=', workorder_id)]
        if workcenter_id:
            temdomain.append(('workcenter_id', '=', workcenter_id))
        consumelist = self.env['aas.mes.workorder.consume'].search(temdomain)
        if consumelist and len(consumelist) > 0:
            values['consumelist'] = [{
                'product_id': tconsume.product_id.id, 'product_code': tconsume.product_id.default_code,
                'material_id': tconsume.material_id.id, 'material_code': tconsume.material_id.default_code,
                'consume_unit': tconsume.consume_unit, 'input_qty': tconsume.input_qty,
                'consume_qty': tconsume.consume_qty, 'leave_qty': tconsume.leave_qty
            } for tconsume in consumelist]
        return values




################################## 向导 #################################

class AASMESWorkorderProducingWizard(models.TransientModel):
    _name = 'aas.mes.workorder.producing.wizard'
    _description = 'AAS MES Workorder Producing Wizard'

    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', ondelete='cascade')
    action_message = fields.Char(string=u'提示信息', copy=False)

    @api.one
    def action_done(self):
        workorder = self.workorder_id
        mesline = workorder.mesline_id
        if mesline.workorder_id:
            mesline.workorder_id.write({'isproducing': False})
        mesline.write({'workorder_id': workorder.id})
        workorder.write({'isproducing': True})



class AASMESWorkorderCloseWizard(models.TransientModel):
    _name = 'aas.mes.workorder.close.wizard'
    _description = 'AAS MES Workorder Close Wizard'

    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', ondelete='cascade')
    action_message = fields.Char(string=u'提示信息', copy=False)

    @api.one
    def action_done(self):
        workorder = self.workorder_id
        workorder.action_done()
        workorder.write({'time_finish': fields.Datetime.now(), 'closer_id': self.env.user.id})
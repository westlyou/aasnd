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
OUTPUTMANNERS = [('container', u'容器'), ('label', u'标签')]

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
    creator_id = fields.Many2one(comodel_name='res.users', string=u'创建人', ondelete='restrict', default=lambda self: self.env.user)
    state = fields.Selection(selection=ORDERSTATES, string=u'状态', default='draft', copy=False)
    produce_date = fields.Char(string=u'生产日期', copy=False)
    produce_start = fields.Datetime(string=u'实际开工时间', copy=False)
    produce_finish = fields.Datetime(string=u'实际完工时间', copy=False)
    plan_start = fields.Datetime(string=u'计划开工时间', copy=False)
    plan_finish = fields.Datetime(string=u'计划完工时间', copy=False)
    plan_finish_date = fields.Char(string=u'计划完工日期', compute='_compute_plan_finish_date', store=True)
    finishontime = fields.Boolean(string=u'准时完工', default=False, copy=False)


    date_code = fields.Char(string='DateCode')
    mainorder_id = fields.Many2one(comodel_name='aas.mes.mainorder', string=u'主工单', ondelete='cascade', index=True)
    wireorder_id = fields.Many2one(comodel_name='aas.mes.wireorder', string=u'线材工单', ondelete='cascade', index=True)
    mesline_type = fields.Selection(selection=MESLINETYPE, string=u'产线类型', compute='_compute_mesline', store=True)
    mesline_name = fields.Char(string=u'产线名称', compute='_compute_mesline', store=True)
    mainorder_name = fields.Char(string=u'主工单', compute='_compute_mainorder', store=True)
    product_code = fields.Char(string=u'产品编码', copy=False)
    customer_code = fields.Char(string=u'客方编码', copy=False, help=u'产品在客户方的料号')
    workcenter_id = fields.Many2one(comodel_name='aas.mes.workticket', string=u'当前工序', ondelete='restrict')
    workcenter_name = fields.Char(string=u'当前工序名称', copy=False)
    workcenter_start = fields.Many2one(comodel_name='aas.mes.workticket', string=u'开始工序', ondelete='restrict')
    workcenter_finish = fields.Many2one(comodel_name='aas.mes.workticket', string=u'结束工序', ondelete='restrict')
    isproducing = fields.Boolean(string=u'正在生产', default=False, copy=False, help=u'当前工单在相应的产线上正在生产')
    output_qty = fields.Float(string=u'产出数量', digits=dp.get_precision('Product Unit of Measure'))
    output_time = fields.Datetime(string=u'产出时间', copy=False, help=u'最近一次产出的时间')
    scrap_qty = fields.Float(string=u'报废数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    output_manner = fields.Selection(selection=OUTPUTMANNERS, string=u'产出方式', copy=False)
    finalproduct_id = fields.Many2one(comodel_name='product.product', string=u'最终产品')
    closer_id = fields.Many2one(comodel_name='res.users', string=u'手工关单员', ondelete='restrict', copy=False)
    close_time = fields.Datetime(string=u'手工关单时间', copy=False)

    workticket_lines = fields.One2many(comodel_name='aas.mes.workticket', inverse_name='workorder_id', string=u'工票明细')
    production_lines = fields.One2many(comodel_name='aas.production.product', inverse_name='workorder_id', string=u'产出明细')
    consume_lines = fields.One2many(comodel_name='aas.mes.workorder.consume', inverse_name='workorder_id', string=u'消耗清单')
    badmode_lines = fields.One2many(comodel_name='aas.production.badmode', inverse_name='workorder_id', string=u'不良明细')

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

    @api.depends('plan_finish')
    def _compute_plan_finish_date(self):
        for record in self:
            if not record.plan_finish:
                record.plan_finish_date = False
            else:
                record.plan_finish_date = fields.Datetime.to_china_date(record.plan_finish)


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
        if product.customer_product_code:
            vals['customer_code'] = product.customer_product_code
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
        ordervals = {
            'workcenter_id': workticket.id, 'workcenter_name': routline.name, 'workcenter_start': workticket.id
        }
        if workticket.islastworkcenter():
            ordervals['workcenter_finish'] = workticket.id
        self.write(ordervals)


    @api.one
    def action_build_consumelist(self):
        """生成物料消耗清单
        :return:
        """
        if not self.aas_bom_id:
            raise UserError(u'请先设置工单成品的BOM清单，否则无法计算原料消耗！')
        if not self.aas_bom_id.workcenter_lines or len(self.aas_bom_id.workcenter_lines) <= 0:
            raise UserError(u'请先仔细检查BOM清单是否正确设置！')
        productdict, product = {}, self.aas_bom_id.product_id
        productdict[product.id] = {'workcenterid': False, 'level': 1}
        for workcenterline in self.aas_bom_id.workcenter_lines:
            material = workcenterline.product_id
            virtual, workcenter = material.virtual_material, workcenterline.workcenter_id
            if virtual:
                productdict[material.id] = {'workcenterid': workcenter.id, 'level': 2}
        consumelist, aasbom = [], self.aas_bom_id
        self.action_loading_consumelist(aasbom, productdict, consumelist, self.input_qty, False, 1)
        if not consumelist or len(consumelist) <= 0:
            raise UserError(u'请仔细检查BOM清单设置，无法生成消耗明细清单')
        templist = []
        for tconsume in consumelist:
            productid, materialid = tconsume['product_id'], tconsume['material_id']
            tlevel = tconsume['material_level']
            if materialid in productdict and (productdict[materialid]['level'] - tlevel > 1):
                continue
            if productid in productdict:
                if productdict[productid]['level'] != tlevel:
                    continue
                else:
                    if productdict[productid]['workcenterid']:
                        tconsume['workcenter_id'] = productdict[productid]['workcenterid']
                    templist.append((0, 0, tconsume))
        self.write({'consume_lines': templist})


    @api.model
    def action_loading_consumelist(self, bom, productdict, consumelist, inputqty, workcenterid, level):
        """
        :param bom:
        :param virtualdict:
        :param inputqty:
        :param workcenterid:
        :param level:
        :return:
        """
        if not bom or not bom.workcenter_lines or len(bom.workcenter_lines) <= 0:
            return
        product = bom.product_id
        if product.id not in productdict:
            productdict[product.id] = {'workcenterid': workcenterid, 'level': level}
        else:
            if productdict[product.id]['level'] < level:
                productdict[product.id]['level'] = level
        for workcenterline in bom.workcenter_lines:
            material = workcenterline.product_id
            virtual = material.virtual_material
            conunit = workcenterline.product_qty / bom.product_qty
            if workcenterline.workcenter_id:
                workcenterid = workcenterline.workcenter_id.id
            consumevals = {
                'product_id': product.id, 'material_id': material.id,
                'consume_unit': conunit, 'input_qty': inputqty * conunit,
                'workcenter_id': workcenterid, 'material_level': level, 'material_virtual': virtual
            }
            consumelist.append(consumevals)
            if virtual:
                virtualdomain = [('product_id', '=', material.id), ('active', '=', True)]
                virtualbom = self.env['aas.mes.bom'].search(virtualdomain, limit=1)
                if not virtualbom or not virtualbom.workcenter_lines or len(virtualbom.workcenter_lines) <= 0:
                    continue
                tlevel, tinputqty = level + 1, consumevals['input_qty']
                self.action_loading_consumelist(virtualbom, productdict, consumelist, tinputqty, workcenterid, tlevel)






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
        # 根据结单方式判断什么时候自动结单
        closeorder = self.env['ir.values'].sudo().get_default('aas.mes.settings', 'closeorder_method')
        if closeorder == 'equal':
            if float_compare(self.output_qty, self.input_qty, precision_rounding=0.000001) >= 0.0:
                self.action_workorder_over()
        else:
            # total
            total_qty = self.output_qty + self.scrap_qty
            if float_compare(total_qty, self.input_qty, precision_rounding=0.000001) >= 0.0:
                self.action_workorder_over()


    @api.one
    def action_workorder_over(self):
        currenttime = fields.Datetime.now()
        workordervals = {'state': 'done', 'produce_finish': currenttime}
        chinatoday = fields.Datetime.to_china_today()
        if self.plan_finish_date and self.plan_finish_date == chinatoday:
            workordervals['finishontime'] = True
        self.write(workordervals)
        if not self.mainorder_id:
            return
        maindomain = [('mainorder_id', '=', self.mainorder_id.id), ('state', '!=', 'done')]
        if self.env['aas.mes.workorder'].search_count(maindomain) <= 0:
           self.mainorder_id.write({'state': 'done', 'produce_finish': currenttime})


    @api.multi
    def action_close(self):
        """
        手工关闭工单
        :return:
        """
        self.ensure_one()
        if float_compare(self.output_qty, self.input_qty, precision_rounding=0.000001) >= 0.0:
            self.action_done()
            self.write({'close_time': fields.Datetime.now(), 'closer_id': self.env.user.id})
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
    def get_virtual_materiallist(self, equipment_code, workorderid=None):
        """
        获取工位上虚拟件的消耗清单
        :param equipment_code:
        :param workorderid: 子工单id
        :return:
        """
        values = {'success': True, 'message': '', 'virtuallist': [], 'orderlist': []}
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
        if workorderid:
            workorder = self.env['aas.mes.workorder'].browse(workorderid)
            if not workorder:
                values.update({'success': False, 'message': u'请仔细检查，是否加载了有效的工单，或工单已经被删除！'})
                return values
        else:
            workorder = mesline.workorder_id
        if not workorder:
            values.update({'success': False, 'message': u'设备产线还未指定生产工单，请联系领班设置工单！'})
            return values
        values.update({
            'workorder_id': workorder.id, 'workorder_name': workorder.name, 'product_id': workorder.product_id.id,
            'product_code': workorder.product_id.default_code, 'input_qty': workorder.input_qty,
            'mainorder_id': 0 if not workorder.mainorder_id else workorder.mainorder_id.id,
            'mainorder_name': '' if not workorder.mainorder_id else workorder.mainorder_id.name
        })
        orderdomain = [('state', 'in', ['confirm', 'producing'])]
        orderdomain += [('mesline_id', '=', mesline.id), ('id', '!=', workorder.id)]
        workorderlist = self.env['aas.mes.workorder'].search(orderdomain)
        if workorderlist and len(workorderlist) > 0:
            values['orderlist'] = [{
                'order_id': torder.id, 'order_name': torder.name,
                'product_code': torder.product_id.default_code, 'input_qty': torder.input_qty
            } for torder in workorderlist]
        routing = workorder.routing_id
        if not routing:
            values.update({'success': False, 'message': u'工单%s上未设置工艺路线，请仔细检查！'% workorder.name})
            return values
        wcdomain = [('routing_id', '=', routing.id), ('workstation_id', '=', workstation.id)]
        workcenter = self.env['aas.mes.routing.line'].search(wcdomain, limit=1)
        if not workcenter:
            values.update({'success': False, 'message': u'工位%s上未设置相应工序，请仔细检查！'% workcenter.name})
            return values
        values['workcenter_id'] = workcenter.id
        # 加载半成品信息
        productdict = {}
        materialdomain = [('workorder_id', '=', workorder.id)]
        materialdomain += [('workcenter_id', '=', workcenter.id), ('product_id', '!=', workorder.product_id.id)]
        consumelist = self.env['aas.mes.workorder.consume'].search(materialdomain)
        if consumelist and len(consumelist) > 0:
            for tconsume in consumelist:
                product, material = tconsume.product_id, tconsume.material_id
                pkey = 'P'+str(product.id)
                materialval = {
                    'product_id': product.id, 'product_code': product.default_code,
                    'material_id': material.id, 'material_code': material.default_code,
                    'consume_unit': tconsume.consume_unit, 'input_qty': tconsume.input_qty,
                    'consume_qty': tconsume.consume_qty, 'leave_qty': tconsume.leave_qty
                }
                if pkey not in productdict:
                    temp_inputqty = tconsume.input_qty/tconsume.consume_unit
                    productdict[pkey] = {
                        'product_id': product.id, 'product_code': product.default_code,
                        'output_qty': 0.0, 'badmode_qty': 0.0, 'actual_qty': 0.0,
                        'weld_count': product.weld_count, 'input_qty': temp_inputqty, 'todo_qty': temp_inputqty
                    }
                    productdict[pkey]['materiallist'] = [materialval]
                else:
                    productdict[pkey]['materiallist'].append(materialval)
        workstation = workcenter.workstation_id
        outputdomain = [('workorder_id', '=', workorder.id), ('workstation_id', '=', workstation.id)]
        outputlist = self.env['aas.production.product'].search(outputdomain)
        if outputlist and len(outputlist) > 0 and consumelist and len(consumelist) > 0:
            for tempout in outputlist:
                product = tempout.product_id
                pkey = 'P'+str(product.id)
                if pkey not in productdict:
                    continue
                productdict[pkey]['output_qty'] += tempout.product_qty
                productdict[pkey]['badmode_qty'] += tempout.badmode_qty
                productdict[pkey]['actual_qty'] += tempout.product_qty + tempout.badmode_qty
                productdict[pkey]['todo_qty'] = productdict[pkey]['input_qty'] - productdict[pkey]['output_qty']
        if productdict and len(productdict) > 0:
            values['virtuallist'] = productdict.values()
        return values


    @api.model
    def action_print_label(self, printer_id, ids=[], domain=[]):
        """打印工单二维码
        :param printer_id:
        :param ids:
        :param domain:
        :return:
        """
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


    @api.multi
    def action_show_outputlabels(self):
        self.ensure_one()
        labeldomain = [('workorder_id', '=', self.id), ('label_id', '!=', False)]
        labellines = self.env['aas.production.product'].search(labeldomain)
        if not labellines or len(labellines) <= 0:
            raise UserError(u'当前没有产出标签显示，可能已经按照其他方式产出！')
        labelids = [str(tlabel.label_id.id) for tlabel in labellines]
        if len(labelids) == 1:
            tempdomain = "[('id','=',"+labelids[0]+")]"
        else:
            labelidsstr = ','.join(labelids)
            tempdomain = "[('id','in',("+labelidsstr+"))]"
        view_form = self.env.ref('aas_wms.view_form_aas_product_label')
        view_tree = self.env.ref('aas_wms.view_tree_aas_product_label')
        return {
            'name': u"标签清单",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'aas.product.label',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'target': 'self',
            'context': self.env.context,
            'domain': tempdomain
        }


    @api.multi
    def action_show_serialnumbers(self):
        self.ensure_one()
        if self.env['aas.mes.serialnumber'].search_count([('workorder_id', '=', self.id)]) <= 0:
            raise UserError(u'当前工单没有关联序列号！！')
        view_form = self.env.ref('aas_mes.view_form_aas_mes_serialnumber')
        view_tree = self.env.ref('aas_mes.view_tree_aas_mes_serialnumber')
        return {
            'name': u"序列号清单",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'aas.mes.serialnumber',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'target': 'self',
            'context': self.env.context,
            'domain': [('workorder_id', '=', self.id)]
        }


    @api.multi
    def action_show_wireorder(self):
        self.ensure_one()
        view_form = self.env.ref('aas_mes.view_form_aas_mes_workorder_manufacture')
        return {
            'name': u"生产工单",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.workorder',
            'res_id': self.id,
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'self',
            'context': self.env.context,
            'flags': {'initial_mode': 'view'}
        }

    @api.one
    def action_refresh_consumelist(self):
        """刷新消耗清单
        :return:
        """
        consumedict, workcenterdict = {}, {}
        if self.consume_lines and len(self.consume_lines) > 0:
            for tconsume in self.consume_lines:
                ckey = 'C-'+str(tconsume.product_id.id)+'-'+str(tconsume.material_id.id)
                consumedict[ckey] = {
                    'consumeid': tconsume.id, 'product_id': tconsume.product_id.id,
                    'material_id': tconsume.material_id.id, 'consume_unit': tconsume.consume_unit,
                    'input_qty': tconsume.input_qty, 'consume_qty': tconsume.consume_qty,
                    'workcenter_id': tconsume.workcenter_id.id
                }
        if not self.aas_bom_id:
            return
        workcenterlines = self.aas_bom_id.workcenter_lines
        if not workcenterlines or len(workcenterlines) <= 0:
            return
        for bworkcenter in workcenterlines:
            consume_unit = bworkcenter.product_qty / self.aas_bom_id.product_qty
            if not bworkcenter.product_id.virtual_material:
                ckey = 'C-'+str(self.product_id.id)+'-'+str(bworkcenter.product_id.id)
                workcenterdict[ckey] = {
                    'product_id': self.product_id.id, 'material_id': bworkcenter.product_id.id,
                    'consume_unit': consume_unit, 'input_qty': consume_unit * self.product_qty,
                    'consume_qty': 0.0, 'workcenter_id': bworkcenter.workcenter_id.id
                }
            else:
                tempproduct = bworkcenter.product_id
                bomdomain = [('product_id', '=', tempproduct.id), ('active', '=', True)]
                virtualbom = self.env['aas.mes.bom'].search(bomdomain, limit=1)
                if not virtualbom:
                    raise UserError(u'虚拟物料%s还未设置有效BOM清单，请通知相关人员设置BOM清单！'% tempproduct.default_code)
                if not virtualbom.bom_lines or len(virtualbom.bom_lines) <= 0:
                    raise UserError(u'请先仔细检查虚拟物料%s的BOM清单是否正确设置！'% tempproduct.default_code)
                for virtualbomline in virtualbom.bom_lines:
                    if virtualbomline.product_id.virtual_material:
                        continue
                    ckey = 'C-'+str(tempproduct.id)+'-'+str(virtualbomline.product_id.id)
                    virtual_consume_unit = virtualbomline.product_qty / virtualbom.product_qty
                    total_consume_unit = consume_unit * virtual_consume_unit
                    workcenterdict[ckey] = {
                        'product_id': tempproduct.id, 'material_id': virtualbomline.product_id.id,
                        'consume_unit': virtual_consume_unit, 'input_qty': self.input_qty * total_consume_unit,
                        'workcenter_id': False if not bworkcenter.workcenter_id else bworkcenter.workcenter_id.id
                    }
        consumelist = []
        for wkey, wval in workcenterdict.items():
            if wkey not in consumedict:
                consumelist.append((0, 0, wval))
            else:
                consumevals = {}
                orderunit, bomunit = consumedict[wkey]['consume_unit'], wval['consume_unit']
                if float_compare(orderunit, bomunit, precision_rounding=0.000001) != 0.0:
                    consumevals['consume_unit'] = bomunit
                orderinput_qty, bominput_qty = consumedict[wkey]['input_qty'], wval['input_qty']
                if float_compare(orderinput_qty, bominput_qty, precision_rounding=0.000001) != 0.0:
                    consumevals['input_qty'] = bominput_qty
                if consumevals and len(consumevals) > 0:
                    consumelist.append((1, consumedict[wkey]['consumeid'], consumevals))
                del consumedict[wkey]
        if consumedict and len(consumedict) > 0:
            for cskey, csval in consumedict.items():
                consumelist.append((2, csval['consumeid'], False))
        if consumelist and len(consumelist) > 0:
            self.write({'consume_lines': consumelist})



    @api.multi
    def action_set_finalproduct(self):
        self.ensure_one()
        finallist = self.env['aas.mes.bom'].get_finallist(self.product_id.id)
        if not finallist or len(finallist) <= 0:
            return
        if len(finallist) == 1:
            self.write({'finalproduct_id': finallist[0]['product_id']})
        else:
            wizard = self.env['aas.mes.workorder.finalproduct.setting.wizard'].create({
                'workorder_id': self.id,
                'action_message': u'请在下方最终产品清单中选择一个产品作为此工单的最终产品，提供首末检时使用！',
                'product_lines': [(0, 0, {'product_id': tfinal['product_id']}) for tfinal in finallist]
            })
            view_form = self.env.ref('aas_mes.view_form_aas_mes_workorder_finalproduct_setting_wizard')
            return {
                'name': u"设置最终产品",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'aas.mes.workorder.finalproduct.setting.wizard',
                'views': [(view_form.id, 'form')],
                'view_id': view_form.id,
                'target': 'new',
                'res_id': wizard.id,
                'context': self.env.context
            }


    @api.multi
    def action_show_equipment_data(self):
        self.ensure_one()
        datadomain = [('workorder_id', '=', self.id)]
        view_form = self.env.ref('aas_equipment.view_form_aas_equipment_data')
        view_tree = self.env.ref('aas_equipment.view_tree_aas_equipment_data')
        return {
            'name': u"设备数据",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'aas.equipment.data',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'target': 'self',
            'context': self.env.context,
            'domain': datadomain
        }

    @api.multi
    def action_show_producttest_data(self):
        self.ensure_one()
        datadomain = [('workorder_id', '=', self.id)]
        view_form = self.env.ref('aas_mes.view_form_aas_mes_producttest_order')
        view_tree = self.env.ref('aas_mes.view_tree_aas_mes_producttest_order_all')
        return {
            'name': u"检测数据",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'aas.mes.producttest.order',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'target': 'self',
            'context': self.env.context,
            'domain': datadomain
        }

    @api.model
    def action_flowingline_output(self, workorder, workstation, serialnumber):
        """流水线产出
        :param workorder:
        :param serialnumber:
        :return:
        """
        values = {'success': True, 'message': ''}
        product = workorder.product_id
        outputresult = self.env['aas.production.product'].action_production_output(workorder, product, 1,
                                                                                       workstation=workstation,
                                                                                       serialnumber=serialnumber,
                                                                                       finaloutput=True, tracing=True)
        if not outputresult.get('success', False):
            values.update(outputresult)
            return values
        return values


    @api.model
    def action_vtproduct_output(self, workstation_id, workorder_id, product_id, output_qty, badmode_lines=[], equipment_id=False):
        """虚拟件半成品产出
        :param workstation_id:
        :param workorder_id:
        :param product_id:
        :param output_qty:
        :param badmode_lines:
        :param equipment_id:
        :return:
        """
        values = {'success': True, 'message': ''}
        workorder = self.env['aas.mes.workorder'].browse(workorder_id)
        workstation = self.env['aas.mes.workstation'].browse(workstation_id)
        product = self.env['product.product'].browse(product_id)
        equipment = False if not equipment_id else self.env['aas.equipment.equipment'].browse(equipment_id)
        lotcode = fields.Datetime.to_china_today().replace('-', '')
        if equipment and equipment.sequenceno:
            lotcode += equipment.sequenceno
        productlot = self.env['stock.production.lot'].action_checkout_lot(product_id, lotcode)
        csvalues = self.env['aas.production.product'].action_production_output(workorder, product, output_qty,
                                                                               equipment=equipment,
                                                                               workstation=workstation,
                                                                               badmode_lines=badmode_lines,
                                                                               tracing=True, product_lot=productlot)
        if not csvalues.get('success', False):
            values.update(csvalues)
        return values



class AASMESWorkorderConsume(models.Model):
    _name = 'aas.mes.workorder.consume'
    _description = 'AAS MES Work Order Consume'
    _order = 'workorder_id desc,material_level,workcenter_id,product_id'

    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', ondelete='cascade')
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'成品', ondelete='restrict')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料', ondelete='restrict')
    material_level = fields.Integer(string=u'物料层级', default=1)
    material_virtual = fields.Boolean(string=u'虚拟物料', default=False)
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
        workorder.write({'isproducing': True, 'produce_date': fields.Datetime.to_china_today()})



class AASMESWorkorderCloseWizard(models.TransientModel):
    _name = 'aas.mes.workorder.close.wizard'
    _description = 'AAS MES Workorder Close Wizard'

    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', ondelete='cascade')
    action_message = fields.Char(string=u'提示信息', copy=False)

    @api.one
    def action_done(self):
        workorder = self.workorder_id
        workorder.action_workorder_over()
        workorder.write({'close_time': fields.Datetime.now(), 'closer_id': self.env.user.id})



class AASMESWorkorderFinalProductSettingWizard(models.TransientModel):
    _name = 'aas.mes.workorder.finalproduct.setting.wizard'
    _description = 'AAS MES Workorder FinalProduct Setting Wizard'

    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', ondelete='cascade')
    action_message = fields.Char(string=u'提示信息', copy=False)
    product_lines = fields.One2many(comodel_name='aas.mes.workorder.finalproduct.setting.product.wizard', inverse_name='wizard_id', string=u'最终产品')

    @api.one
    def action_done(self):
        if not self.product_lines or len(self.product_lines) <= 0:
            raise UserError(u'操作异常，请检查当前产品是否有多个最终产品！')
        finalproduct = False
        for fproduct in self.product_lines:
            if not fproduct.finalchecked:
                continue
            if not finalproduct:
                finalproduct = fproduct.product_id
            else:
                raise UserError(u'最终产品只能设置一个！')
        if not finalproduct:
            raise UserError(u'请选择一个产品作为当前工单的最终产品！')
        self.workorder_id.write({'finalproduct_id': finalproduct.id})





class AASMESWorkorderFianlProductSettingProductWizard(models.TransientModel):
    _name = 'aas.mes.workorder.finalproduct.setting.product.wizard'
    _description = 'AAS MES Workorder FinalProduct Setting Product Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.mes.workorder.finalproduct.setting.wizard', string='Wizard', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    finalchecked = fields.Boolean(string=u'确认', default=False, copy=False)

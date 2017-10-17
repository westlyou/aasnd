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

    name = fields.Char(string=u'名称', required=True, copy=False, index=True)
    barcode = fields.Char(string=u'条码', compute='_compute_barcode', store=True, index=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', required=True, index=True)
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    input_qty = fields.Float(string=u'投入数量', digits=dp.get_precision('Product Unit of Measure'), default=1.0)
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
    mesline_type = fields.Selection(selection=MESLINETYPE, string=u'产线类型', compute='_compute_mesline', store=True)
    mesline_name = fields.Char(string=u'名称', compute='_compute_mesline', store=True)
    mainorder_name = fields.Char(string=u'主工单', compute='_compute_mainorder', store=True)
    product_code = fields.Char(string=u'产品编码', copy=False)
    workcenter_id = fields.Many2one(comodel_name='aas.mes.workticket', string=u'当前工序', ondelete='restrict')
    workcenter_name = fields.Char(string=u'当前工序名称', copy=False)
    workcenter_start = fields.Many2one(comodel_name='aas.mes.workticket', string=u'开始工序', ondelete='restrict')
    workcenter_finish = fields.Many2one(comodel_name='aas.mes.workticket', string=u'结束工序', ondelete='restrict')

    workticket_lines = fields.One2many(comodel_name='aas.mes.workticket', inverse_name='workorder_id', string=u'工票明细')
    product_lines = fields.One2many(comodel_name='aas.mes.workorder.product', inverse_name='workorder_id', string=u'成品明细')
    output_qty = fields.Float(string=u'产出数量', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_output_qty', store=True)



    isproducing = fields.Boolean(string=u'正在生产', default=False, copy=False, help=u'当前工单在相应的产线上正在生产')

    _sql_constraints = [
        ('uniq_name', 'unique (name)', u'子工单名称不可以重复！')
    ]

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

    @api.depends('product_lines')
    def _compute_output_qty(self):
        for record in self:
            tempqty = 0.0
            if record.product_lines and len(record.product_lines) > 0:
                tempqty = sum([pline.product_qty for pline in record.product_lines])
            record.output_qty = tempqty


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
        self.write({'state': 'confirm'})
        if self.mesline_type == 'station' and self.routing_id:
            domain = [('routing_id', '=', self.routing_id.id)]
            routline = self.env['aas.mes.routing.line'].search(domain, order='sequence', limit=1)
            workticket = self.env['aas.mes.workticket'].create({
                'name': self.name+'-'+str(routline.sequence), 'sequence': routline.sequence,
                'workcenter_id': routline.id, 'workcenter_name': routline.name,
                'product_id': self.product_id.id, 'product_uom': self.product_uom.id,
                'input_qty': self.input_qty, 'state': 'waiting', 'time_wait': fields.Datetime.now(),
                'workorder_id': self.id, 'workorder_name': self.name, 'mesline_id': self.mesline_id.id,
                'mesline_name': self.mesline_name, 'routing_id': self.routing_id.id,
                'mainorder_id': False if not self.mainorder_id else self.mainorder_id.id,
                'mainorder_name': False if not self.mainorder_name else self.mainorder_name
            })
            self.write({
                'workcenter_id': workticket.id, 'workcenter_name': routline.name, 'workcenter_start': workticket.id
            })



    @api.one
    def action_done(self):
        self.write({'state': 'done', 'produce_finish': fields.Datetime.now()})
        if self.mainorder_id:
            if self.env['aas.mes.workorder'].search_count([('mainorder_id', '=', self.mainorder_id.id), ('state', '!=', 'done')]) <= 0:
               self.mainorder_id.write({'state': 'done', 'produce_finish': fields.Datetime.now()})


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

# 工单产出
class AASMESWorkorderProduct(models.Model):
    _name = 'aas.mes.workorder.product'
    _description = 'AAS MES Work Order Product'

    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=1.0)
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号')
    operator_id = fields.Many2one(comodel_name='res.users', string=u'操作员', default= lambda self:self.env.user)
    operation_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)

    @api.model
    def create(self, vals):
        record = super(AASMESWorkorderProduct, self).create(vals)
        if record.serialnumber_id:
            record.serialnumber_id.write({'used': True})
        return record


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
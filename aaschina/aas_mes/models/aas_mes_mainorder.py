# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-9-21 14:19
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError
from . import MESLINETYPE

import logging

_logger = logging.getLogger(__name__)

#  主工单

ORDERSTATES = [('draft', u'草稿'), ('splited', u'拆分'), ('producing', u'生产'), ('done', u'完成')]

class AASMESMainorder(models.Model):
    _name = 'aas.mes.mainorder'
    _description = 'AAS MES Main Order'


    name = fields.Char(string=u'名称', required=True, copy=False, index=True)
    barcode = fields.Char(string=u'条码', copy=False, index=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', required=True, index=True)
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_qty = fields.Float(string=u'计划数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    actual_qty = fields.Float(string=u'实际数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    aas_bom_id = fields.Many2one(comodel_name='aas.mes.bom', string=u'物料清单', ondelete='restrict')
    routing_id = fields.Many2one(comodel_name='aas.mes.routing', string=u'工艺路线', ondelete='restrict')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict', index=True)
    time_create = fields.Datetime(string=u'创建时间', default=fields.Datetime.now, copy=False)
    time_finish = fields.Datetime(string=u'完成时间', copy=False)
    creator_id = fields.Many2one(comodel_name='res.users', string=u'创建人', ondelete='restrict', default=lambda self: self.env.user)
    state = fields.Selection(selection=ORDERSTATES, string=u'状态', default='draft', copy=False)
    produce_start = fields.Datetime(string=u'开始生产', copy=False)
    produce_finish = fields.Datetime(string=u'结束生产', copy=False)
    imported = fields.Boolean(string=u'系统导入', default=False, copy=False)
    splited = fields.Boolean(string=u'是否拆分', default=False, copy=False)
    start_index = fields.Integer(string=u"开始序号", default=1)
    split_unit_qty = fields.Float(string=u'拆分批次数量', digits=dp.get_precision('Product Unit of Measure'))
    mesline_type = fields.Selection(selection=MESLINETYPE, string=u'产线类型', compute='_compute_mesline_type', store=True)

    workorder_lines = fields.One2many(comodel_name='aas.mes.workorder', inverse_name='mainorder_id', string=u'工单明细')

    _sql_constraints = [
        ('uniq_name', 'unique (name)', u'主工单名称不可以重复！')
    ]

    @api.one
    @api.constrains('aas_bom_id', 'start_index', 'split_unit_qty', 'actual_qty', 'product_qty')
    def action_check_mainorder(self):
        if not self.product_qty or float_compare(self.product_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise ValidationError(u'计划生产数量必须是一个有效的正数！')
        if not self.actual_qty or float_compare(self.actual_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise ValidationError(u'实际生产数量必须是一个有效的正数！')
        if self.aas_bom_id and self.aas_bom_id.product_id.id != self.product_id.id:
            raise ValidationError(u'请仔细检查，当前物料清单和产品不匹配！')
        if not self.start_index or self.start_index < 1:
            raise ValidationError(u'开始序号必须是一个大于等于1的整数！')
        if float_compare(self.split_unit_qty, self.actual_qty, precision_rounding=0.000001) > 0.0:
            raise ValidationError(u'拆分批次数量不能大于实际生产数量')

    @api.depends('mesline_id')
    def _compute_mesline_type(self):
        for record in self:
            record.mesline_type = record.mesline_id.line_type


    @api.onchange('product_id')
    def action_change_product(self):
        if not self.product_id:
            self.product_uom, self.aas_bom_id, self.routing_id = False, False, False
            self.actual_qty, self.split_unit_qty = self.product_qty, 0.0
        else:
            self.product_uom = self.product_id.id
            aasbom = self.env['aas.mes.bom'].search([('product_id', '=', self.product_id.id)], order='create_time desc', limit=1)
            if aasbom:
                self.aas_bom_id = aasbom.id
                if aasbom.routing_id:
                    self.routing_id = aasbom.routing_id.id
            if self.product_id.product_yield:
                self.actual_qty = self.product_qty / self.product_id.product_yield
            if self.product_id.split_qty:
                self.split_unit_qty = self.product_id.split_qty

    @api.onchange('product_qty')
    def action_change_product_qty(self):
        if not self.product_qty:
            self.actual_qty = 0.0
        elif self.product_id:
            if not self.product_id.product_yield:
                self.actual_qty = self.product_qty
            else:
                self.actual_qty = self.product_qty / self.product_id.product_yield

    @api.model
    def default_get(self, fields_list):
        defaults = super(AASMESMainorder,self).default_get(fields_list)
        defaults['name'] = fields.Datetime.to_timezone_time(fields.Datetime.now(), 'Asia/Shanghai').strftime('%Y%m%d%H%M%S')
        return defaults


    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        record = super(AASMESMainorder, self).create(vals)
        return record

    @api.model
    def action_before_create(self, vals):
        vals['barcode'] = 'AP'+vals['name']
        product = self.env['product.product'].browse(vals.get('product_id'))
        vals['product_uom'] = product.uom_id.id
        bomdomain = [('product_id', '=', product.id), ('state', '=', 'normal')]
        aasbom = self.env['aas.mes.bom'].search(bomdomain, order='create_time desc', limit=1)
        if aasbom:
            vals['aas_bom_id'] = aasbom.id
            if aasbom.routing_id:
                vals['routing_id'] = aasbom.routing_id.id
        if not vals.get('actual_qty', False):
            if not product.product_yield:
                vals['actual_qty'] = vals.get('product_qty', 0.0)
            else:
                vals['actual_qty'] = vals.get('product_qty', 0.0) / product.product_yield

    @api.multi
    def write(self, vals):
        if vals.get('name', False):
            vals['barcode'] = 'AP'+vals['name']
        if vals.get('product_id', False):
            raise UserError(u'您可删除主工单并重新创建，但不可以修改产品信息！')
        return super(AASMESMainorder, self).write(vals)

    @api.multi
    def unlink(self):
        for record in self:
            if record.workorder_lines and len(record.workorder_lines) > 0 and record.state in ['producing', 'done']:
                raise UserError(u'主工单%s已经开始生产或已经完成，不可以删除！'% record.name)
        return super(AASMESMainorder, self).unlink()


    @api.one
    def action_split(self):
        if not self.split_unit_qty or float_compare(self.split_unit_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise UserError(u'拆分批次数量必须是一个有效的正数！')
        tempqty, sequence = self.actual_qty, self.start_index
        while float_compare(tempqty, 0.0, precision_rounding=0.000001) > 0:
            order_qty = self.split_unit_qty
            if float_compare(tempqty, order_qty, precision_rounding=0.000001) < 0:
                order_qty = tempqty
            self.action_building_workorder(sequence, order_qty)
            tempqty -= order_qty
            sequence += 1
        self.write({'state': 'splited', 'splited': True})


    @api.one
    def action_building_workorder(self, sequence, product_qty):
        workorder = self.env['aas.mes.workorder'].create({
            'name': self.name+'-'+str(sequence), 'product_id': self.product_id.id,
            'product_uom': self.product_uom.id, 'input_qty': product_qty, 'output_qty': product_qty,
            'aas_bom_id': self.aas_bom_id.id, 'routing_id': self.routing_id.id,
            'mesline_id': self.mesline_id.id, 'mainorder_id': self.id, 'product_code': self.product_id.default_code
        })
        workorder.action_confirm()


    @api.multi
    def action_list_workorders(self):
        self.ensure_one()
        if not self.workorder_lines or len(self.workorder_lines) <= 0:
            raise UserError(u'当前主工单下没有子工单，可能已经被清理！')
        productionids = str(tuple(self.workorder_lines.ids))
        action = self.env.ref('aas_mes.action_aas_mes_workorder')
        formview = self.env.ref('aas_mes.view_form_aas_mes_workorder')
        treeview = self.env.ref('aas_mes.view_tree_aas_mes_workorder')
        result = {'name': u'拆分明细', 'help': action.help, 'type': action.type}
        result.update({'views': [[treeview.id, 'tree'], [formview.id, 'form']]})
        result.update({
            'target': action.target, 'context': action.context,
            'res_model': action.res_model, 'domain': "[('id','in',%s)]" % productionids
        })
        return result

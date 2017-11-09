# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-11-1 17:04
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

WIREBOMSTATE = [('draft', u'草稿'), ('normal', u'正常'), ('override', u'失效')]

# 线材BOM
class AASMESWirebom(models.Model):
    _name = 'aas.mes.wirebom'
    _description = 'AAS MES Wire BOM'
    _rec_name = 'product_id'

    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=1.0)
    active = fields.Boolean(string=u'是否有效', default=True, copy=False)
    note = fields.Text(string=u'描述')
    version = fields.Char(string=u'版本', copy=False)
    state = fields.Selection(selection=WIREBOMSTATE, string=u'状态', default='draft', copy=False)
    operation_time = fields.Datetime(string=u'制单时间', default=fields.Datetime.now, copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'制单人', ondelete='restrict')
    origin_id = fields.Many2one(comodel_name='aas.mes.wirebom', string=u'源BOM', ondelete='restrict')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)
    material_lines = fields.One2many(comodel_name='aas.mes.wirebom.line', inverse_name='wirebom_id', string=u'原料明细')

    @api.onchange('product_id')
    def action_change_product(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id
        else:
            self.product_uom = False

    @api.model
    def create(self, vals):
        product = self.env['product.product'].browse(vals['product_id'])
        vals['product_uom'] = product.uom_id.id
        return super(AASMESWirebom, self).create(vals)


    @api.one
    def action_confirm(self):
        self.write({'state': 'normal'})



# 线材BOM明细
class AASMESWirebomLine(models.Model):
    _name = 'aas.mes.wirebom.line'
    _description = 'AAS MES Wire BOM Line'

    wirebom_id = fields.Many2one(comodel_name='aas.mes.wirebom', string=u'线材BOM', ondelete='cascade')
    material_id = product_id = fields.Many2one(comodel_name='product.product', string=u'原料', ondelete='restrict')
    material_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    material_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=1.0)

    _sql_constraints = [
        ('uniq_material', 'unique (wirebom_id, material_id)', u'请不要重复添加同一个物料！')
    ]

    @api.onchange('material_id')
    def action_change_material(self):
        if self.material_id:
            self.material_uom = self.material_id.uom_id.id
        else:
            self.material_uom = False

    @api.model
    def create(self, vals):
        material = self.env['product.product'].browse(vals['material_id'])
        vals['material_uom'] = material.uom_id.id
        return super(AASMESWirebomLine, self).create(vals)

    @api.one
    @api.constrains('material_id')
    def action_check_material(self):
        if not self.material_id:
            return
        materialbom = self.env['aas.mes.bom'].search([('product_id', '=', self.material_id.id), ('active', '=', True)], limit=1)
        if not materialbom:
            raise ValidationError(u'物料%s还未设置BOM清单，请先设置好BOM清单再继续线材BOM设置！'% self.material_id.default_code)



WIREORDERSTATES = [('draft', u'草稿'), ('wait', u'等待'), ('producing', u'生产'), ('done', u'完成')]

# 线材工单
class AASMESWireOrder(models.Model):
    _name = 'aas.mes.wireorder'
    _description = 'AAS MES Wire Order'

    name = fields.Char(string=u'名称', copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=1.0)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict', index=True)
    state = fields.Selection(selection=WIREORDERSTATES, string=u'状态', default='draft', copy=False)
    wirebom_id = fields.Many2one(comodel_name='aas.mes.wirebom', string=u'线材BOM', ondelete='restrict')
    produce_start = fields.Datetime(string=u'开始生产', copy=False)
    produce_finish = fields.Datetime(string=u'结束生产', copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'制单人', ondelete='restrict', default=lambda self:self.env.user)
    operation_time = fields.Datetime(string=u'制单时间', default=fields.Datetime.now, copy=False)
    pusher_id = fields.Many2one(comodel_name='res.users', string=u'投产人', ondelete='restrict')
    push_time = fields.Datetime(string=u'投产时间', copy=False)
    workorder_lines = fields.One2many(comodel_name='aas.mes.workorder', inverse_name='wireorder_id', string=u'工单明细')


    @api.onchange('product_id')
    def action_change_product(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id
            wirebomdomain = [('product_id', '=', self.product_id.id), ('active', '=', True)]
            wirebom = self.env['aas.mes.wirebom'].search(wirebomdomain, limit=1)
            if wirebom:
                self.wirebom_id = wirebom.id
        else:
            self.product_uom, self.wirebom_id = False, False

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('aas.mes.wireorder')
        product = self.env['product.product'].browse(vals['product_id'])
        vals['product_uom'] = product.uom_id.id
        return super(AASMESWireOrder, self).create(vals)

    @api.multi
    def unlink(self):
        for record in self:
            if record.state in ['producing', 'done']:
                raise UserError(u'工单%s已经开始执行，不可以删除！'% record.name)
        return super(AASMESWireOrder, self).unlink()


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


    @api.one
    def action_produce(self):
        """
        投产；拆分子工单
        :return:
        """
        if self.state != 'draft' or (self.workorder_lines and len(self.workorder_lines) > 0):
            return
        wirebom = self.wirebom_id
        tempindex, tempname = 1, self.name[2:]
        for tempmaterial in wirebom.material_lines:
            material = tempmaterial.material_id
            aasbom = self.env['aas.mes.bom'].search([('product_id', '=', material.id), ('active', '=', True)], limit=1)
            workorder = self.env['aas.mes.workorder'].create({
                'name': tempname+'-'+str(tempindex), 'product_id': material.id,
                'product_uom': material.uom_id.id, 'aas_bom_id': aasbom.id,
                'mesline_id': self.mesline_id.id, 'wireorder_id': self.id,
                'input_qty': (tempmaterial.material_qty / wirebom.product_qty) * self.product_qty
            })
            workorder.action_confirm()
            tempindex += 1
        self.write({'pusher_id': self.env.user.id, 'push_time': fields.Datetime.now(), 'state': 'wait'})



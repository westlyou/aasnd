# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-1-11 13:46
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

DATATYPES = [('char', 'Char'), ('number', 'Number')]

PRODUCTTESTSTATES = [
    ('draft', u'草稿'), ('prdcheck', u'PRD检查'), ('frmcheck', u'领班检查'), ('ipqcheck', u'IPQC检查'), ('done', u'完成')
]
TESTTYPES = [('firstone', u'首件'), ('lastone', u'末件'), ('random', u'抽检')]
DETERMINETYPES = [('prdcheck', u'PRD检查'), ('frmcheck', u'领班检查'), ('ipqcheck', u'IPQC检查')]


# 测试分类
class AASMESProductTestTemplate(models.Model):
    _name = 'aas.mes.producttest.template'
    _description = 'AAS MES ProductTest Template'

    name = fields.Char(string=u'名称', copy=False)
    operate_time = fields.Datetime(string=u'创建时间', default=fields.Datetime.now, copy=False)
    operator_id = fields.Many2one('res.users', string=u'创建用户', default=lambda self: self.env.user)
    parameter_lines = fields.One2many(comodel_name='aas.mes.producttest.template.parameter', inverse_name='template_id',
                                      string=u'参数明细')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)


class AASMESProductTestTemplateParameter(models.Model):
    _name = 'aas.mes.producttest.template.parameter'
    _description = 'AAS MES ProductTest Template Parameter'
    _rec_name = 'parameter_name'

    template_id = fields.Many2one(comodel_name='aas.mes.producttest.template', string=u'测试', ondelete='cascade')
    sequence = fields.Integer(string=u'序号', required=True)
    active = fields.Boolean(string=u'有效', default=True, copy=False)
    parameter_name = fields.Char(string=u'名称', required=True, copy=False)
    parameter_type = fields.Selection(selection=DATATYPES, string=u'数据类型', default='char', copy=False)
    parameter_note = fields.Text(string=u'备注说明')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)



class AASMESProductTest(models.Model):
    _name = 'aas.mes.producttest'
    _description = 'AAS MES ProductTest'

    name = fields.Char(string=u'名称', copy=False)
    template_id = fields.Many2one(comodel_name='aas.mes.producttest.template', string=u'测试分类', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict', index=True)
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='restrict', index=True)
    active = fields.Boolean(string=u'有效', default=True, copy=False)
    operate_time = fields.Datetime(string=u'创建时间', default=fields.Datetime.now, copy=False)
    operator_id = fields.Many2one('res.users', string=u'创建用户', default=lambda self: self.env.user)
    parameter_lines = fields.One2many('aas.mes.producttest.parameter', inverse_name='producttest_id', string=u'参数明细')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('uniq_test', 'unique (workcenter_id, product_id)', u'请不要重复添加同一个测试信息！')
    ]

    @api.multi
    def action_firstone_checking(self):
        self.ensure_one()
        if not self.parameter_lines or len(self.parameter_lines) <= 0:
            raise UserError(u'请先设置检测参数信息')
        testorder = self.env['aas.mes.producttest.order'].create({
            'producttest_id': self.id, 'product_id': False if not self.product_id else self.product_id.id,
            'workcenter_id': self.workcenter_id.id, 'paramsloaded': True, 'test_type': 'firstone',
            'order_lines': [(0, 0, {'parameter_id': ppline.id}) for ppline in self.parameter_lines]
        })
        view_form = self.env.ref('aas_mes.view_form_aas_mes_producttest_order')
        return {
            'name': u"首件检测",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.producttest.order',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'self',
            'res_id': testorder.id,
            'context': self.env.context
        }



    @api.multi
    def action_lastone_checking(self):
        self.ensure_one()
        if not self.parameter_lines or len(self.parameter_lines) <= 0:
            raise UserError(u'请先设置检测参数信息')
        testorder = self.env['aas.mes.producttest.order'].create({
            'producttest_id': self.id, 'product_id': False if not self.product_id else self.product_id.id,
            'workcenter_id': self.workcenter_id.id, 'paramsloaded': True, 'test_type': 'lastone',
            'order_lines': [(0, 0, {'parameter_id': ppline.id}) for ppline in self.parameter_lines]
        })
        view_form = self.env.ref('aas_mes.view_form_aas_mes_producttest_order')
        return {
            'name': u"末件检测",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.producttest.order',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'self',
            'res_id': testorder.id,
            'context': self.env.context
        }

    @api.multi
    def action_random_checking(self):
        self.ensure_one()
        if not self.parameter_lines or len(self.parameter_lines) <= 0:
            raise UserError(u'请先设置检测参数信息')
        testorder = self.env['aas.mes.producttest.order'].create({
            'producttest_id': self.id, 'product_id': False if not self.product_id else self.product_id.id,
            'workcenter_id': self.workcenter_id.id, 'paramsloaded': True, 'test_type': 'random',
            'order_lines': [(0, 0, {'parameter_id': ppline.id}) for ppline in self.parameter_lines]
        })
        view_form = self.env.ref('aas_mes.view_form_aas_mes_producttest_order')
        return {
            'name': u"抽样检测",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.producttest.order',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'self',
            'res_id': testorder.id,
            'context': self.env.context
        }



class AASMESProductTestParameter(models.Model):
    _name = 'aas.mes.producttest.parameter'
    _description = 'AAS MES ProductTest Parameter'
    _rec_name = 'parameter_name'

    producttest_id = fields.Many2one(comodel_name='aas.mes.producttest', string=u'测试', ondelete='cascade')
    sequence = fields.Integer(string=u'序号', required=True)
    active = fields.Boolean(string=u'有效', default=True, copy=False)
    parameter_name = fields.Char(string=u'名称', required=True, copy=False)
    parameter_type = fields.Selection(selection=DATATYPES, string=u'数据类型', default='char', copy=False)
    parameter_value = fields.Char(string=u'规格值', copy=False)
    parameter_maxvalue = fields.Float(string=u'规格上限')
    parameter_minvalue = fields.Float(string=u'规格下限')
    parameter_note = fields.Text(string=u'备注说明')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)


# 首末件工单
class AASMESProductTestOrder(models.Model):
    _name = 'aas.mes.producttest.order'
    _description = 'AAS MES ProductTest Order'

    name = fields.Char(string=u'名称', copy=False)
    producttest_id = fields.Many2one(comodel_name='aas.mes.producttest', string=u'测试', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict', index=True)
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='restrict', index=True)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='restrict')
    order_date = fields.Char(string=u'日期', copy=False)
    order_time = fields.Datetime(string=u'时间', default=fields.Datetime.now, copy=False)
    paramsloaded = fields.Boolean(string=u'参数加载', default=False, copy=False)
    state = fields.Selection(selection=PRODUCTTESTSTATES, string=u'状态', default='draft', copy=False)
    test_type = fields.Selection(selection=TESTTYPES, string=u'检测类型', default='firstone', copy=False)

    instrument_code = fields.Char(string=u'仪器编码', copy=False)
    fixture_code = fields.Char(string=u'夹具编码', copy=False)
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'当前班次', ondelete='restrict')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'操作员工', ondelete='restrict')

    order_lines = fields.One2many(comodel_name='aas.mes.producttest.order.line', inverse_name='order_id', string=u'检测明细')
    determine_lines = fields.One2many(comodel_name='aas.mes.producttest.order.determine', inverse_name='order_id', string=u'检查明细')

    @api.model
    def create(self, vals):
        vals.update({
            'name': self.env['ir.sequence'].next_by_code('aas.mes.producttest.order'),
            'order_date': fields.Datetime.to_china_string(fields.Datetime.now())[0:10]
        })
        return super(AASMESProductTestOrder, self).create(vals)


    @api.multi
    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(u'%s检测已经执行不可以删除！'% record.name)
        return super(AASMESProductTestOrder, self).unlink()

    @api.one
    def action_loading_producttest(self):
        if not self.workcenter_id:
            raise UserError(u'请先设置好工序信息！')
        tempdomain = [('workcenter_id', '=', self.workcenter_id.id)]
        if self.product_id:
            tempdomain.append(('product_id', '=', self.product_id.id))
        producttest = self.env['aas.mes.producttest'].search(tempdomain, limit=1)
        if not producttest:
            raise UserError(u'请仔细检查可能还未设置相关检测信息')
        if producttest and (not producttest.parameter_lines or len(producttest.parameter_lines) <= 0):
            raise UserError(u'请仔细检查检测信息还未设置检测参数')
        self.write({
            'paramsloaded': True, 'producttest_id': producttest.id,
            'order_lines': [(0, 0, {'parameter_id': ppline.id}) for ppline in producttest.parameter_lines]
        })



class AASMESProductTestOrderLine(models.Model):
    _name = 'aas.mes.producttest.order.line'
    _description = 'AAS MES ProductTest Order Line'

    order_id = fields.Many2one(comodel_name='aas.mes.producttest.order', string=u'首件检测', ondelete='cascade')
    parameter_id = fields.Many2one(comodel_name='aas.mes.producttest.parameter', string=u'参数名称', ondelete='restrict')
    parameter_value = fields.Char(string=u'参数数据', copy=False)
    parameter_note = fields.Char(string=u'备注说明', copy=False)
    qualified = fields.Boolean(string=u'合格', copy=False)




class AASMESProductTestOrderDetermine(models.Model):
    _name = 'aas.mes.producttest.order.determine'
    _description = 'AAS MES ProductTest Order Determine'

    order_id = fields.Many2one(comodel_name='aas.mes.producttest.order', string=u'首件检测', ondelete='cascade')
    determine_type = fields.Selection(selection=DETERMINETYPES, string=u'检查类型', copy=False)
    determine_pass = fields.Boolean(string=u'合格', default=False, copy=False)
    checker_code = fields.Char(string=u'检查人员')
    determine_time = fields.Datetime(string=u'检查时间', default=fields.Datetime.now, copy=False)
    determine_note = fields.Char(string=u'检查备注', copy=False)













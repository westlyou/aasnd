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

import re
import logging

_logger = logging.getLogger(__name__)

DATATYPES = [('char', 'Char'), ('number', 'Number')]

TESTSTATES = [('draft', u'草稿'), ('confirm', u'确认')]

PRODUCTTESTSTATES = [('draft', u'草稿'), ('confirm', u'确认'), ('done', u'完成')]
TESTTYPES = [('firstone', u'首件'), ('lastone', u'末件'), ('random', u'抽检')]


def isfloat(value):
    if not value:
        return False
    if not re.match('^-?[1-9]\d*$', value) and not re.match('^-?([1-9]\d*\.\d*|0\.\d*[1-9]\d*|0?\.0+|0)$', value):
        return False
    return True




# 测试分类
class AASMESProductTestTemplate(models.Model):
    _name = 'aas.mes.producttest.template'
    _description = 'AAS MES ProductTest Template'
    _order = 'id desc'

    name = fields.Char(string=u'名称', copy=False)
    operate_time = fields.Datetime(string=u'创建时间', default=fields.Datetime.now, copy=False)
    operator_id = fields.Many2one('res.users', string=u'创建用户', default=lambda self: self.env.user)
    parameter_lines = fields.One2many(comodel_name='aas.mes.producttest.template.parameter', inverse_name='template_id',
                                      string=u'参数明细')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    @api.multi
    def action_producttest(self):
        """
        设置检测的产品和工序
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.mes.producttest.template.pworkcenter.wizard'].create({'template_id': self.id})
        view_form = self.env.ref('aas_mes.view_form_aas_mes_producttest_template_pworkcenter_wizard')
        return {
            'name': u'设置检测产品和工序',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.producttest.template.pworkcenter.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }


class AASMESProductTestTemplateParameter(models.Model):
    _name = 'aas.mes.producttest.template.parameter'
    _description = 'AAS MES ProductTest Template Parameter'
    _rec_name = 'parameter_name'

    template_id = fields.Many2one(comodel_name='aas.mes.producttest.template', string=u'测试', ondelete='cascade')
    sequence = fields.Integer(string=u'序号', required=True)
    active = fields.Boolean(string=u'有效', default=True, copy=False)
    parameter_name = fields.Char(string=u'名称', copy=False)
    parameter_code = fields.Char(string=u'采集字段', copy=False)
    parameter_type = fields.Selection(selection=DATATYPES, string=u'数据类型', default='char', copy=False)
    firstone = fields.Boolean(string=u'首件', default=False, copy=False)
    lastone = fields.Boolean(string=u'末件', default=False, copy=False)
    random = fields.Boolean(string=u'抽检', default=False, copy=False)
    parameter_note = fields.Text(string=u'备注说明')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('uniq_sequence', 'unique (template_id, sequence)', u'请不要重复添加同一个序号！'),
        ('uniq_name', 'unique (template_id, parameter_name)', u'请不要重复添加同一个参数名称！')
    ]

    @api.multi
    def write(self, vals):
        if 'sequence' in vals:
            raise UserError(u'序号是检测清单参数同步依据，不可以随意修改！')
        templist = []
        for record in self:
            tempdict = {}
            if 'parameter_name' in vals:
                tempdict['parameter_name'] = vals['parameter_name']
            if 'parameter_code' in vals:
                tempdict['parameter_code'] = vals['parameter_code']
            if 'firstone' in vals:
                tempdict['firstone'] = vals['firstone']
            if 'lastone' in vals:
                tempdict['lastone'] = vals['lastone']
            if 'random' in vals:
                tempdict['random'] = vals['random']
            if tempdict and len(tempdict) > 0:
                tempdict.update({'template_id': record.template_id.id, 'sequence': record.sequence})
                templist.append(tempdict)
        result = super(AASMESProductTestTemplateParameter, self).write(vals)
        # 自动更新参数名称和编码
        if templist and len(templist) > 0:
            for tempval in templist:
                tempdomain = [('producttest_id.template_id', '=', tempval['template_id']), ('sequence', '=', tempval['sequence'])]
                parameterlist = self.env['aas.mes.producttest.parameter'].search(tempdomain)
                if not parameterlist or len(parameterlist) <= 0:
                    continue
                paramvals = {}
                if 'parameter_name' in tempval:
                    paramvals['parameter_name'] = tempval.get('parameter_name', False)
                if 'parameter_code' in tempval:
                    paramvals['parameter_code'] = tempval.get('parameter_code', False)
                if 'firstone' in tempval:
                    paramvals['firstone'] = tempval.get('firstone', False)
                if 'lastone' in tempval:
                    paramvals['lastone'] = tempval.get('lastone', False)
                if 'random' in tempval:
                    paramvals['random'] = tempval.get('random', False)
                if paramvals and len(paramvals) > 0:
                    parameterlist.write(paramvals)
        return result

    @api.multi
    def unlink(self):
        templist = []
        for record in self:
            templist.append({'template_id': record.template_id.id, 'sequence': record.sequence})
        delresult = super(AASMESProductTestTemplateParameter, self).unlink()
        for templateseq in templist:
            paramdomain = [('sequence', '=', templateseq['sequence']),
                           ('producttest_id.template_id', '=', templateseq['template_id'])]
            parameterlist = self.env['aas.mes.producttest.parameter'].search(paramdomain)
            if parameterlist and len(parameterlist) > 0:
                parameterlist.unlink()
        return delresult





class AASMESProductTest(models.Model):
    _name = 'aas.mes.producttest'
    _description = 'AAS MES ProductTest'
    _order = 'id desc'

    name = fields.Char(string=u'名称', copy=False)
    template_id = fields.Many2one(comodel_name='aas.mes.producttest.template', string=u'测试分类', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict', index=True)
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict', index=True)
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='restrict', index=True)
    active = fields.Boolean(string=u'有效', default=True, copy=False)
    state = fields.Selection(selection=TESTSTATES, string=u'状态', default='draft', copy=False)
    operate_time = fields.Datetime(string=u'创建时间', default=fields.Datetime.now, copy=False)
    operator_id = fields.Many2one('res.users', string=u'创建用户', default=lambda self: self.env.user)
    parameter_lines = fields.One2many('aas.mes.producttest.parameter', inverse_name='producttest_id', string=u'参数明细')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)


    _sql_constraints = [
        ('uniq_test', 'unique (workstation_id, product_id)', u'请不要重复添加同一个测试信息！')
    ]

    @api.one
    def action_confirm(self):
        self.write({'state': 'confirm'})

    @api.multi
    def action_firstone_checking(self):
        self.ensure_one()
        if not self.parameter_lines or len(self.parameter_lines) <= 0:
            raise UserError(u'请先设置检测参数信息')
        parameterlist = []
        for ppline in self.parameter_lines:
            if not ppline.firstone:
                continue
            parameterlist.append((0, 0, {'parameter_id': ppline.id, 'parameter_code': ppline.parameter_code}))
        if not parameterlist or len(parameterlist) <= 0:
            raise UserError(u'请仔细检查可能您还未设置首件检测参数！')
        testorder = self.env['aas.mes.producttest.order'].create({
            'producttest_id': self.id, 'state': 'confirm', 'test_type': 'firstone',
            'product_id': False if not self.product_id else self.product_id.id,
            'workstation_id': False if not self.workstation_id else self.workstation_id.id,
            'order_lines': parameterlist
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
            'context': self.env.context,
            'flags': {'initial_mode': 'edit'}
        }



    @api.multi
    def action_lastone_checking(self):
        self.ensure_one()
        if not self.parameter_lines or len(self.parameter_lines) <= 0:
            raise UserError(u'请先设置检测参数信息')
        parameterlist = []
        for ppline in self.parameter_lines:
            if not ppline.lastone:
                continue
            parameterlist.append((0, 0, {'parameter_id': ppline.id, 'parameter_code': ppline.parameter_code}))
        if not parameterlist or len(parameterlist) <= 0:
            raise UserError(u'请仔细检查可能您还未设置末件检测参数！')
        testorder = self.env['aas.mes.producttest.order'].create({
            'producttest_id': self.id, 'state': 'confirm', 'test_type': 'lastone',
            'product_id': False if not self.product_id else self.product_id.id,
            'workstation_id': False if not self.workstation_id else self.workstation_id.id,
            'order_lines': parameterlist
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
            'context': self.env.context,
            'flags': {'initial_mode': 'edit'}
        }

    @api.multi
    def action_random_checking(self):
        self.ensure_one()
        if not self.parameter_lines or len(self.parameter_lines) <= 0:
            raise UserError(u'请先设置检测参数信息')
        parameterlist = []
        for ppline in self.parameter_lines:
            if not ppline.random:
                continue
            parameterlist.append((0, 0, {'parameter_id': ppline.id, 'parameter_code': ppline.parameter_code}))
        if not parameterlist or len(parameterlist) <= 0:
            raise UserError(u'请仔细检查可能您还未设置抽样检测参数！')
        testorder = self.env['aas.mes.producttest.order'].create({
            'producttest_id': self.id, 'state': 'confirm', 'test_type': 'random',
            'product_id': False if not self.product_id else self.product_id.id,
            'workstation_id': False if not self.workstation_id else self.workstation_id.id,
            'order_lines': parameterlist
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
            'context': self.env.context,
            'flags': {'initial_mode': 'edit'}
        }


    @api.model
    def loading_producttest(self, productid, workstationid, testtype='firstone'):
        """获取检测参数信息
        :param productid:
        :param workstationid:
        :return:
        """
        values = {'success': True, 'message': '', 'producttestid': 0, 'parameters': []}
        if testtype not in ['firstone', 'lastone', 'random']:
            values.update({'success': False, 'message': u'检测分类异常，分类值只能是(firstone|lastone|random)'})
            return values
        tdomain = [('product_id', '=', productid), ('workstation_id', '=', workstationid)]
        producttest = self.env['aas.mes.producttest'].search(tdomain)
        if not producttest:
            values.update({'success': False, 'message': u'请仔细检查，系统可能还未设置相关质检信息！'})
            return values
        values['producttestid'] = producttest.id
        if not producttest.parameter_lines or len(producttest.parameter_lines) <= 0:
            values.update({'success': False, 'message': u'请仔细检查，检测信息中可能还未设置任何参数！'})
            return values
        parameterlist = []
        for tparameter in producttest.parameter_lines:
            tempval = {
                'id': tparameter.id,
                'name': tparameter.parameter_name, 'type': tparameter.parameter_type,
                'code': '' if not tparameter.parameter_code else tparameter.parameter_code,
                'value': '' if not tparameter.parameter_value else tparameter.parameter_value,
                'maxvalue': tparameter.parameter_maxvalue, 'minvalue': tparameter.parameter_minvalue
            }
            if testtype == 'firstone' and tparameter.firstone:
                parameterlist.append(tempval)
            elif testtype == 'lastone' and tparameter.lastone:
                parameterlist.append(tempval)
            elif testtype == 'random' and tparameter.random:
                parameterlist.append(tempval)
        if not parameterlist or len(parameterlist) <= 0:
            values['success'] = False
            if testtype == 'firstone':
                values['message'] = u'您还未设置首件检测参数！'
            elif testtype == 'lastone':
                values['message'] = u'您还未设置末件检测参数！'
            elif testtype == 'random':
                values['message'] = u'您还未设置抽样检测参数！'
            return values
        values['parameters'] = parameterlist
        return values



    @api.model
    def action_producttest(self, equipmentid, producttestid, parameters, testtype='firstone', workorderid=False, instrument=False, fixture=False):
        """添加首末件抽检操作
        :param equipmentid:
        :param producttestid:
        :param parameters:
        :param testtype:
        :param instrument:
        :param fixture:
        :return:
        """
        values = {'success': True, 'message': '', 'qualified': False}
        equipment = self.env['aas.equipment.equipment'].browse(equipmentid)
        if not equipment:
            values.update({'success': False, 'message': u'请仔细检查，设备异常！'})
            return values
        mesline, workstation = equipment.mesline_id, equipment.workstation_id
        if not mesline or not workstation:
            values.update({'success': False, 'message': u'当前设备可能还未设置产线和工位！'})
            return values
        empdomain = [('mesline_id', '=', mesline.id)]
        empdomain += [('workstation_id', '=', workstation.id), ('equipment_id', '=', equipmentid)]
        employeelist = self.env['aas.mes.workstation.employee'].search(empdomain)
        if not employeelist or len(employeelist) <= 0:
            values.update({'success': False, 'message': u'当前设备上还没有员工在岗！'})
            return values
        employee = employeelist[0].employee_id
        producttest = self.env['aas.mes.producttest'].browse(producttestid)
        if not producttest:
            values.update({'success': False, 'message': u'检测信息异常，请仔细检查！'})
            return values
        if not producttest.parameter_lines or len(producttest.parameter_lines) <= 0:
            values.update({'success': False, 'message': u'请仔细检查，检测信息中可能还未设置任何参数！'})
            return values
        if not parameters or len(parameters) <= 0:
            values.update({'success': False, 'message': u'请仔细检查，您还未设置任何检测参数规格值！'})
            return values
        paramdict = {}
        for ppline in producttest.parameter_lines:
            pkey = 'P'+str(ppline.id)
            tempval = {
                'id': ppline.id, 'name': ppline.parameter_name,
                'type': ppline.parameter_type, 'value': ppline.parameter_value,
                'maxvalue': ppline.parameter_maxvalue, 'minvalue': ppline.parameter_minvalue
            }
            if testtype == 'firstone' and ppline.firstone:
                paramdict[pkey] = tempval
            elif testtype == 'lastone' and ppline.lastone:
                paramdict[pkey] = tempval
            elif testtype == 'random' and ppline.random:
                paramdict[pkey] = tempval
        if not paramdict or len(paramdict) <= 0:
            values.update({'success': False, 'message': u'请仔细检查，是否已经设置了检测参数！'})
            return values
        orderlines = []
        for tparameter in parameters:
            pkey = 'P'+str(tparameter['id'])
            if pkey not in paramdict:
                continue
            pname, pvalue = paramdict.get('name'), tparameter.get('value', False)
            if not pvalue:
                values.update({'success': False, 'message': u'参数%s未设置检测值！'% pname})
                return values
            ptype = paramdict.get('type', 'char')
            if ptype == 'number' and not isfloat(pvalue):
                values.update({'success': False, 'message': u'参数%s检测值必须是一个数值！'% pname})
                return values
            orderlines.append((0, 0, {
                'parameter_id': tparameter['id'], 'parameter_value': pvalue,
                'parameter_code': tparameter['code'], 'parameter_note': tparameter['note']
            }))
            del paramdict[pkey]
        if paramdict and len(paramdict) > 0:
            values.update({'success': False, 'message': u'请仔细检查，还有某些参数未设置检测值！'})
            return values
        ordervals = {
            'producttest_id': producttestid, 'product_id': producttest.product_id.id,
            'workstation_id': producttest.workstation_id.id, 'mesline_id': mesline.id,
            'equipment_id': equipment.id, 'order_date': fields.Datetime.to_china_today(),
            'test_type': testtype, 'instrument_code': instrument, 'fixture_code': fixture,
            'employee_id': employee.id, 'state': 'confirm', 'order_lines': orderlines,
            'schedule_id': False if not mesline.schedule_id else mesline.schedule_id.id
        }
        if workorderid:
            ordervals['workorder_id'] = workorderid
        testorder = self.env['aas.mes.producttest.order'].create(ordervals)
        if testorder.order_lines and len(testorder.order_lines) > 0:
            qualified = all([orderline.qualified for orderline in testorder.order_lines])
            if qualified:
                testorder.write({'qualified': qualified})
        values['qualified'] = testorder.qualified
        return values


    @api.model
    def action_loading_parameters(self, producttest, testtype):
        values = {'success': True, 'message': '', 'parameters': []}
        if not producttest.parameter_lines or len(producttest.parameter_lines) <= 0:
            values.update({'success': False, 'message': u'请仔细检查当前还未设置检测参数！'})
            return values
        parameterlist = []
        for ppline in producttest.parameter_lines:
            tempval = {
                'id': ppline.id, 'name': ppline.parameter_name, 'type': ppline.parameter_type,
                'value': ppline.parameter_value,
                'maxvalue': ppline.parameter_maxvalue, 'minvalue': ppline.parameter_minvalue
            }
            if testtype == 'firstone' and ppline.firstone:
                parameterlist.append(tempval)
            elif testtype == 'lastone' and ppline.lastone:
                parameterlist.append(tempval)
            elif testtype == 'random' and ppline.random:
                parameterlist.append(tempval)
        if not parameterlist or len(parameterlist) <= 0:
            values.update({'success': False, 'message': u'请仔细检查当前还未设置检测参数！'})
            return values
        values['parameters'] = parameterlist
        return values



class AASMESProductTestParameter(models.Model):
    _name = 'aas.mes.producttest.parameter'
    _description = 'AAS MES ProductTest Parameter'
    _rec_name = 'parameter_name'

    producttest_id = fields.Many2one(comodel_name='aas.mes.producttest', string=u'测试', ondelete='cascade')
    sequence = fields.Integer(string=u'序号', required=True)
    active = fields.Boolean(string=u'有效', default=True, copy=False)
    parameter_name = fields.Char(string=u'名称', copy=False)
    parameter_code = fields.Char(string=u'采集字段', copy=False)
    parameter_type = fields.Selection(selection=DATATYPES, string=u'数据类型', default='char', copy=False)
    firstone = fields.Boolean(string=u'首件', default=False, copy=False)
    lastone = fields.Boolean(string=u'末件', default=False, copy=False)
    random = fields.Boolean(string=u'抽检', default=False, copy=False)
    parameter_value = fields.Char(string=u'规格值', copy=False)
    parameter_maxvalue = fields.Float(string=u'规格上限')
    parameter_minvalue = fields.Float(string=u'规格下限')
    parameter_note = fields.Text(string=u'备注说明')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('uniq_sequence', 'unique (template_id, sequence)', u'请不要重复添加同一个序号！'),
        ('uniq_name', 'unique (template_id, parameter_name)', u'请不要重复添加同一个参数名称！')
    ]

    @api.one
    @api.constrains('parameter_type', 'parameter_value')
    def action_check_parameter(self):
        if self.parameter_type == 'number' and self.parameter_value:
            if not isfloat(self.parameter_value):
                raise ValidationError(u'参数%s的规格值必须是一个数值；例如12.34'% self.parameter_name)


# 首末件工单
class AASMESProductTestOrder(models.Model):
    _name = 'aas.mes.producttest.order'
    _description = 'AAS MES ProductTest Order'
    _order = 'id desc'

    name = fields.Char(string=u'名称', copy=False)
    producttest_id = fields.Many2one(comodel_name='aas.mes.producttest', string=u'测试', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict', index=True)
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', ondelete='restrict', index=True)
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict', index=True)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='restrict')
    order_date = fields.Char(string=u'日期', copy=False)
    order_time = fields.Datetime(string=u'时间', default=fields.Datetime.now, copy=False)
    state = fields.Selection(selection=PRODUCTTESTSTATES, string=u'状态', default='draft', copy=False)
    test_type = fields.Selection(selection=TESTTYPES, string=u'检测类型', default='firstone', copy=False)

    instrument_code = fields.Char(string=u'仪器编码', copy=False)
    fixture_code = fields.Char(string=u'夹具编码', copy=False)
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'当前班次', ondelete='restrict')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'操作员工', ondelete='restrict')

    qualified = fields.Boolean(string=u'合格', default=False, copy=False)
    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', index=True)
    wireorder_id = fields.Many2one(comodel_name='aas.mes.wireorder', string=u'线材工单', index=True)
    order_lines = fields.One2many(comodel_name='aas.mes.producttest.order.line', inverse_name='order_id', string=u'参数明细')

    @api.model
    def create(self, vals):
        vals.update({
            'order_date': fields.Datetime.to_china_today(),
            'name': self.env['ir.sequence'].next_by_code('aas.mes.producttest.order')
        })
        return super(AASMESProductTestOrder, self).create(vals)


    @api.multi
    def unlink(self):
        for record in self:
            if record.state not in ['draft', 'confirm']:
                raise UserError(u'%s检测已经执行不可以删除！'% record.name)
        return super(AASMESProductTestOrder, self).unlink()


    @api.one
    def action_confirm(self):
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
            'producttest_id': producttest.id, 'state': 'confirm',
            'order_lines': [(0, 0, {'parameter_id': ppline.id}) for ppline in producttest.parameter_lines]
        })






class AASMESProductTestOrderLine(models.Model):
    _name = 'aas.mes.producttest.order.line'
    _description = 'AAS MES ProductTest Order Line'

    order_id = fields.Many2one(comodel_name='aas.mes.producttest.order', string=u'首件检测', ondelete='cascade')
    parameter_id = fields.Many2one(comodel_name='aas.mes.producttest.parameter', string=u'参数名称', ondelete='restrict')
    parameter_value = fields.Char(string=u'参数数据', copy=False)
    parameter_code = fields.Char(string=u'采集字段', copy=False)
    parameter_note = fields.Char(string=u'备注说明', copy=False)
    qualified = fields.Boolean(string=u'合格', compute="_compute_parameter_qualified", store=True)

    @api.one
    @api.constrains('parameter_id', 'parameter_value')
    def action_check_parameter(self):
        if self.parameter_id.parameter_type == 'number' and self.parameter_value:
            if not isfloat(self.parameter_value):
                raise ValidationError(u'参数%s的规格值必须是一个数值；例如12.34'% self.parameter_id.parameter_name)


    @api.depends('parameter_id', 'parameter_value')
    def _compute_parameter_qualified(self):
        for record in self:
            recordvalue = record.parameter_value
            if not recordvalue:
                record.qualified = False
                continue
            tparameter = record.parameter_id
            if tparameter.parameter_type == 'char':
                record.qualified = True
                continue
            if tparameter.parameter_type == 'number':
                standardvalue = tparameter.parameter_value
                if standardvalue:
                    tempvalue = float(standardvalue) - float(recordvalue)
                    record.qualified = float_is_zero(tempvalue, precision_rounding=0.000001)
                    continue
                maxvalue, minvalue = tparameter.parameter_maxvalue, tparameter.parameter_minvalue
                if maxvalue and float_compare(float(recordvalue), maxvalue, precision_rounding=0.000001) > 0.0:
                    record.qualified = False
                    continue
                if minvalue and float_compare(float(recordvalue), minvalue, precision_rounding=0.000001) < 0.0:
                    record.qualified = False
                    continue
                record.qualified = True



##################################################向导#########################################

class AASMESProductTestTemplatePWorkcenterWizard(models.TransientModel):
    _name = 'aas.mes.producttest.template.pworkcenter.wizard'
    _description = "AAS MES Producttest Template PWorkcenter Wizard"

    template_id = fields.Many2one(comodel_name='aas.mes.producttest.template', string=u'测试分类', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade', index=True)
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='cascade', index=True)


    @api.multi
    def action_done(self):
        self.ensure_one()
        if not self.template_id.parameter_lines or len(self.template_id.parameter_lines) <= 0:
            raise UserError(u'检测分类还未设置参数明细！')
        producttest = self.env['aas.mes.producttest'].create({
            'template_id': self.template_id.id,
            'product_id': self.product_id.id, 'workstation_id': self.workstation_id.id,
            'parameter_lines': [(0, 0, {
                'parameter_code': tparameter.parameter_code,
                'sequence': tparameter.sequence, 'parameter_name': tparameter.parameter_name,
                'parameter_type': tparameter.parameter_type, 'parameter_note': tparameter.parameter_note,
                'firstone': tparameter.firstone, 'lastone': tparameter.lastone, 'random': tparameter.random
            }) for tparameter in self.template_id.parameter_lines]
        })
        view_form = self.env.ref('aas_mes.view_form_aas_mes_producttest')
        return {
            'name': u'检测清单',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.producttest',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'self',
            'res_id': producttest.id,
            'context': self.env.context,
            'flags': {'initial_mode': 'edit'}
        }











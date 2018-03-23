# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-1-6 16:03
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


# 成品标签记录
class AASMESProductionLabel(models.Model):
    _name = 'aas.mes.production.label'
    _description = 'AAS MES Production Label'
    _rec_name = 'label_id'
    _order = 'id desc'

    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', index=True)
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', index=True)
    lot_id = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', index=True)
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', index=True)
    action_time = fields.Datetime(string=u'时间', default=fields.Datetime.now, copy=False)
    action_date = fields.Char(string=u'日期', copy=False, index=True)
    customer_code = fields.Char(string=u'客户编码', copy=False)
    product_code = fields.Char(string=u'产品编码', copy=False)
    isserialnumber = fields.Boolean(string=u'是否序列号', default=False, copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'用户', index=True)
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', index=True)
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', index=True)
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', default=lambda self: self.env.user.company_id)


    @api.model
    def action_gp12_dolabel(self, product_id, productlot_id, product_qty, location_id, equipment_id=False, customer_code=False):
        label = self.env['aas.product.label'].create({
            'product_id': product_id, 'product_lot': productlot_id, 'product_qty': product_qty, 'stocked': True,
            'location_id': location_id, 'company_id': self.env.user.company_id.id, 'customer_code': customer_code
        })
        product_code, chinadate = label.product_code, fields.Datetime.to_china_today()
        self.env['aas.mes.production.label'].create({
            'label_id': label.id, 'product_id': product_id,  'product_qty': product_qty,
            'lot_id': productlot_id, 'product_code': product_code, 'customer_code': customer_code,
            'operator_id': self.env.user.id, 'action_date': chinadate, 'equipment_id': equipment_id,
            'location_id': location_id, 'isserialnumber': True
        })
        return label


    @api.multi
    def action_show_serialnumbers(self):
        self.ensure_one()
        view_form = self.env.ref('aas_mes.view_form_aas_mes_serialnumber')
        view_tree = self.env.ref('aas_mes.view_tree_aas_mes_serialnumber')
        return {
            'name': u"成品清单",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'aas.mes.serialnumber',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'target': 'self',
            'context': self.env.context,
            'domain': "[('label_id','=',"+str(self.label_id.id)+")]"
        }


    @api.multi
    def action_update_serialnumber(self):
        self.ensure_one()
        wizard = self.env['aas.mes.production.label.update.serialnumber.wizard'].create({
            'plabel_id': self.id, 'label_id': self.label_id.id,
            'product_id': self.label_id.product_id.id, 'lot_id': self.label_id.product_lot.id,
            'product_qty': self.label_id.product_qty
        })
        view_form = self.env.ref('aas_mes.view_form_aas_mes_production_label_update_serialnumber_wizard')
        return {
            'name': u"更新标签序列号",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.production.label.update.serialnumber.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }

    @api.multi
    def action_destroy(self):
        self.ensure_one()
        if self.location_id.id != self.label_id.location_id.id:
            raise UserError(u'标签库位已发生变化，不可以解绑！')
        wizard = self.env['aas.mes.production.label.destroy.wizard'].create({
            'plabel_id': self.id, 'product_qty': self.label_id.product_qty,
            'product_id': self.label_id.product_id.id, 'lot_id': self.label_id.product_lot.id
        })
        view_form = self.env.ref('aas_mes.view_form_aas_mes_production_label_destroy_wizard')
        return {
            'name': u"解除标签绑定",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.production.label.destroy.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }


# 成品产出
class AASProductionProduct(models.Model):
    _name = 'aas.production.product'
    _description = 'AAS Production Product'















# 生产产出
class AASMESProductionOutput(models.Model):
    _name = 'aas.mes.production.output'
    _description = 'AAS MES Production Output'
    _order = 'id desc'

    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict', index=True)
    product_code = fields.Char(string=u'产品编码', copy=False)
    customer_pn = fields.Char(string=u'客方编码', copy=False)
    output_time = fields.Datetime(string=u'产出时间', default=fields.Datetime.now, copy=False)
    output_date = fields.Char(string=u'产出日期', copy=False)
    output_qty = fields.Float(string=u'产出数量', default=1.0)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict', index=True)
    mesline_name = fields.Char(string=u'产线名称', copy=False)
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次', ondelete='restrict', index=True)
    schedule_name = fields.Char(string=u'班次名称', copy=False)
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict', index=True)
    workstation_name = fields.Char(string=u'工位名称', copy=False)
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='restrict',index=True)
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', ondelete='restrict', index=True)
    employee_name = fields.Char(string=u'员工', copy=False, index=True)
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', ondelete='restrict', index=True)
    qualified = fields.Boolean(string=u'合格', default=True, copy=False)
    pass_onetime = fields.Boolean(string=u'一次通过', default=True, copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'用户', default=lambda self:self.env.user)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', default=lambda self:self.env.user.company_id)


    @api.model
    def create(self, vals):
        record = super(AASMESProductionOutput, self).create(vals)
        record.write({
            'product_code': record.product_id.default_code, 'schedule_name': record.schedule_id.name,
            'customer_pn': record.product_id.customer_product_code, 'mesline_name': record.mesline_id.name,
            'workstation_name': record.workstation_id.name
        })
        return record

    @api.model
    def action_building_outputrecords(self, meslineid, starttime, finishtime, workstationid=None,
                                      productid=None, equipmentid=None):
        values = {'success': True, 'message': '', 'records': []}
        if finishtime <= starttime:
            values.update({'success': False, 'message': u'请设置有效的开始和结束时间，结束时间必须要大于开始时间！'})
            return values
        tempdomain = [('mesline_id', '=', meslineid)]
        tempdomain += [('output_time', '>=', starttime), ('output_time', '<=', finishtime)]
        if workstationid:
            tempdomain.append(('workstation_id', '=', workstationid))
        if productid:
            tempdomain.append(('product_id', '=', productid))
        if equipmentid:
            tempdomain.append(('equipment_id', '=', equipmentid))
        outputlist = self.env['aas.mes.production.output'].search(tempdomain)
        if not outputlist or len(outputlist) <= 0:
            values.update({'success': False, 'message': u'请确认查询条件，当前可能还没有可以查询的数据'})
            return values
        productquerydict, records = {}, []
        for toutput in outputlist:
            tkey = 'P+'+str(toutput.product_id.id)+'+'+toutput.output_date+'+'+str(toutput.mesline_id.id)+'+'+str(toutput.workstation_id.id)
            if tkey in productquerydict:
                productquerydict[tkey]['product_qty'] += toutput.output_qty
            else:
                product, mesline, workstation = toutput.product_id, toutput.mesline_id, toutput.workstation_id
                productquerydict[tkey] = {
                    'product_id': product.id, 'product_qty': toutput.output_qty,
                    'mesline_id': mesline.id, 'workstation_id': workstation.id,
                    'output_date': toutput.output_date, 'once_rate': 0.0, 'twice_rate': 0.0,
                    'once_qty': 0.0, 'twice_total_qty': 0.0, 'twice_qualified_qty': 0.0,
                    'product_code': '' if not product else product.default_code,
                    'mesline_name': '' if not mesline else mesline.name,
                    'workstation_name': '' if not workstation else workstation.name
                }
            if toutput.pass_onetime:
                productquerydict[tkey]['once_qty'] += toutput.output_qty
            else:
                productquerydict[tkey]['twice_total_qty'] += toutput.output_qty
                if toutput.qualified:
                    productquerydict[tkey]['twice_qualified_qty'] += toutput.output_qty
        for pkey, pval in productquerydict.items():
            total_qty, once_qty = pval['product_qty'], pval['once_qty']
            twice_total_qty, twice_qualified_qty = pval['twice_qualified_qty'], pval['twice_qualified_qty']
            if float_is_zero(twice_total_qty, precision_rounding=0.000001):
                pval['twice_rate'] = 100
            else:
                pval['twice_rate'] = float_round(twice_qualified_qty / twice_total_qty * 100, precision_rounding=0.001)
            pval['once_rate'] = float_round(once_qty / total_qty * 100, precision_rounding=0.001)
            records.append(pval)
        values['records'] = records
        return values











########################################## 向导 ##############################################

# 生产产出以及优率查询
class AASMESProductionOutputQueryWizard(models.TransientModel):
    _name = 'aas.mes.production.output.query.wizard'
    _description = 'AAS MES Production Output Query Wizard'

    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='cascade')
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='cascade')
    time_start = fields.Datetime(string=u'开始时间', copy=False)
    time_finish = fields.Datetime(string=u'结束时间', copy=False)
    query_lines = fields.One2many(comodel_name='aas.mes.production.output.query.line.wizard', inverse_name='wizard_id', string=u'查询明细')

    @api.model
    def default_get(self, fields_list):
        defaults = super(AASMESProductionOutputQueryWizard,self).default_get(fields_list)
        chinatime = fields.Datetime.to_china_time(fields.Datetime.now())
        startime = chinatime.replace(hour=0, minute=0, second=0)
        finishtime = chinatime.replace(hour=23, minute=59, second=59)
        defaults.update({
            'time_start': fields.Datetime.to_utc_string(startime, 'Asia/Shanghai'),
            'time_finish': fields.Datetime.to_utc_string(finishtime, 'Asia/Shanghai')
        })
        return defaults


    @api.multi
    def action_query(self):
        """查询产出汇总数据
        :return:
        """
        self.ensure_one()
        meslineid, starttime, finishtime = self.mesline_id.id, self.time_start, self.time_finish
        workstationid = False if not self.workstation_id else self.workstation_id.id
        productid = False if not self.product_id else self.product_id.id
        equipmentid = False if not self.equipment_id else self.equipment_id.id
        tvalues = self.env['aas.mes.production.output'].action_building_outputrecords(meslineid,
                                                                                      starttime,
                                                                                      finishtime,
                                                                                      workstationid=workstationid,
                                                                                      productid=productid,
                                                                                      equipmentid=equipmentid)
        if not tvalues.get('success', False):
            raise UserError(tvalues.get('message', u'异常错误！'))
        querylines = []
        for record in tvalues.get('records', []):
            querylines.append((0, 0, {
                'product_id': record['product_id'], 'product_qty': record['product_qty'],
                'mesline_id': record['mesline_id'], 'workstation_id': record['workstation_id'],
                'output_date': record['output_date'], 'once_rate': record['once_rate'],
                'twice_rate': record['twice_rate'], 'once_qty': record['once_qty'],
                'twice_total_qty': record['twice_total_qty'], 'twice_qualified_qty': record['twice_qualified_qty']
            }))
        self.write({'query_lines': querylines})
        view_form = self.env.ref('aas_mes.view_form_aas_mes_production_output_query_result')
        return {
            'name': u"查询结果",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.production.output.query.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context
        }







class AASMESProductionOutputQueryLineWizard(models.TransientModel):
    _name = 'aas.mes.production.output.query.line.wizard'
    _description = 'AAS MES Production Output Query Line Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.mes.production.output.query.wizard', string='Wizard', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    product_qty = fields.Float(string=u'总数', default=0.0)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='cascade')
    output_date = fields.Char(string=u'日期', copy=False)
    once_qty = fields.Float(string=u'一次合格数量', default=0.0)
    twice_total_qty = fields.Float(string=u'二次总数', default=0.0)
    twice_qualified_qty = fields.Float(string=u'二次合格数量', default=0.0)
    once_rate = fields.Float(string=u'一次优率', default=0.0)
    twice_rate = fields.Float(string=u'二次优率', default=0.0)



class AASMESProductionLabelUpdateSerialnumberWizard(models.TransientModel):
    _name = 'aas.mes.production.label.update.serialnumber.wizard'
    _description = 'AAS MES Production Label Update Serialnumber Wizard'

    plabel_id = fields.Many2one(comodel_name='aas.mes.production.label', string=u'标签', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    lot_id = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', index=True)
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    add_lines = fields.One2many('aas.mes.production.label.update.addserial.wizard', inverse_name='wizard_id', string=u'新增明细')
    del_lines = fields.One2many('aas.mes.production.label.update.delserial.wizard', inverse_name='wizard_id', string=u'删除明细')

    @api.one
    def action_done(self):
        tlabel, plabel = self.label_id, self.plabel_id
        addcount = 0 if not self.add_lines else len(self.add_lines)
        delcount = 0 if not self.del_lines else len(self.del_lines)
        if addcount <= 0 and delcount <= 0:
            raise UserError(u'请先设置需要新增或则清理的序列号！')
        if addcount > 0:
            aserialnumberlist = self.env['aas.mes.serialnumber']
            for tserial in self.add_lines:
                aserialnumberlist |= tserial.serialnumber_id
            aserialnumberlist.write({'label_id': tlabel.id, 'product_lot': tlabel.product_lot.id})
        if delcount > 0:
            dserialnumberlist, doperationlist = self.env['aas.mes.serialnumber'], self.env['aas.mes.operation']
            for tserial in self.del_lines:
                dserialnumberlist |= tserial.serialnumber_id
                doperationlist |= tserial.serialnumber_id.operation_id
            dserialnumberlist.write({'label_id': False, 'product_lot': False})
            doperationlist.write({'gp12_check': False, 'gp12_record_id': False, 'gp12_date': False, 'gp12_time': False})
        if addcount == delcount:
            return
        labelocation = tlabel.location_id
        pdtlocation = self.env.ref('stock.location_production')
        movevals = {
            'name': tlabel.name, 'product_id': tlabel.product_id.id,
            'company_id': self.env.user.company_id.id, 'product_uom': tlabel.product_id.uom_id.id,
            'create_date': fields.Datetime.now(), 'restrict_lot_id': tlabel.product_lot.id,
            'product_uom_qty': abs(addcount - delcount)
        }
        if addcount > delcount:
            movevals.update({'location_id': pdtlocation.id, 'location_dest_id': labelocation.id})
        else:
            movevals.update({'location_id': labelocation.id, 'location_dest_id': pdtlocation.id})
        self.env['stock.move'].create(movevals).action_done()
        temp_qty = tlabel.product_qty + addcount - delcount
        plabel.write({'product_qty': temp_qty})
        tlabel.write({'product_qty': temp_qty})



class AASMESProductionLabelUpdateAddserialWizard(models.TransientModel):
    _name = 'aas.mes.production.label.update.addserial.wizard'
    _description = 'AAS MES Production Label Update Addserial Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.mes.production.label.update.serialnumber.wizard', string='Wizard', ondelete='cascade')
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    sequence_code = fields.Char(string=u'序列编码', copy=False)

    @api.onchange('serialnumber_id')
    def action_change_serialnumber(self):
        if not self.serialnumber_id:
            self.product_id, self.sequence_code = False, False
        else:
            self.product_id = self.serialnumber_id.product_id.id
            self.sequence_code = self.serialnumber_id.sequence_code

    @api.model
    def create(self, vals):
        record = super(AASMESProductionLabelUpdateAddserialWizard, self).create(vals)
        record.write({
            'product_id': record.serialnumber_id.product_id.id,
            'sequence_code': record.serialnumber_id.sequence_code
        })
        return record


    @api.one
    @api.constrains('serialnumber_id')
    def action_check_serialnumber(self):
        plabel = self.wizard_id.plabel_id
        serialnumber = self.serialnumber_id
        if serialnumber.label_id:
            raise ValidationError(u'序列号%s已绑定在标签%中，不可以随意更换标签'% (serialnumber.name, serialnumber.label_id.name))
        if plabel.label_id.product_id.id != serialnumber.product_id.id:
            raise ValidationError(u'序列号%s与标签%s的产品不一致，不可以添加到此标签中！'% (serialnumber.name, plabel.label_id.name))
        toperation = serialnumber.operation_id
        if not toperation.gp12_check:
            raise ValidationError(u'序列号%s还未通过GP12检测，不可以添加到产出标签！'% serialnumber.name)



class AASMESProductionLabelUpdateDelserialWizard(models.TransientModel):
    _name = 'aas.mes.production.label.update.delserial.wizard'
    _description = 'AAS MES Production Label Update Delserial Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.mes.production.label.update.serialnumber.wizard', string='Wizard', ondelete='cascade')
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    sequence_code = fields.Char(string=u'序列编码', copy=False)


    @api.onchange('serialnumber_id')
    def action_change_serialnumber(self):
        if not self.serialnumber_id:
            self.product_id, self.sequence_code = False, False
        else:
            self.product_id = self.serialnumber_id.product_id.id
            self.sequence_code = self.serialnumber_id.sequence_code

    @api.model
    def create(self, vals):
        record = super(AASMESProductionLabelUpdateDelserialWizard, self).create(vals)
        record.write({
            'product_id': record.serialnumber_id.product_id.id,
            'sequence_code': record.serialnumber_id.sequence_code
        })
        return record

class AASMESProductionLabelDestroyWizard(models.TransientModel):
    _name = 'aas.mes.production.label.destroy.wizard'
    _description = 'AAS MES Production Label Destroy Wizard'

    plabel_id = fields.Many2one(comodel_name='aas.mes.production.label', string=u'标签', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    lot_id = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', index=True)
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    @api.one
    def action_done(self):
        tlabel = self.plabel_id.label_id
        operationlist = self.env['aas.mes.operation']
        serialnumberlist = self.env['aas.mes.serialnumber'].search([('label_id', '=', tlabel.id)])
        if serialnumberlist and len(serialnumberlist) > 0:
            for tserialnumber in serialnumberlist:
                operationlist |= tserialnumber.operation_id
            serialnumberlist.write({'label_id': False})
        if operationlist and len(operationlist) > 0:
            operationlist.write({'gp12_check': False, 'gp12_record_id': False, 'gp12_date': False, 'gp12_time': False})
        if float_compare(tlabel.product_qty, 0.0, precision_rounding=0.000001) > 0.0:
            labelocation, pdtlocation = tlabel.location_id, self.env.ref('stock.location_production')
            self.env['stock.move'].create({
                'name': tlabel.name, 'product_id': tlabel.product_id.id,
                'company_id': self.env.user.company_id.id, 'product_uom': tlabel.product_id.uom_id.id,
                'create_date': fields.Datetime.now(), 'restrict_lot_id': tlabel.product_lot.id,
                'product_uom_qty': tlabel.product_qty, 'location_id': labelocation.id, 'location_dest_id': pdtlocation.id
            }).action_done()
        tlabel.write({'product_qty': 0.0})
        self.plabel_id.unlink()









# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-8-19 17:04
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

from . import MESLINETYPE

import logging

_logger = logging.getLogger(__name__)


class AASBaseCron(models.Model):
    _inherit = 'aas.base.cron'

    @api.model
    def action_thirty_minutes_cron(self):
        # 切换产线班次
        self.env['aas.mes.line'].action_switch_schedule()


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    customer_product_code = fields.Char(string=u'客户编码', copy=False, help=u'产品在客户方的编码')



# 生产线
class AASMESLine(models.Model):
    _name = 'aas.mes.line'
    _description = 'AAS MES Line'

    name = fields.Char(string=u'名称')
    line_type = fields.Selection(selection=MESLINETYPE, string=u'生产类型', default='station', copy=False)
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'当前班次')
    isautoswitch = fields.Boolean(string=u'自动切换', default=False, copy=False, help=u'自动切换产线班次')
    refresh_time = fields.Datetime(string=u'刷新时间', copy=False, help=u'自动刷新班次上的实际开始和结束时间的时间点')
    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'当前工单')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)
    employees = fields.One2many(comodel_name='aas.hr.employee', inverse_name='mesline_id', string=u'员工清单')
    location_production_id = fields.Many2one(comodel_name='stock.location', string=u'成品库位', ondelete='restrict')
    location_material_list = fields.One2many(comodel_name='aas.mes.line.material.location', inverse_name='mesline_id', string=u'原料库位')
    schedule_lines = fields.One2many(comodel_name='aas.mes.schedule', inverse_name='mesline_id', string=u'班次清单')

    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'默认工位')

    _sql_constraints = [
        ('uniq_name', 'unique (name)', u'产线名称不可以重复！')
    ]

    @api.multi
    def action_allocate_employee(self):
        """
        直接对班次分配员工
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.mes.line.allocate.wizard'].create({'mesline_id': self.id})
        view_form = self.env.ref('aas_mes.view_form_aas_mes_line_allocate_wizard')
        return {
            'name': u"员工分配",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.line.allocate.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }

    @api.one
    def action_refresh_schedule_times(self):
        if self.schedule_lines and len(self.schedule_lines) > 0:
            if not self.refresh_time:
                self.schedule_lines.action_refresh_actualtime()
            else:
                currentdate = fields.Datetime.to_timezone_string(fields.Datetime.now(), 'Asia/Shanghai')[0:10]
                refreshdate = fields.Datetime.to_timezone_string(self.refresh_time, 'Asia/Shanghai')[0:10]
                if currentdate != refreshdate:
                    self.schedule_lines.action_refresh_actualtime()

    @api.model
    def action_switch_schedule(self):
        """
        切换产线班次
        :return:
        """
        meslines = self.env['aas.mes.line'].search([('isautoswitch', '=', True)])
        if not meslines or len(meslines) <= 0:
            return False
        currenttime = fields.Datetime.now()
        for mesline in meslines:
            mesline.action_refresh_schedule_times()
            searchdomain = [('mesline_id', '=', mesline.id)]
            searchdomain.extend([('actual_start', '<=', currenttime), ('actual_finish', '>=', currenttime)])
            schedule = self.env['aas.mes.schedule'].search(searchdomain, limit=1)
            if not schedule:
                continue
            if not mesline.schedule_id or mesline.schedule_id.id != schedule.id:
                mesline.write({'schedule_id': schedule.id, 'workorder_id': False})
                self.action_clear_feeding(mesline.id)
                self.action_clear_employees(mesline.id)


    @api.model
    def action_clear_feeding(self, mesline_id):
        """
        清除当前产线的上料记录
        :param mesline_id:
        :return:
        """
        feedmateriallist = self.env['aas.mes.feedmaterial'].search([('mesline_id', '=', mesline_id)])
        if feedmateriallist and len(feedmateriallist) > 0:
            feedmateriallist.unlink()


    @api.model
    def action_clear_employees(self, mesline_id):
        attendancelist = self.env['aas.mes.work.attendance'].search([('mesline_id', '=', mesline_id), ('attend_done', '=', False)])
        if attendancelist and len(attendancelist) > 0:
            for attendance in attendancelist:
                attendance.action_done()






class AASMESLineMaterialLocation(models.Model):
    _name = 'aas.mes.line.material.location'
    _description = 'AAS MES Line Material Location'
    _rec_name = 'location_id'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')
    location_note = fields.Char(string=u'描述', copy=False)

    _sql_constraints = [
        ('uniq_location', 'unique (mesline_id, location_id)', u'同一产线的原料库位请不要重复！')
    ]


class AASHREmployee(models.Model):
    _inherit = 'aas.hr.employee'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线')
    meslines = fields.One2many(comodel_name='aas.mes.line.employee', inverse_name='employee_id', string=u'产线调整记录')

    @api.multi
    def action_allocate_mesline(self):
        """
        员工分配产线
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.mes.employee.allocate.mesline.wizard'].create({'employee_id': self.id})
        view_form = self.env.ref('aas_mes.view_form_aas_mes_employee_allocate_mesline_wizard')
        return {
            'name': u"分配产线",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.employee.allocate.mesline.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }





# 员工产线调整记录
class AASMESLineEmployee(models.Model):
    _name = 'aas.mes.line.employee'
    _description = 'AAS MES Line Employee'
    _order = 'id desc'

    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', ondelete='restrict')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    action_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    action_user = fields.Many2one(comodel_name='res.users', string=u'操作人', ondelete='restrict', default=lambda self: self.env.user)

    @api.model
    def create(self, vals):
        record = super(AASMESLineEmployee, self).create(vals)
        record.action_after_create()
        return record

    @api.one
    def action_after_create(self):
        empvals = {}
        if self.mesline_id:
            empvals['mesline_id'] = self.mesline_id.id
        if empvals and len(empvals) > 0:
            self.employee_id.write(empvals)




# 库存盘点
class AASStockInventory(models.Model):
    _inherit = 'aas.stock.inventory'

    isproductionline = fields.Boolean(string=u'产线盘点', default=False, copy=False)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')

    @api.multi
    def action_refresh(self):
        self.ensure_one()
        if not self.isproductionline:
            return self.action_wms_refresh()
        else:
            return self.action_mes_refresh()

    @api.multi
    def action_mes_refresh(self):
        self.ensure_one()
        locationlist = [self.mesline_id.location_production_id.id]
        for mlocation in self.mesline_id.location_material_list:
            locationlist.append(mlocation.location_id.id)
        tempdomain = [('location_id', 'in', locationlist)]
        if self.product_id:
            tempdomain.append(('product_id', '=', self.product_id.id))
        quantlist = self.env['stock.quant'].search(tempdomain)
        if not quantlist or len(quantlist) <= 0:
            return False
        tempdict = {}
        for tquant in quantlist:
            pkey = 'P_'+str(tquant.product_id.id)+'_'+str(tquant.lot_id.id)+'_'+str(tquant.location_id.id)
            if pkey not in tempdict:
                tempdict[pkey] = {
                    'product_id': tquant.product_id.id, 'product_lot': tquant.lot_id.id,
                    'location_id': tquant.location_id.id, 'stock_qty': tquant.qty
                }
            else:
                tempdict[pkey]['stock_qty'] += tquant.qty
        templines = []
        if self.inventory_lines and len(self.inventory_lines) > 0:
            for iline in self.inventory_lines:
                pkey = 'P_'+str(iline.product_id.id)+'_'+str(iline.product_lot.id)+'_'+str(iline.location_id.id)
                if pkey in tempdict:
                    templines.append((1, iline.id, {'stock_qty': tempdict[pkey]['stock_qty']}))
                    del tempdict[pkey]
                else:
                    templines.append((2, iline.id, False))
        if tempdict and len(tempdict) > 0:
            templines.extend([(0, 0, tval) for tkey, tval in tempdict.items()])
        self.write({'inventory_lines': templines})
        return True


class AASStockInventoryLabel(models.Model):
    _inherit = 'aas.stock.inventory.label'

    @api.one
    @api.constrains('label_id')
    def action_check_label(self):
        tlabel, tinventory = self.label_id, self.inventory_id
        if tlabel.state not in ['normal', 'frozen']:
            raise ValidationError(u'无效标签请仔细检查！')
        if tinventory.product_id and tinventory.product_id.id != tlabel.product_id.id:
            raise ValidationError(u'请仔细检查，标签的产品不在盘点范围内！')
        if tinventory.product_lot and tinventory.product_lot.id != tlabel.product_lot.id:
            raise ValidationError(u'请仔细检查，标签产品批次不在盘点范围内！')
        if tinventory.location_id:
            parent_left, parent_right = tinventory.location_id.parent_left, tinventory.location_id.parent_right
            if tlabel.location_id.parent_left < parent_left or tlabel.location_id.parent_right > parent_right:
                raise ValidationError(u'请仔细检查，标签库位不在盘点范围！')
        if tinventory.mesline_id:
            mesline = tinventory.mesline_id
            parent_left, parent_right = tinventory.location_id.parent_left, tinventory.location_id.parent_right
            locationlist = [(mesline.location_production_id.parent_left, mesline.location_production_id.parent_right)]
            for mlocation in mesline.location_material_list:
                templocation = mlocation.location_id
                locationlist.append((templocation.parent_left, templocation.parent_right))
            checkingflag = False
            for tlocation in locationlist:
                if parent_left >= tlocation[0] and parent_right <= tlocation[1]:
                    checkingflag = True
                    break
            if not checkingflag:
                raise ValidationError(u'请仔细检查，标签库位不在盘点范围！')



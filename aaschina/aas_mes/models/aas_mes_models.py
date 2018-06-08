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
from odoo.tools.float_utils import float_compare, float_repr
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

# 不良物料挑选
class AASMESBadMaterialSelection(models.Model):
    _name = 'aas.mes.badmaterial.selection'
    _description = 'AAS MES Bad Material Selection'
    _order = 'id desc'
    _rec_name = 'internal_material_id'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线')
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'问题工位')
    selector_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'挑选员工')
    selector_code = fields.Char(string=u'员工工号', compute='_compute_selector_code', store=True)
    ipqchecker_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'IPQC员工')
    ipqchecker_code = fields.Char(string=u'IPQC工号')
    ipqcheck_time = fields.Datetime(string=u'IPQC确认时间')
    internal_material_id = fields.Many2one(comodel_name='product.product', string=u'内部料号')
    customer_material_code = fields.Char(string=u'客户料号', compute='_compute_cusmtomer_code', store=True)
    badmode_id = fields.Many2one(comodel_name='aas.mes.badmode', string=u'不良模式')
    product_qty = fields.Float(string=u'总数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    badmode_qty = fields.Float(string=u'不良数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    material_yield = fields.Float(string=u'良率', compute='_compute_material_yield', store=True)
    action_start = fields.Datetime(string=u'开始时间', copy=False)
    action_finish = fields.Datetime(string=u'结束时间', copy=False)
    action_worktime = fields.Float(string=u'总工时(H)', default=0.0)
    state = fields.Selection(selection=[('select', u'挑选'), ('done', u'完成')], string=u'状态', default='select')

    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(u'请仔细检查，已完成的记录是不可以删除的！')
        return super(AASMESBadMaterialSelection, self).unlink()


    @api.depends('product_qty', 'badmode_qty')
    def _compute_material_yield(self):
        for record in self:
            pdtflag = record.product_qty and float_compare(record.product_qty, 0.0, precision_rounding=0.000001) > 0.0
            badflag = record.badmode_qty and float_compare(record.badmode_qty, 0.0, precision_rounding=0.000001) > 0.0
            if pdtflag and badflag:
                material_yield = (record.product_qty - record.badmode_qty) / record.product_qty * 100.0
                record.material_yield = float_repr(material_yield, 2)
            else:
                record.material_yield = 0.00


    @api.onchange('selector_id')
    def action_change_selector(self):
        if not self.selector_id:
            self.selector_code = False
        else:
            self.selector_code = self.selector_id.code

    @api.depends('selector_id')
    def _compute_selector_code(self):
        for record in self:
            record.selector_code = False if not record.selector_id else record.selector_id.code

    @api.depends('internal_material_id')
    def _compute_cusmtomer_code(self):
        for record in self:
            material = record.internal_material_id
            record.customer_material_code = False if not material else material.customer_product_code


    @api.one
    @api.constrains('product_qty', 'badmode_qty')
    def action_check_selection_qty(self):
        if float_compare(self.product_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise ValidationError(u'总数量必须是大于0的数！')
        if float_compare(self.badmode_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise ValidationError(u'不良数量必须是大于0的数！')
        if float_compare(self.badmode_qty, self.product_qty, precision_rounding=0.000001) > 0.0:
            raise ValidationError(u'不良数量不能大于总数量！')

    @api.one
    @api.constrains('action_start', 'action_finish')
    def action_check_action_time(self):
        if self.action_start and self.action_finish and self.action_finish <= self.action_start:
            raise ValidationError(u'结束时间必须大于开始时间！')

    @api.multi
    def action_ipqchecking(self):
        """IPQC确认
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.mes.badmaterial.ipqcheck.wizard'].create({'selection_id': self.id})
        view_form = self.env.ref('aas_mes.view_form_aas_mes_badmaterial_ipqcheck_wizard')
        return {
            'name': u"IPQC确认",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.badmaterial.ipqcheck.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }



class AASHREmployee(models.Model):
    _inherit = 'aas.hr.employee'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线')
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
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
        tempdomain = [('location_id', 'child_of', locationlist)]
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
                    'product_id': tquant.product_id.id, 'stock_qty': tquant.qty,
                    'location_id': tquant.location_id.id, 'product_lot': tquant.lot_id.id
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

    @api.one
    def action_done(self):
        super(AASStockInventory, self).action_done()
        # 消亡标签更新为正常; 只针对线边库
        if self.inventory_labels and len(self.inventory_labels) > 0:
            labellist = self.env['aas.product.label']
            for ilabel in self.inventory_labels:
                if ilabel.label_id.state == 'over':
                    labellist |= ilabel.label_id
            if labellist and len(labellist) > 0:
                labellist.write({'state': 'normal'})


    @api.model
    def action_scan_label(self, inventory, barcode):
        """扫描标签盘点
        :param barcode:
        :return:
        """
        values = {'success': True, 'message': '', 'ilabel': False}
        if not barcode:
            values.update({'success': False, 'message': u'请仔细检查是否扫描了一个有效的条码！'})
            return values
        barcode = barcode.upper()
        label = self.env['aas.product.label'].search([('barcode', '=', barcode)], limit=1)
        if not label:
            values.update({'success': False, 'message': u'请仔细检查是否扫描有效的标签！'})
            return values
        labeldomain = [('inventory_id', '=', inventory.id), ('label_id', '=', label.id)]
        if self.env['aas.stock.inventory.label'].search_count(labeldomain) > 0:
            values.update({'success': False, 'message': u'标签已存在请不要重复扫描！'})
            return values
        if label.state not in ['normal', 'frezon']:
            values.update({'success': False, 'message': u'标签状态异常，不在盘点范围！'})
            return values
        if inventory.product_id and inventory.product_id.id != label.product_id.id:
            values.update({'success': False, 'message': u'标签产品与需要盘点的产品不一致，不在盘点范围！'})
            return values
        if inventory.product_lot and inventory.product_lot.id != label.product_lot.id:
            values.update({'success': False, 'message': u'标签产品批次与需要盘点的产品批次不一致，不在盘点范围！'})
            return values
        if inventory.location_id:
            ipleft, ipright = inventory.location_id.parent_left, inventory.location_id.parent_right
            lpleft, lpright = label.location_id.parent_left, label.location_id.parent_right
            if lpleft < ipleft or lpright > ipright:
                values.update({'success': False, 'message': u'标签产品库位与需要盘点的产品库位不一致，不在盘点范围！'})
                return values
        if inventory.mesline_id:
            llocations = []
            lpleft, lpright = label.location_id.parent_left, label.location_id.parent_right
            if inventory.mesline_id.location_production_id:
                plocation = inventory.mesline_id.location_production_id
                llocations.append((plocation.parent_left, plocation.parent_right))
            if inventory.mesline_id.location_material_list and len(inventory.mesline_id.location_material_list) > 0:
                for mlocation in inventory.mesline_id.location_material_list:
                    tmlocation = mlocation.location_id
                    llocations.append((tmlocation.parent_left, tmlocation.parent_right))
            passflag = False
            if llocations and len(llocations) > 0:
                for llocation in llocations:
                    if lpleft >= llocation[0] and lpright <= llocations[1]:
                        passflag = True
                        break
            if not passflag:
                values.update({'success': False, 'message': u'标签产品库位与需要盘点的产品库位不一致，不在盘点范围！'})
                return values
        ilabel = self.env['aas.stock.inventory.label'].create({'inventory_id': inventory.id, 'label_id': label.id})
        values['ilabel'] = {
            'list_id': ilabel.id, 'product_code': ilabel.product_id.default_code,
            'product_lot': ilabel.product_lot.name, 'product_qty': ilabel.product_qty,
            'location_name': ilabel.location_id.name, 'label_name': ilabel.label_id.name, 'container_name': ''
        }
        return values


    @api.model
    def action_scan_container(self, inventory, barcode):
        """扫描容器盘点
        :param barcode:
        :return:
        """
        values = {'success': True, 'message': '', 'ilabel': False}
        if not barcode:
            values.update({'success': False, 'message': u'请仔细检查是否扫描了一个有效的容器！'})
            return values
        barcode = barcode.upper()
        container = self.env['aas.container'].search([('barcode', '=', barcode)], limit=1)
        if not container:
            values.update({'success': False, 'message': u'请仔细检查是否扫描有效的容器！'})
            return values
        cdomain = [('inventory_id', '=', inventory.id), ('container_id', '=', container.id)]
        if self.env['aas.stock.inventory.label'].search_count(cdomain) > 0:
            values.update({'success': False, 'message': u'容器已存在请不要重复扫描！'})
            return values
        if container.isempty:
            values.update({'success': False, 'message': u'当前容器是一个空的容器，不可以盘点！'})
            return values
        productline = container.product_lines[0]
        if inventory.product_id and inventory.product_id.id != productline.product_id.id:
            values.update({'success': False, 'message': u'容器产品与需要盘点的产品不一致，不在盘点范围！'})
            return values
        if inventory.product_lot and inventory.product_lot.id != productline.product_lot.id:
            values.update({'success': False, 'message': u'容器产品批次与需要盘点的产品批次不一致，不在盘点范围！'})
            return values
        if inventory.location_id:
            ipleft, ipright = inventory.location_id.parent_left, inventory.location_id.parent_right
            cpleft, cpright = container.stock_location_id.parent_left, container.stock_location_id.parent_right
            if cpleft < ipleft or cpright > ipright:
                values.update({'success': False, 'message': u'容器产品库位与需要盘点的产品库位不一致，不在盘点范围！'})
                return values
        if inventory.mesline_id:
            llocations = []
            cpleft, cpright = container.stock_location_id.parent_left, container.stock_location_id.parent_right
            if inventory.mesline_id.location_production_id:
                plocation = inventory.mesline_id.location_production_id
                llocations.append((plocation.parent_left, plocation.parent_right))
            if inventory.mesline_id.location_material_list and len(inventory.mesline_id.location_material_list) > 0:
                for mlocation in inventory.mesline_id.location_material_list:
                    tmlocation = mlocation.location_id
                    llocations.append((tmlocation.parent_left, tmlocation.parent_right))
            passflag = False
            if llocations and len(llocations) > 0:
                for llocation in llocations:
                    if cpleft >= llocation[0] and cpright <= llocations[1]:
                        passflag = True
                        break
            if not passflag:
                values.update({'success': False, 'message': u'容器产品库位与需要盘点的产品库位不一致，不在盘点范围！'})
                return values
        ilabel = self.env['aas.stock.inventory.label'].create({'inventory_id': inventory.id, 'container_id': container.id})
        values['ilabel'] = {
            'list_id': ilabel.id, 'product_code': ilabel.product_id.default_code,
            'product_lot': ilabel.product_lot.name, 'product_qty': ilabel.product_qty,
            'location_name': ilabel.location_id.name, 'label_name': '', 'container_name': ilabel.container_id.name
        }
        return values


class AASStockInventoryLabel(models.Model):
    _inherit = 'aas.stock.inventory.label'

    @api.one
    @api.constrains('label_id')
    def action_check_label(self):
        tlabel, tinventory, production = self.label_id, self.inventory_id, self.inventory_id.isproductionline
        if not production and (tlabel.state not in ['normal', 'frozen']):
            raise ValidationError(u'无效标签,可能已经消亡或是草稿标签，请仔细检查！')
        if production and tlabel.state == 'draft':
            raise ValidationError(u'草稿标签不可用作盘点！')
        if tinventory.product_id and tinventory.product_id.id != tlabel.product_id.id:
            raise ValidationError(u'请仔细检查，标签的产品不在盘点范围内！')
        if tinventory.product_lot and tinventory.product_lot.id != tlabel.product_lot.id:
            raise ValidationError(u'请仔细检查，标签产品批次不在盘点范围内！')
        locationids, ilocation, imesline = [], tinventory.location_id, tinventory.mesline_id
        if ilocation:
            locationids.append(ilocation.id)
        if imesline:
            if not imesline.location_production_id or (not imesline.location_material_list or len(imesline.location_material_list) <= 0):
                raise ValidationError(u'请仔细检查，产线还未设置原料库位信息！')
            locationids.append(imesline.location_production_id.id)
            for mlocation in imesline.location_material_list:
                locationids.append(mlocation.location_id.id)
        locationlist = self.env['stock.location'].search([('id', 'child_of', locationids)])
        if tlabel.location_id.id not in locationlist.ids:
            raise ValidationError(u'请仔细检查，标签库位不在盘点范围！')



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

import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    customer_product_code = fields.Char(string=u'客户编码', copy=False, help=u'产品在客户方的编码')



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



# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-5-25 10:26
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class AASStockDelivery(models.Model):
    _inherit = 'aas.stock.delivery'

    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'生产工单')


class AASMESWorkorder(models.Model):
    _inherit = 'aas.mes.workorder'

    delivery_id = fields.Many2one(comodel_name='aas.stock.delivery', string=u'备料单')




    @api.multi
    def action_prepare_material(self):
        """备料
        :return:
        """
        self.ensure_one()
        if self.delivery_id:
            return
        if self.state != 'confirm':
            raise UserError(u'工单只有确认状态才可以备料！')
        if not self.aas_bom_id:
            raise UserError(u'当前工单未设置物料清单，无法生成备料清单！')
        if not self.aas_bom_id.bom_lines or len(self.aas_bom_id.bom_lines) <= 0:
            raise UserError(u'请仔细检查物料清单设置是否正确！')
        if not self.mesline_id:
            raise UserError(u'当前工单还未设置产线！')
        wizardvals = {
            'workorder_id': self.id, 'mesline_id': self.mesline_id.id,
            'product_id': self.product_id.id, 'product_qty': self.input_qty, 'material_lines': []
        }
        bomqty = self.aas_bom_id.product_qty
        for bline in self.aas_bom_id.bom_lines:
            if not bline.product_id.ismaterial:
                continue
            wizardvals['material_lines'].append((0, 0, {
                'material_id': bline.product_id.id,
                'material_qty': bline.product_qty / bomqty * self.input_qty
            }))
        if not wizardvals['material_lines'] and len(wizardvals['material_lines']) <= 0:
            raise UserError(u'当前工单无需备料！')
        preparewizard = self.env['aas.mes.preparation.wizard'].create(wizardvals)
        view_form = self.env.ref('aas_mes.view_form_aas_mes_preparation_wizard')
        return {
            'name': u"工单备料",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.preparation.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': preparewizard.id,
            'context': self.env.context
        }






class AASMESPreparationWizard(models.TransientModel):
    _name = 'aas.mes.preparation.wizard'
    _description = u'备料'

    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'生产工单', ondelete='cascade')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    product_qty = fields.Float(string=u'投入数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    material_lines = fields.One2many('aas.mes.preparation.material.wizard', inverse_name='wizard_id', string=u'备料清单')

    @api.one
    def action_done(self):
        if not self.material_lines or len(self.material_lines) <= 0:
            raise UserError(u'请先添加备料清单明细！')
        if not self.mesline_id.location_material_list or len(self.mesline_id.location_material_list) <= 0:
            raise UserError(u'%s产线还未设置原料库位！'% self.mesline_id.name)
        destlocation = self.mesline_id.location_material_list[0].location_id
        deliverylines = []
        for mline in self.material_lines:
            if float_compare(mline.material_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                raise UserError(u'%s备料数量必须是一个大于0的数！'% mline.material_id.default_code)
            deliverylines.append((0, 0, {
                'product_id': mline.material_id.id, 'delivery_type': 'manufacture',
                'product_qty': mline.material_qty, 'state': 'confirm'
            }))
        delivery = self.env['aas.stock.delivery'].create({
            'state': 'confirm', 'delivery_type': 'manufacture',
            'workorder_id': self.workorder_id.id, 'origin_order': self.workorder_id.name,
            'delivery_lines': deliverylines, 'location_id': destlocation.id
        })
        self.workorder_id.write({'delivery_id': delivery.id})




class AASMESPreparationMaterialWizard(models.TransientModel):
    _name = 'aas.mes.preparation.material.wizard'
    _description = u'备料清单'

    wizard_id = fields.Many2one(comodel_name='aas.mes.preparation.wizard', string='Wizard', ondelete='cascade')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料', ondelete='cascade')
    material_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

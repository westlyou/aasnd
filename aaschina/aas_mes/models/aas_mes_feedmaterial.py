# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-9-23 21:04
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


# 上料
class AASMESFeedmaterial(models.Model):
    _name = 'aas.mes.feedmaterial'
    _description = 'AAS MES Feed Material'
    _rec_name = 'material_id'
    _order = 'feed_time desc'


    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料', ondelete='restrict')
    material_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    material_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    material_qty = fields.Float(string=u'现场库存', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    feed_time = fields.Datetime(string=u'上料时间', default=fields.Datetime.now, copy=False)
    feeder_id = fields.Many2one(comodel_name='res.users', string=u'上料员', default= lambda self:self.env.user)


    _sql_constraints = [
        ('uniq_materiallot', 'unique (mesline_id, workstation_id, material_id, material_lot)', u'请不要在工位上重复添加同一批次的物料！')
    ]


    @api.model
    def get_material_qty(self, record):
        material_qty = 0.0
        domain = [('product_id', '=', record.material_id.id), ('lot_id', '=', record.material_lot.id)]
        location_ids = [record.mesline_id.location_production_id.id]
        for mlocation in record.mesline_id.location_material_list:
            location_ids.append(mlocation.location_id.id)
        domain.append(('location_id', 'child_of', location_ids))
        quants = self.env['stock.quant'].search(domain)
        if quants and len(quants) > 0:
            material_qty = sum([quant.qty for quant in quants])
        if float_compare(record.material_qty, material_qty, precision_rounding=0.000001) != 0.0:
            record.write({'material_qty': material_qty})
        return material_qty


    @api.one
    def action_refresh_stock(self):
        self.get_material_qty(self)

    @api.multi
    def action_checking_quants(self):
        """
        整理库存份
        :return:
        """
        self.ensure_one()
        domain = [('product_id', '=', self.material_id.id), ('lot_id', '=', self.material_lot.id)]
        location_ids = [self.mesline_id.location_production_id.id]
        for mlocation in self.mesline_id.location_material_list:
            location_ids.append(mlocation.location_id.id)
        domain.append(('location_id', 'in', location_ids))
        quants = self.env['stock.quant'].search(domain)
        if quants and len(quants) > 0:
            temp_qty = sum([quant.qty for quant in quants])
            if not float_is_zero(self.material_qty-temp_qty, precision_rounding=0.000001):
                self.write({'material_qty': temp_qty})
        return quants


    @api.model
    def create(self, vals):
        record = super(AASMESFeedmaterial, self).create(vals)
        record.write({'material_uom': record.material_id.uom_id.id})
        record.action_refresh_stock()
        return record


    @api.onchange('material_id')
    def action_change_material(self):
        if self.material_id:
            self.material_uom = self.material_id.uom_id.id
        else:
            self.material_uom = False



    @api.model
    def get_workstation_materiallist(self, equipment_code):
        """
        根据设备获取相应产线工位的上料清单
        :param equipment_code:
        :return:
        """
        values = {'success': True, 'message': '', 'materiallist': []}
        equipment = self.env['aas.equipment.equipment'].search([('code', '=', equipment_code)], limit=1)
        if not equipment:
            values.update({'success': False, 'message': u'请仔细检查设备编码是否正确，系统中未搜索到此设备！'})
            return values
        if not equipment.mesline_id or not equipment.workstation_id:
            values.update({'success': False, 'message': u'设备当前还未绑定产线和工位，请联系相关人员设置产线和工位！'})
            return values
        feeddomain = [('mesline_id', '=', equipment.mesline_id.id), ('workstation_id', '=', equipment.workstation_id.id)]
        feedmateriallist = self.env['aas.mes.feedmaterial'].search(feeddomain)
        if feedmateriallist and len(feedmateriallist) > 0:
            values['materiallist'] = [{
                'material_id': feedmaterial.material_id.id, 'material_code': feedmaterial.material_id.default_code,
                'materiallot_id': feedmaterial.material_lot.id, 'materiallot_name': feedmaterial.material_lot.name,
                'material_qty': feedmaterial.material_qty
            } for feedmaterial in feedmateriallist]
        return values

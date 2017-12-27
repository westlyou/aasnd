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
    _order = 'feed_time asc'

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
        material, materialot, mesline = record.material_id, record.material_lot, record.mesline_id
        materialdomain = [('product_id', '=', material.id), ('lot_id', '=', materialot.id)]
        locationids = [mesline.location_production_id.id]
        locationids += [mlocation.location_id.id for mlocation in mesline.location_material_list]
        materialdomain.append(('location_id', 'child_of', locationids))
        quants = self.env['stock.quant'].search(materialdomain)
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
        """整理库存份
        :return:
        """
        self.ensure_one()
        mesline, material, mtlot = self.mesline_id, self.material_id, self.material_lot
        quantdomain = [('product_id', '=', material.id), ('lot_id', '=', mtlot.id)]
        locationids = [mesline.location_production_id.id]
        locationids += [mlocation.location_id.id for mlocation in mesline.location_material_list]
        quantdomain += [('location_id', 'child_of', locationids)]
        quants = self.env['stock.quant'].search(quantdomain)
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
    def get_workstation_materiallist(self, equipment_code, withlots=False):
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
            if withlots:
                values['materiallist'] = [{
                    'material_id': feedmaterial.material_id.id, 'material_code': feedmaterial.material_id.default_code,
                    'materiallot_id': feedmaterial.material_lot.id, 'materiallot_name': feedmaterial.material_lot.name,
                    'material_qty': feedmaterial.material_qty
                } for feedmaterial in feedmateriallist]
            else:
                materialdict = {}
                for feedmaterial in feedmateriallist:
                    mkey = 'M'+str(feedmaterial.material_id.id)
                    if mkey not in materialdict:
                        materialdict[mkey] = {
                            'material_id': feedmaterial.material_id.id,
                            'material_qty': feedmaterial.material_qty,
                            'materiallots': [feedmaterial.material_lot.name],
                            'material_code': feedmaterial.material_id.default_code
                        }
                    else:
                        materialdict[mkey]['material_qty'] += feedmaterial.material_qty
                        if feedmaterial.material_lot.name not in materialdict[mkey]['materiallots']:
                            materialdict[mkey]['materiallots'].append(feedmaterial.material_lot.name)
                tmateriallist = []
                for tmaterial in materialdict.values():
                    tmateriallist.append({
                        'material_id': tmaterial['material_id'], 'material_qty': tmaterial['material_qty'],
                        'materiallot_id': 0, 'materiallot_name': ','.join(tmaterial['materiallots']),
                        'material_code': tmaterial['material_code']
                    })
                values['materiallist'] = tmateriallist
        return values

    @api.model
    def action_feed_onstationclient(self, equipment_code, barcode):
        """
        工控工位上料
        :param equipment_code:
        :param barcode:
        :return:
        """
        values = {'success': True, 'message': ''}
        equipment = self.env['aas.equipment.equipment'].search([('code', '=', equipment_code)], limit=1)
        if not equipment:
            values.update({'success': False, 'message': u'设备编码异常，未搜索到相应编码的设备；请仔细检查！'})
            return values
        mesline, workstation = equipment.mesline_id, equipment.workstation_id
        if not mesline:
            values.update({'success': False, 'message': u'设备还未绑定产线，请联系相关人员设置！'})
            return values
        if not mesline.location_production_id or (not mesline.location_material_list or len(mesline.location_material_list)<= 0):
            values.update({'success': False, 'message': u'产线%s还未设置成品原料库位，请联系相关人员设置！'})
            return values
        if not workstation:
            values.update({'success': False, 'message': u'设备还未绑定工位，请联系相关人员设置！'})
            return values
        if barcode.startswith('AT'):
            return self.action_feeding_withcontainer(mesline, workstation, barcode)
        else:
            return self.action_feeding_withlabel(mesline, workstation, barcode)


    @api.model
    def action_feeding_withcontainer(self, mesline, workstation, barcode):
        values = {'success': True, 'message': ''}
        container = self.env['aas.container'].search([('barcode', '=', barcode)], limit=1)
        if not container:
            values.update({'success': False, 'message': u'未搜索到容器，请仔细检查是否是有效的容器条码！'})
            return values
        if container.isempty:
            values.update({'success': False, 'message': u'容器%s里面空空如也，不可以用空容器投料！'% container.name})
            return values
        if not mesline.location_production_id or (not mesline.location_material_list or len(mesline.location_material_list) <= 0):
            values.update({'success': False, 'message': u'产线%s还未设置原料和成品库位！'% mesline.name})
            return values
        locationids = [mlocation.location_id.id for mlocation in mesline.location_material_list]
        locationids.append(mesline.location_production_id.id)
        locationlist = self.env['stock.location'].search([('id', 'child_of', locationids)])
        if container.location_id.id not in locationlist.ids:
            # 容器不在当前产线自动调拨
            materiallocation = mesline.location_material_list[0].location_id
            container.write({'location_id': materiallocation.id})
        for pline in container.product_lines:
            product_id, product_lot = pline.product_id.id, pline.product_lot.id
            feeddomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
            feeddomain.extend([('material_id', '=', product_id), ('material_lot', '=', product_lot)])
            feedmaterial = self.env['aas.mes.feedmaterial'].search(feeddomain, limit=1)
            if not feedmaterial:
                self.env['aas.mes.feedmaterial'].create({
                    'mesline_id': mesline.id, 'workstation_id': workstation.id,
                    'material_id': product_id, 'material_lot': product_lot
                })
            else:
                feedmaterial.action_refresh_stock()
        return values



    @api.model
    def action_feeding_withlabel(self, mesline, workstation, barcode):
        values = {'success': True, 'message': ''}
        label = self.env['aas.product.label'].search([('barcode', '=', barcode)], limit=1)
        if not label:
            values.update({'success': False, 'message': u'未搜索到标签，请仔细检查是否是有效的标签条码！'})
            return values
        if label.state != 'normal':
            values.update({'success': False, 'message': u'标签状态异常，可能标签已冻结，或是无效标签；请仔细检查！'})
            return values
        if label.locked:
            values.update({'success': False, 'message': u'标签已被单据%s锁定，暂时不可以投料！'% label.locked_order})
            return values
        locationids = [mlocation.location_id.id for mlocation in mesline.location_material_list]
        locationids.append(mesline.location_production_id.id)
        locationlist = self.env['stock.location'].search([('id', 'child_of', locationids)])
        if label.location_id.id not in locationlist.ids:
            values.update({'success': False, 'message': u'标签%s不在产线%s的线边库下，不可以投料！'% (label.name, mesline.name)})
            return values
        feeddomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        feeddomain.extend([('material_id', '=', label.product_id.id), ('material_lot', '=', label.product_lot.id)])
        feedmaterial = self.env['aas.mes.feedmaterial'].search(feeddomain, limit=1)
        if not feedmaterial:
            self.env['aas.mes.feedmaterial'].create({
                'mesline_id': mesline.id, 'workstation_id': workstation.id,
                'material_id': label.product_id.id, 'material_lot': label.product_lot.id
            })
        else:
            feedmaterial.action_refresh_stock()
        return values


    @api.multi
    def action_freshandclear(self):
        """刷新上料库存信息；若是库存小于等于零，则清理掉
        :return:
        """
        todellist = self.env['aas.mes.feedmaterial']
        for record in self:
            record.action_refresh_stock()
            if float_compare(record.material_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                todellist |= record
        if todellist and len(todellist) > 0:
            todellist.unlink()

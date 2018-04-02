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
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料', ondelete='restrict')
    material_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    material_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    material_qty = fields.Float(string=u'现场库存', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    feed_time = fields.Datetime(string=u'上料时间', default=fields.Datetime.now, copy=False)
    feeder_id = fields.Many2one(comodel_name='res.users', string=u'上料员', default= lambda self:self.env.user)


    _sql_constraints = [
        ('uniq_materiallot', 'unique (mesline_id, material_id, material_lot)', u'请不要在产线上重复添加同一批次的物料！')
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
    def get_workstation_materiallist(self, equipment_code, workorder_id=False):
        """根据设备获取相应产线工位的上料清单
        :param equipment_code:
        :param workorder_id:
        :return:
        """
        values = {'success': True, 'message': '', 'materiallist': []}
        if not workorder_id:
            return values
        equipment = self.env['aas.equipment.equipment'].search([('code', '=', equipment_code)], limit=1)
        if not equipment:
            values.update({'success': False, 'message': u'请仔细检查设备编码是否正确，系统中未搜索到此设备！'})
            return values
        mesline, workstation = equipment.mesline_id, equipment.workstation_id
        if not mesline or not workstation:
            values.update({'success': False, 'message': u'设备当前还未绑定产线和工位，请联系相关人员设置产线和工位！'})
            return values
        workorder = self.env['aas.mes.workorder'].browse(workorder_id)
        if not workorder:
            values.update({'success': False, 'message': u'当前工单是否为有效工单！'})
            return values
        bom, routing = workorder.aas_bom_id, workorder.routing_id
        if not bom or not routing:
            return values
        routingdomain = [('routing_id', '=', routing.id), ('workstation_id', '=', workstation.id)]
        routinglines = self.env['aas.mes.routing.line'].search(routingdomain)
        if not routinglines or len(routinglines) <= 0:
            return values
        consumedomain = [('workorder_id', '=', workorder.id), ('workcenter_id', 'in', routinglines.ids)]
        consumelist = self.env['aas.mes.workorder.consume'].search(consumedomain)
        if not consumelist or len(consumelist) <= 0:
            return values
        materialids = [tconsume.material_id.id for tconsume in consumelist]
        feeddomain = [('mesline_id', '=', equipment.mesline_id.id), ('material_id', 'in', materialids)]
        feedmateriallist = self.env['aas.mes.feedmaterial'].search(feeddomain)
        if feedmateriallist and len(feedmateriallist) > 0:
            todelfeedinglist = self.env['aas.mes.feedmaterial']
            materialids, materiallotids, materialdict = [], [], {}
            for feedmaterial in feedmateriallist:
                materialid, materiallotid = feedmaterial.material_id.id, feedmaterial.material_lot.id
                mkey = 'M'+str(materialid)
                if materialid not in materialids:
                    materialdict[mkey] = {
                        'materiallot_id': 0,
                        'material_id': feedmaterial.material_id.id,
                        'material_qty': feedmaterial.material_qty,
                        'materiallot_name': feedmaterial.material_lot.name,
                        'material_code': feedmaterial.material_id.default_code
                    }
                    materialids.append(materialid)
                    materiallotids.append(materiallotid)
                elif materiallotid not in materiallotids:
                    templotcode = ','+feedmaterial.material_lot.name
                    materialdict[mkey]['materiallot_name'] += templotcode
                    materialdict[mkey]['material_qty'] += feedmaterial.material_qty
                    materiallotids.append(materiallotid)
                else:
                    todelfeedinglist |= feedmaterial
            values['materiallist'] = materialdict.values()
            if todelfeedinglist and len(todelfeedinglist) > 0:
                todelfeedinglist.unlink()
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
            return self.action_feeding_withcontainer(mesline, barcode)
        else:
            return self.action_feeding_withlabel(mesline, barcode)


    @api.model
    def action_feeding_withcontainer(self, mesline, barcode):
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
        materiallocation = mesline.location_material_list[0].location_id
        locationids = [mlocation.location_id.id for mlocation in mesline.location_material_list]
        locationids.append(mesline.location_production_id.id)
        locationlist = self.env['stock.location'].search([('id', 'child_of', locationids)])
        if container.location_id.id not in locationlist.ids:
            # 容器不在当前产线自动调拨
            container.write({'location_id': materiallocation.id})
        productdict, movelist = {}, self.env['stock.move']
        for pline in container.product_lines:
            pkey = 'P-'+str(pline.product_id.id)+'-'+str(pline.product_lot.id)
            if pkey in productdict:
                productdict[pkey]['material_qty'] += pline.stock_qty
            else:
                productdict[pkey] = {
                    'material_id': pline.product_id.id, 'material_lot': pline.product_lot.id,
                    'material_uom': pline.product_id.uom_id.id, 'material_qty': pline.stock_qty
                }
        for mline in productdict.values():
            temp_qty = mline['material_qty']
            material_id, material_lot = mline['material_id'], mline['material_lot']
            feeddomain = [('mesline_id', '=', mesline.id)]
            feeddomain += [('material_id', '=', material_id), ('material_lot', '=', material_lot)]
            feedinglist = self.env['aas.mes.feedmaterial'].search(feeddomain)
            if feedinglist and len(feedinglist) > 0:
                feedinglist.unlink()
            feeding = self.env['aas.mes.feedmaterial'].create({
                'mesline_id': mesline.id,
                'material_id': material_id, 'material_lot': material_lot, 'material_qty': temp_qty
            })
            # 将库存自动移动到线边库上
            movelist |= self.env['stock.move'].create({
                'name': container.name, 'product_id': mline['material_id'], 'product_uom': mline['material_uom'],
                'create_date': fields.Datetime.now(), 'company_id': self.env.user.company_id.id,
                'restrict_lot_id': mline['material_lot'], 'location_id': container.stock_location_id.id,
                'location_dest_id': materiallocation.id, 'product_uom_qty': temp_qty
            })
            self.env['aas.mes.feedmaterial.list'].create({
                'mesline_id': mesline.id,
                'feedmaterial_id': feeding.id, 'material_id': material_id,
                'material_lot': material_lot, 'material_qty': temp_qty,
                'toatal_qty': feeding.material_qty, 'feeder_id': self.env.user.id, 'container_id': container.id
            })
        movelist.action_done()
        if container.product_lines and len(container.product_lines) > 0:
            # 库存移动之后清理容器内容
            container.product_lines.unlink()
        return values



    @api.model
    def action_feeding_withlabel(self, mesline, barcode):
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
        feeddomain = [('mesline_id', '=', mesline.id)]
        feeddomain += [('material_id', '=', label.product_id.id), ('material_lot', '=', label.product_lot.id)]
        feedmaterialist = self.env['aas.mes.feedmaterial'].search(feeddomain)
        if feedmaterialist and len(feedmaterialist) > 0:
            feedmaterialist.unlink()
        feeding = self.env['aas.mes.feedmaterial'].create({
            'mesline_id': mesline.id,
            'material_id': label.product_id.id, 'material_uom': label.product_id.uom_id.id,
            'material_lot': label.product_lot.id, 'material_qty': label.product_qty
        })
        self.env['aas.mes.feedmaterial.list'].create({
            'mesline_id': mesline.id,
            'feedmaterial_id': feeding.id, 'material_id': label.product_id.id,
            'material_lot': label.product_lot.id, 'material_qty': label.product_qty,
            'toatal_qty': feeding.material_qty, 'feeder_id': self.env.user.id, 'label_id': label.id
        })
        return values


    @api.multi
    def action_freshandclear(self):
        """刷新上料库存信息；若是库存小于等于零，则清理掉
        :return:
        """
        feedinglist = []
        todellist = self.env['aas.mes.feedmaterial']
        for record in self:
            fkey = 'F-'+str(record.mesline_id.id)+'-'+str(record.material_id.id)+'-'+str(record.material_lot.id)
            if fkey in feedinglist:
                todellist |= record
                continue
            feedinglist.append(fkey)
            record.action_refresh_stock()
            if float_compare(record.material_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                todellist |= record
        if todellist and len(todellist) > 0:
            todellist.unlink()



class AASMESFeedmaterialList(models.Model):
    _name = 'aas.mes.feedmaterial.list'
    _description = 'AAS MES Feed Material'
    _rec_name = 'material_id'
    _order = 'feed_time asc'


    feedmaterial_id = fields.Many2one(comodel_name='aas.mes.feedmaterial', string=u'上料信息')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料', ondelete='restrict')
    material_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    material_qty = fields.Float(string=u'本次上料数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    toatal_qty = fields.Float(string=u'已上料总数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    feed_time = fields.Datetime(string=u'上料时间', default=fields.Datetime.now, copy=False)
    feeder_id = fields.Many2one(comodel_name='res.users', string=u'上料员')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签')
    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器')

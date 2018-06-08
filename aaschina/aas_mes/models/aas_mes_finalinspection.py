# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-6-7 11:46
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

# 扭矩焊终检挑选不良
class AASMESFinalinspection(models.Model):
    _name = 'aas.mes.finalinspection'
    _description = 'AAS MES Finalinspection'
    _rec_name = 'product_id'
    _order = 'id desc'

    product_id = fields.Many2one(comodel_name='product.product', string=u'产品')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签')
    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器')
    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线')
    schedule_date = fields.Date(string=u'日期')
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次')
    operator_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'操作员工')
    operation_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    output_qty = fields.Float(string=u'报工数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    badmode_qty = fields.Float(string=u'不良数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    badmode_lines = fields.One2many('aas.production.badmode', inverse_name='finalinspection_id', string=u'不良清单')

    @api.model
    def action_scanning(self, barcode):
        values = {
            'success': True, 'message': '', 'workorder_id': '0', 'mesline_id': '0',
            'label_id': '0', 'label_name': '', 'container_id': '0', 'container_name': ''
        }
        prefix = barcode[0:2]
        if prefix == 'AT':
            container = self.env['aas.container'].search([('barcode', '=', barcode)], limit=1)
            if not container:
                values.update({'success': False, 'message': u'请仔细检查是否扫描了有效的容器条码！'})
                return values
            if container.isempty:
                values.update({'success': False, 'message': u'请仔细检查,当前容器里面什么也没有！'})
                return values
            pline = container.product_lines[0]
            production = self.env['aas.production.product'].search([('container_id', '=', container.id)], limit=1)
            values.update({
                'mesline_id': production.workorder_id.mesline_id.id,
                'product_qty': pline.stock_qty, 'container_id': container.id, 'container_name': container.name,
                'workorder_id': production.workorder_id.id, 'workorder_name': production.workorder_id.name
            })
        else:
            label = self.env['aas.product.label'].search([('name', '=', barcode)], limit=1)
            if not label:
                values.update({'success': False, 'message': u'请仔细检查是否扫描了有效的标签条码！'})
                return values
            if label.state == 'over':
                values.update({'success': False, 'message': u'标签可能已消耗！'})
                return values
            if not label.isproduction:
                values.update({'success': False, 'message': u'标签已入库，不可以操作！'})
                return values
            production = self.env['aas.production.product'].search([('label_id', '=', label.id)], limit=1)
            values.update({
                'mesline_id': production.workorder_id.mesline_id.id,
                'product_qty': label.product_qty, 'label_id': label.id, 'label_name': label.name,
                'workorder_id': production.workorder_id.id, 'workorder_name': production.workorder_id.name
            })
        return values


    @api.model
    def action_finalinspect(self, workorderid, employeeid, labelid=0, containerid=0, badmodelines=[]):
        values = {'success': True, 'message': ''}
        if not labelid and not containerid:
            values.update({'success': False, 'message': u'请仔细检查可能未获取到标签或容器的信息！'})
            return values
        if not badmodelines or len(badmodelines) <= 0:
            values.update({'success': False, 'message': u'请仔细检查可能还未添加不良信息！'})
            return values
        workorder = self.env['aas.mes.workorder'].browse(workorderid)
        companyid, destlocation = self.env.user.company_id.id, self.env.ref('stock.location_production')
        product, adjustment, movevals, product_qty = workorder.product_id, False, {}, 0.0
        inspectionvals = {
            'workorder_id': workorderid, 'product_id': product.id,
            'schedule_id': workorder.plan_schedule.id, 'operator_id': employeeid,
            'mesline_id': workorder.mesline_id.id, 'schedule_date': workorder.plan_date
        }
        if containerid:
            container = self.env['aas.container'].browse(containerid)
            pline = container.product_lines[0]
            product_qty = pline.stock_qty
            adjustment = pline
            movevals = {
                'name': '容器%s终检'% container.name, 'product_id': product.id, 'product_uom': product.uom_id.id,
                'create_date': fields.Datetime.now(), 'company_id': companyid,
                'restrict_lot_id': pline.product_lot.id, 'location_id': container.stock_location_id.id,
                'location_dest_id': destlocation.id, 'company_id': companyid
            }
            inspectionvals.update({'container_id': containerid, 'output_qty': product_qty})
        else:
            label = self.env['aas.product.label'].browse(labelid)
            adjustment = label
            product_qty = label.product_qty
            movevals = {
                'name': '标签%s终检'% label.name, 'product_id': product.id, 'product_uom': product.uom_id.id,
                'create_date': fields.Datetime.now(), 'company_id': companyid,
                'restrict_lot_id': label.product_lot.id, 'location_id': label.location_id.id,
                'location_dest_id': destlocation.id, 'company_id': companyid
            }
            inspectionvals.update({'label_id': labelid, 'output_qty': product_qty})
        badmodelist, badmode_qty = [], 0.0
        meslineid, scheduleid = workorder.mesline_id.id, workorder.plan_schedule.id
        badmode_date = fields.Datetime.to_china_today()
        for badmode in badmodelines:
            badmode_qty += badmode['badmode_qty']
            badmodelist.append((0, 0, {
                'product_id': product.id,
                'workorder_id': workorderid, 'mesline_id': meslineid, 'schedule_id': scheduleid,
                'badmode_id': badmode['badmode_id'], 'badmode_qty': badmode['badmode_qty'],
                'badmode_date': badmode_date, 'badmode_note': u'最终检查上报不良'
            }))
        if float_compare(badmode_qty, product_qty, precision_rounding=0.000001) > 0.0:
            values.update({'success': False, 'message': u'不良数量不能大于检测数量！'})
            return values
        product_qty -= badmode_qty
        movevals['product_uom_qty'] = badmode_qty
        inspectionvals['badmode_qty'] = badmode_qty
        inspectionvals['badmode_lines'] = badmodelist
        self.create(inspectionvals)
        if containerid:
            adjustment.update({'stock_qty': product_qty})
        else:
            adjustment.update({'product_qty': product_qty})
        workorder.write({'output_qty': workorder.output_qty - badmode_qty})
        self.env['stock.move'].create(movevals).action_done()
        return values





class AASProductionBadmode(models.Model):
    _inherit = 'aas.production.badmode'

    finalinspection_id = fields.Many2one(comodel_name='aas.mes.finalinspection', string=u'终检单')
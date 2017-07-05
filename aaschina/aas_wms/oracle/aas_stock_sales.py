# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-5 22:59
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

class AASEBSDelivery(models.Model):
    _auto = False
    _log_access = False
    _name = 'aas.ebs.delivery'
    _description = 'AAS EBS Delivery'
    _order = 'id desc'

    name = fields.Char(string=u'发票单号')
    shipment_date = fields.Datetime(string=u'交付日期')
    partner_id = fields.Integer(string=u'客户')
    confirmed_by = fields.Integer(string='Confirmed By')
    confirm_date = fields.Datetime(string='Confirm Date')
    creation_date = fields.Datetime(string='Creation Date')
    created_by = fields.Integer(string='Created By')
    last_update_date = fields.Datetime(string='Last Update Date')
    last_updated_by = fields.Integer(string='Last Updated By')



class AASEBSDeliveryLine(models.Model):
    _auto = False
    _log_access = False
    _name = 'aas.ebs.delivery.line'
    _description = 'AAS EBS Delivery Line'
    _order = 'id desc'

    delivery_id = fields.Integer(string=u'销售发票')
    so_no = fields.Char(string=u'销售订单')
    line_no = fields.Char(string=u'销售明细')
    client_order_ref = fields.Char(string=u'客户订单')
    partner_id = fields.Integer(string=u'客户')
    product_id = fields.Integer(string=u'产品ID')
    product_name = fields.Char(string=u'产品名称')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    product_uom = fields.Char(string=u'单位')
    lot_number = fields.Char(string=u'批次')
    released_status = fields.Char(string=u'状态')
    unit_price = fields.Float(string=u'单价', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    currency_code = fields.Char(string=u'货币')
    creation_date = fields.Datetime(string='Creation Date')
    created_by = fields.Integer(string='Created By')
    last_update_date = fields.Datetime(string='Last Update Date')
    last_update_by = fields.Integer(string='Last Updated By')



class AASStockSaleDelivery(models.Model):
    _name = 'aas.stock.sale.delivery'
    _description = 'AAS Stock Sale Delivery'
    _order = 'id desc'

    name = fields.Char(string=u'发票单号')
    shipment_date = fields.Datetime(string=u'交付日期')
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'客户')
    confirmed_by = fields.Integer(string='Confirmed By')
    confirm_date = fields.Datetime(string='Confirm Date')
    creation_date = fields.Datetime(string='Creation Date')
    created_by = fields.Integer(string='Created By')
    last_update_date = fields.Datetime(string='Last Update Date')
    last_updated_by = fields.Integer(string='Last Updated By')
    aas_delivery_id = fields.Many2one(comodel_name='aas.stock.delivery', string=u'销售发货')
    delivery_lines = fields.One2many(comodel_name='aas.stock.sale.delivery.line', inverse_name='delivery_id', string=u'发票明细')
    ebsdelivery = fields.Boolean(string=u'Oracle发票', default=False, copy=False)

    @api.model
    def action_import_order(self, order_number):
        """
        导入销售发票
        :param order_number:
        :return:
        """
        values = {'success': True, 'message': ''}
        tdelivery = self.env['aas.stock.sale.delivery'].search([('name', '=', order_number)], limit=1)
        if tdelivery:
            values.update({'success': False, 'message': u'销售发票已存在，请不要重复导入！'})
            return values
        ebsdelivery = self.env['aas.ebs.delivery'].search([('name', '=', order_number)], limit=1)
        if not ebsdelivery:
            values.update({'success': False, 'message': u'未搜索到相应发票，请仔细确认！'})
            return values
        deliverylist = self.env['aas.ebs.delivery.line'].search([('delivery_id', '=', ebsdelivery.id)])
        if not deliverylist or len(deliverylist) <= 0:
            values.update({'success': False, 'message': u'未搜索到相应发票明细，请仔细确认！'})
            return values
        delivery_lines = [(0, 0, {
            'so_no': dlist.so_no, 'line_no': dlist.line_no, 'client_order_ref': dlist.client_order_ref,
            'partner_id': dlist.partner_id, 'product_id': dlist.product_id, 'product_qty': dlist.product_qty,
            'product_uom': dlist.product_uom, 'lot_number': dlist.lot_number, 'released_status': dlist.released_status,
            'unit_price': dlist.unit_price, 'currency_code': dlist.currency_code, 'creation_date': dlist.creation_date,
            'created_by': dlist.created_by, 'last_update_date': dlist.last_update_date, 'last_update_by': dlist.last_update_by
        }) for dlist in deliverylist]
        self.env['aas.stock.sale.delivery'].create({
            'name': ebsdelivery.name, 'shipment_date': ebsdelivery.shipment_date, 'partner_id': ebsdelivery.partner_id,
            'confirmed_by': ebsdelivery.confirmed_by, 'confirm_date': ebsdelivery.confirm_date, 'creation_date': ebsdelivery.creation_date,
            'created_by': ebsdelivery.created_by, 'last_update_date': ebsdelivery.last_update_date, 'last_updated_by': ebsdelivery.last_updated_by,
            'delivery_lines': delivery_lines, 'ebsdelivery': True
        })
        return values



    @api.multi
    def action_delivery(self):
        """
        销售发票生成销售发货单
        :return:
        """
        self.ensure_one()
        location = self.env.ref('stock.stock_location_customers')
        deliveryvals = {
            'delivery_type': 'sales', 'partner_id': self.partner_id.id, 'origin_order': self.name, 'location_id': location.id
        }
        if not self.delivery_lines or len(self.delivery_lines) <= 0:
            raise UserError(u'请检查销售发票是否有发票明细！')
        deliverydict = {}
        for dline in self.delivery_lines:
            pkey = 'P'+str(dline.product_id.id)
            if pkey in deliverydict:
                deliverydict[pkey]['product_qty'] += dline.product_qty
            else:
                deliverydict[pkey] = {
                    'product_id': dline.product_id.id, 'product_uom': dline.product_id.uom_id.id, 'product_qty': dline.product_qty,
                    'delivery_type': 'sales'
                }
        deliveryvals['delivery_lines'] = [(0, 0, dval) for dkey, dval in deliverydict.items()]
        delivery = self.env['aas.stock.delivery'].create(deliveryvals)
        delivery.action_confirm()
        self.write({'aas_delivery_id': delivery.id})
        view_form = self.env.ref('aas_wms.view_form_aas_stock_delivery_inside')
        return {
            'name': u'销售发货',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.stock.delivery',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'self',
            'res_id': delivery.id,
            'context': self.env.context
        }





class AASStockSaleDeliveryLine(models.Model):
    _name = 'aas.stock.sale.delivery.line'
    _description = 'AAS Stock Sale Delivery Line'

    delivery_id = fields.Many2one(comodel_name='aas.stock.sale.delivery', string=u'销售发票')
    so_no = fields.Char(string=u'销售订单')
    line_no = fields.Char(string=u'销售明细')
    client_order_ref = fields.Char(string=u'客户订单')
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'客户')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    product_uom = fields.Char(string=u'单位')
    lot_number = fields.Char(string=u'批次')
    released_status = fields.Char(string=u'状态')
    unit_price = fields.Float(string=u'单价', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    currency_code = fields.Char(string=u'货币')
    creation_date = fields.Datetime(string='Creation Date')
    created_by = fields.Integer(string='Created By')
    last_update_date = fields.Datetime(string='Last Update Date')
    last_update_by = fields.Integer(string='Last Updated By')
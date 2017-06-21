# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError


import logging
from datetime import date
_logger = logging.getLogger(__name__)


class AASReceiveDeliver(models.Model):
    _name = 'aas.receive.deliver'
    _description = u'收发汇总'

    name = fields.Char(string=u'名称')
    action_year = fields.Integer(string=u"年份")
    action_month = fields.Integer(string=u"月份")
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    begin_qty = fields.Float(string=u'期初数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    receive_qty = fields.Float(string=u'接收数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    deliver_qty = fields.Float(string=u'发出数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    final_qty = fields.Float(string=u'期末数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('aas.receive.deliver')
        return super(AASReceiveDeliver, self).create(vals)

    @api.model
    def action_receive(self, product_id, location_id, product_lot, receive_qty, action_year=None, action_month=None):
        if not action_year or not action_month:
            today = date.today()
            action_year, action_month = today.year, today.month
        action_domain = [('product_id', '=', product_id), ('location_id', '=', location_id), ('product_lot', '=', product_lot)]
        month_domain = [('action_year', '=', action_year), ('action_month', '=', action_month)]
        receipt = self.env['aas.receive.deliver'].search(action_domain+month_domain, limit=1)
        if receipt:
            receipt.write({'receive_qty': receipt.receive_qty+receive_qty, 'final_qty': receipt.final_qty+receive_qty})
        else:
            begin_qty = 0.0
            last_year, last_month = action_year, action_month
            if action_month == 1:
                last_year, last_month = action_year-1, 12
            last_month_domain = [('action_year', '=', last_year), ('action_month', '=', last_month)]
            last_receipt = self.env['aas.receive.deliver'].search(action_domain+last_month_domain, limit=1)
            if last_receipt:
                begin_qty = last_receipt.final_qty
            self.env['aas.receive.deliver'].create({
                'product_id': product_id, 'location_id': location_id, 'product_lot': product_lot, 'begin_qty': begin_qty,
                'receive_qty': receive_qty, 'final_qty': begin_qty+receive_qty, 'action_year': action_year, 'action_month': action_month
            })


    @api.model
    def action_deliver(self, product_id, location_id, product_lot, deliver_qty, action_year=None, action_month=None):
        if not action_year or not action_month:
            today = date.today()
            action_year, action_month = today.year, today.month
        action_domain = [('product_id', '=', product_id), ('location_id', '=', location_id), ('product_lot', '=', product_lot)]
        month_domain = [('action_year', '=', action_year), ('action_month', '=', action_month)]
        receipt = self.env['aas.receive.deliver'].search(action_domain+month_domain, limit=1)
        if receipt:
            final_qty = receipt.final_qty-deliver_qty
            if float_compare(final_qty, 0.0, precision_rounding=0.000001) < 0.0:
                final_qty = 0.0
            receipt.write({'deliver_qty': receipt.deliver_qty+deliver_qty, 'final_qty': final_qty})
        else:
            begin_qty, final_qty = 0.0, 0.0
            last_year, last_month = action_year, action_month
            if action_month == 1:
                last_year, last_month = action_year-1, 12
            last_month_domain = [('action_year', '=', last_year), ('action_month', '=', last_month)]
            last_receipt = self.env['aas.receive.deliver'].search(action_domain+last_month_domain, limit=1)
            if last_receipt:
                begin_qty, final_qty = last_receipt.final_qty, last_receipt.final_qty
                if float_compare(final_qty - deliver_qty, 0.0, precision_rounding=0.000001) < 0.0:
                    final_qty = 0.0
            self.env['aas.receive.deliver'].create({
                'product_id': product_id, 'location_id': location_id, 'product_lot': product_lot, 'begin_qty': begin_qty,
                'deliver_qty': deliver_qty, 'final_qty': final_qty, 'action_year': action_year, 'action_month': action_month
            })

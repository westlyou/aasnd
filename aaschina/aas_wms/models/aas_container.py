# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-11-5 15:09
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

class AASContainer(models.Model):
    _name = 'aas.container'
    _description = 'AAS Container'
    _inherits = {'stock.location': 'stock_location_id'}

    barcode = fields.Char(string=u'条码', copy=False, index=True)
    stock_location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', required=True, ondelete='cascade', auto_join=True, index=True)
    location_id = fields.Many2one(comodel_name='stock.location', string=u'上级库位', default= lambda self: self.env.ref('aas_wms.stock_location_container'))

    product_lines = fields.One2many(comodel_name='aas.container.product', inverse_name='container_id', string=u'产品清单')

    @api.model
    def create(self, vals):
        if vals.get('name', False):
            vals['barcode'] = 'AT'+vals['name']
        record = super(AASContainer, self).create(vals)
        locationvals = {'container_id': record.id}
        if vals.get('location_id', False):
            locationvals['location_id'] = vals.get('location_id')
        record.stock_location_id.write(locationvals)
        return record

    @api.multi
    def write(self, vals):
        if vals.get('name', False):
            vals['barcode'] = 'AT'+vals['name']
        locationlist = self.env['stock.location']
        if vals.get('location_id', False):
            for record in self:
                locationlist |= record.stock_location_id
        result = super(AASContainer, self).write(vals)
        if locationlist and len(locationlist) > 0:
            locationlist.write({'location_id': vals.get('location_id')})
        return result

    @api.multi
    def action_move(self):
        """
        容器调拨
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.container.move.wizard'].create({'container_id': self.id, 'location_src_id': self.location_id.id})
        view_form = self.env.ref('aas_wms.view_form_aas_container_move_wizard')
        return {
            'name': u"容器调拨",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.container.move.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }


    @api.multi
    def action_show_moves(self):
        """
        显示容器调拨记录
        :return:
        """
        self.ensure_one()
        action = self.env.ref('aas_wms.action_aas_container_move')
        return {
            'name': action.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': action.res_model,
            'domain': [('container_id', '=', self.id)],
            'search_view_id': action.search_view_id.id,
            'context': self.env.context,
            'target': 'self'
        }


# 容器调拨记录
class AASContainerMove(models.Model):
    _name = 'aas.container.move'
    _description = 'AAS Container Move'
    _rec_name = 'container_id'

    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='restrict')
    location_src_id = fields.Many2one(comodel_name='stock.location', string=u'来源库位', ondelete='restrict')
    location_dest_id = fields.Many2one(comodel_name='stock.location', string=u'目标库位', ondelete='restrict')
    move_time = fields.Datetime(string=u'调拨时间', default=fields.Datetime.now, copy=False)
    mover_id = fields.Many2one(comodel_name='res.users', string=u'调拨员', ondelete='restrict', default=lambda self:self.env.user)
    move_note = fields.Text(string=u'调拨备注')


# 容器中产品清单
class AASContainerProduct(models.Model):
    _name = 'aas.container.product'
    _description = 'AAS Container Product'

    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    stock_qty = fields.Float(string=u'库存数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    temp_qty = fields.Float(string=u'未入库数', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_product_qty', store=True)

    @api.depends('stock_qty', 'temp_qty')
    def _compute_product_qty(self):
        for record in self:
            record.product_qty = record.stock_qty + record.temp_qty

    @api.one
    def action_stock(self, qty):
        srclocationid = self.env.ref('stock.location_production').id
        destlocationid = self.container_id.stock_location_id.id
        if float_compare(qty, self.temp_qty, precision_rounding=0.000001) > 0.0:
            qty = self.temp_qty
        self.env['stock.move'].create({
            'name': self.container_id.name, 'product_id': self.product_id.id, 'product_uom': self.product_id.uom_id.id,
            'create_date': fields.Datetime.now(), 'product_uom_qty': qty, 'location_id': srclocationid, 'location_dest_id': destlocationid,
            'company_id': self.env.user.company_id.id, 'restrict_lot_id': False if not self.product_lot else self.product_lot.id
        }).action_done()
        self.write({'stock_qty': self.stock_qty + qty, 'temp_qty': self.temp_qty - qty})
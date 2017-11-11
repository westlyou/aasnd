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
    alias = fields.Char(string=u'说明', copy=False)
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
    def action_adjust(self):
        """
        容器调整
        :return:
        """
        self.ensure_one()
        adjustvals = {'container_id': self.id}
        if self.product_lines and len(self.product_lines) > 0:
            adjustvals['adjust_lines'] = [(0, 0, {
                'line_id': pline.id, 'product_id': pline.product_id.id, 'product_lot': pline.product_lot.id,
                'temp_qty': pline.temp_qty, 'stock_qty': pline.stock_qty,
                'label_id': False if not pline.label_id else pline.label_id.id
            }) for pline in self.product_lines]
        wizard = self.env['aas.container.adjust.wizard'].create(adjustvals)
        view_form = self.env.ref('aas_wms.view_form_aas_container_adjust_wizard')
        return {
            'name': u"容器库存调整",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.container.adjust.wizard',
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

    @api.model
    def action_batchadd(self, rulecode, addcount, addnote):
        values = {'success': True, 'message': ''}
        location_id = self.env.ref('aas_wms.stock_location_container').id
        maxone = self.env['aas.container'].search([('name', 'like', rulecode+'%')], order='name desc', limit=1)
        if maxone:
            startindex = int(maxone.name[len(rulecode):]) + 1
        else:
            startindex = 1
        startindex += 1000000
        for index in range(0, addcount):
            tempname = str(startindex+index)[1:]
            self.env['aas.container'].create({
                'name': rulecode+tempname, 'location_id': location_id, 'alias': addnote, 'usage': 'container'
            })
        return values


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




# 容器调拨向导
class AASContainerMoveWizard(models.TransientModel):
    _name = 'aas.container.move.wizard'
    _description = 'AAS Container Move Wizard'

    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='restrict')
    location_src_id = fields.Many2one(comodel_name='stock.location', string=u'来源库位', ondelete='restrict')
    location_dest_id = fields.Many2one(comodel_name='stock.location', string=u'目标库位', ondelete='restrict')
    move_note = fields.Text(string=u'备注')

    @api.one
    def action_done(self):
        tempcount = self.env['aas.container.product'].search_count([('container_id', '=', self.container_id.id), ('product_label', '=', False)])
        if not self.location_dest_id.edgelocation and tempcount > 0:
            raise UserError(u'容器中还有未打包成标签的产品不可以直接调拨到仓库库存库位！')
        self.env['aas.container.move'].create({
            'container_id': self.container_id.id, 'location_src_id': self.location_src_id.id,
            'location_dest_id': self.location_dest_id.id, 'move_note': False if not self.move_note else self.move_note
        })
        self.container_id.write({'location_id': self.location_dest_id.id})


# 容器库存调整向导
class AASContainerAdjustWizard(models.TransientModel):
    _name = 'aas.container.adjust.wizard'
    _description = 'AAS Container Adjust Wizard'

    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='restrict')
    adjust_note = fields.Text(string=u'备注')
    adjust_lines = fields.One2many(comodel_name='aas.container.adjust.line.wizard', inverse_name='wizard_id', string=u'调整明细')

    @api.one
    def action_done(self):
        lineids, productlines = [], []
        if self.adjust_lines and len(self.adjust_lines) > 0:
            for tadjust in self.adjust_lines:
                if tadjust.line_id:
                    lineids.append(tadjust.line_id.id)
                    tval = {}
                    if float_compare(tadjust.stock_qty, tadjust.line_id.stock_qty, precision_rounding=0.000001) != 0.0:
                        tval['stock_qty'] = tadjust.stock_qty
                    if float_compare(tadjust.temp_qty, tadjust.line_id.temp_qty, precision_rounding=0.000001) != 0.0:
                        tval['temp_qty'] = tadjust.temp_qty
                    if tval and len(tval) > 0:
                       productlines.append((1, tadjust.line_id.id, tval))
                else:
                    tlabel = tadjust.label_id
                    if tlabel:
                        tval = {
                            'label_id': tlabel.id, 'product_id': tlabel.product_id.id,
                            'product_lot': tlabel.product_lot.id, 'stock_qty': tlabel.product_qty
                        }
                    else:
                        tval = {
                            'product_id': tadjust.product_id.id, 'product_lot': tadjust.product_lot.id,
                            'stock_qty': tadjust.stock_qty, 'temp_qty': tadjust.temp_qty
                        }
                    productlines.append((0, 0, tval))
        if self.container_id.product_lines and len(self.container_id.product_lines) > 0:
            for pline in self.container_id.product_lines:
                if pline.id not in lineids:
                    productlines.append((2, pline.id, False))
        if productlines and len(productlines) > 0:
            self.container_id.write({'product_lines': productlines})





class AASContainerAdjustLineWizard(models.TransientModel):
    _name = 'aas.container.adjust.line.wizard'
    _description = 'AAS Container Adjust Line Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.container.adjust.wizard', string=u'调整单', ondelete='restrict')
    line_id = fields.Many2one(comodel_name='aas.container.product', string=u'容器库存', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    stock_qty = fields.Float(string=u'库存数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    temp_qty = fields.Float(string=u'未入库数', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    @api.onchange('label_id')
    def change_label(self):
        if not self.label_id:
            self.product_id, self.product_lot, self.stock_qty, self.temp_qty = False, False, 0.0, 0.0
        else:
            self.product_id, self.product_lot = self.label_id.product_id.id, self.label_id.product_lot.id
            self.stock_qty, self.temp_qty = self.label_id.product_qty, 0.0



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

    isempty = fields.Boolean(string=u'是否为空', compute='_compute_isempty', store=True)
    product_lines = fields.One2many(comodel_name='aas.container.product', inverse_name='container_id', string=u'产品清单')

    @api.depends('product_lines')
    def _compute_isempty(self):
        for record in self:
            if record.product_lines and len(record.product_lines) > 0:
                record.isempty = False
            else:
                record.isempty = True


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
                'line_id': pline.id, 'product_id': pline.product_id.id,
                'product_lot': pline.product_lot.id, 'temp_qty': pline.temp_qty, 'stock_qty': pline.stock_qty
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

    @api.model
    def action_scanning(self, barcode):
        """
        客户端扫描容器
        :param barcode:
        :return:
        """
        values = {'success': True, 'message': ''}
        container = self.env['aas.container'].search([('barcode', '=', barcode)], limit=1)
        if not container:
            values.update({'success': False, 'message': u'未搜索到容器，请仔细检查条码是否正确！'})
            return values
        values.update({
            'container_id': container.id, 'container_name': container.name, 'container_alias': container.alias
        })
        return values

    @api.one
    def action_consume(self, product_id, product_lot, product_qty):
        """
        容器库存消耗
        :param product_id:
        :param product_lot:
        :param product_qty:
        :return:
        """
        pdomain = [('container_id', '=', self.id), ('product_id', '=', product_id), ('product_lot', '=', product_lot)]
        productlines = self.env['aas.container.product'].search(pdomain)
        if productlines and len(productlines) > 0:
            stocklist = []
            for pline in productlines:
                if float_compare(product_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                    break
                if float_compare(product_qty, pline.stock_qty, precision_rounding=0.000001) >= 0.0:
                    stocklist.append((2, pline.id, False))
                    product_qty -= pline.stock_qty
                else:
                    stocklist.append((1, pline.id, {'stock_qty': pline.stock_qty - product_qty}))
                    product_qty = 0.0
            self.write({'product_lines': stocklist})


    @api.one
    def action_domove(self, destlocationid, movenote=False):
        """
        容器调拨
        :param destlocationid:
        :param movenote:
        :return:
        """
        self.env['aas.container.move'].create({
            'container_id': self.id, 'move_note': movenote,
            'location_src_id': self.location_id.id, 'location_dest_id': destlocationid
        })
        self.write({'location_id': destlocationid})


    @api.model
    def action_print_label(self, printer_id, ids=[], domain=[]):
        values = {'success': True, 'message': ''}
        printer = self.env['aas.label.printer'].browse(printer_id)
        if not printer.field_lines or len(printer.field_lines) <= 0:
            values.update({'success': False, 'message': u'请联系管理员标签打印未指定具体打印内容！'})
            return values
        values.update({'printer': printer.name, 'serverurl': printer.serverurl})
        field_list = [fline.field_name for fline in printer.field_lines]
        if ids and len(ids) > 0:
            tempdomain = [('id', 'in', ids)]
        else:
            tempdomain = domain
        if not tempdomain or len(tempdomain) <= 0:
            values.update({'success': False, 'message': u'您可能选中了所有记录或未选中任何记录，请先设置好需要打印的记录！'})
            return values
        records = self.search_read(domain=tempdomain, fields=field_list)
        if not records or len(records) <= 0:
            values.update({'success': False, 'message': u'未搜索到需要打印的容器！'})
            return values
        records = printer.action_correct_records(records)
        values['records'] = records
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


    @api.multi
    def write(self, vals):
        result = super(AASContainerProduct, self).write(vals)
        productlist = self.env['aas.container.product']
        for record in self:
            if float_compare(record.product_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                productlist |= record
        if productlist and len(productlist) > 0:
            productlist.sudo().unlink()
        return result




# 容器调拨向导
class AASContainerMoveWizard(models.TransientModel):
    _name = 'aas.container.move.wizard'
    _description = 'AAS Container Move Wizard'

    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='cascade')
    location_src_id = fields.Many2one(comodel_name='stock.location', string=u'来源库位', ondelete='cascade')
    location_dest_id = fields.Many2one(comodel_name='stock.location', string=u'目标库位', ondelete='cascade')
    move_note = fields.Text(string=u'备注')

    @api.one
    def action_done(self):
        self.container_id.action_domove(self.location_dest_id.id, self.move_note)


# 容器库存调整向导
class AASContainerAdjustWizard(models.TransientModel):
    _name = 'aas.container.adjust.wizard'
    _description = 'AAS Container Adjust Wizard'

    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='cascade')
    adjust_note = fields.Text(string=u'备注')
    adjust_lines = fields.One2many(comodel_name='aas.container.adjust.line.wizard', inverse_name='wizard_id', string=u'调整明细')

    @api.one
    def action_done(self):
        lineids, productlines, movevallist = [], [], []
        productionlocation = self.env.ref('stock.location_production').id
        containerlocation = self.container_id.stock_location_id.id
        if self.adjust_lines and len(self.adjust_lines) > 0:
            for tadjust in self.adjust_lines:
                if tadjust.line_id:
                    lineids.append(tadjust.line_id.id)
                    tval = {}
                    if float_compare(tadjust.stock_qty, tadjust.line_id.stock_qty, precision_rounding=0.000001) != 0.0:
                        tval['stock_qty'] = tadjust.stock_qty
                        moveval = {
                            'name': self.container_id.name, 'product_id': tadjust.product_id.id, 'product_uom': tadjust.product_id.uom_id.id,
                            'create_date': fields.Datetime.now(), 'company_id': self.env.user.company_id.id, 'restrict_lot_id': tadjust.product_lot.id
                        }
                        if float_compare(tadjust.stock_qty, tadjust.line_id.stock_qty, precision_rounding=0.000001) > 0.0:
                            moveval['product_uom_qty'] = tadjust.stock_qty - tadjust.line_id.stock_qty
                            moveval.update({'location_id': productionlocation, 'location_dest_id': containerlocation})
                        else:
                            moveval['product_uom_qty'] = tadjust.line_id.stock_qty - tadjust.stock_qty
                            moveval.update({'location_id': containerlocation, 'location_dest_id': productionlocation})
                        movevallist.append(moveval)
                    if float_compare(tadjust.temp_qty, tadjust.line_id.temp_qty, precision_rounding=0.000001) != 0.0:
                        tval['temp_qty'] = tadjust.temp_qty
                    if tval and len(tval) > 0:
                       productlines.append((1, tadjust.line_id.id, tval))
                else:
                    productlines.append((0, 0, {
                            'product_id': tadjust.product_id.id, 'stock_qty': tadjust.stock_qty,
                            'product_lot': tadjust.product_lot.id, 'temp_qty': tadjust.temp_qty
                        }))
                    if float_compare(tadjust.stock_qty, 0.0, precision_rounding=0.000001) > 0.0:
                        movevallist.append({
                            'name': self.container_id.name, 'product_id': tadjust.product_id.id, 'product_uom': tadjust.product_id.uom_id.id,
                            'create_date': fields.Datetime.now(), 'company_id': self.env.user.company_id.id, 'restrict_lot_id': tadjust.product_lot.id,
                            'product_uom_qty': tadjust.stock_qty, 'location_id': productionlocation, 'location_dest_id': containerlocation
                        })
        if self.container_id.product_lines and len(self.container_id.product_lines) > 0:
            for pline in self.container_id.product_lines:
                if pline.id not in lineids:
                    productlines.append((2, pline.id, False))
                    movevallist.append({
                        'name': self.container_id.name, 'product_id': pline.product_id.id, 'product_uom': pline.product_id.uom_id.id,
                        'create_date': fields.Datetime.now(), 'company_id': self.env.user.company_id.id, 'restrict_lot_id': pline.product_lot.id,
                        'product_uom_qty': pline.stock_qty, 'location_id': containerlocation, 'location_dest_id': productionlocation
                    })
        if productlines and len(productlines) > 0:
            self.container_id.write({'product_lines': productlines})
        if movevallist and len(movevallist) > 0:
            movelist = self.env['stock.move']
            for tempmove in movevallist:
                movelist |= self.env['stock.move'].create(tempmove)
            movelist.action_done()






class AASContainerAdjustLineWizard(models.TransientModel):
    _name = 'aas.container.adjust.line.wizard'
    _description = 'AAS Container Adjust Line Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.container.adjust.wizard', string=u'调整单', ondelete='cascade')
    line_id = fields.Many2one(comodel_name='aas.container.product', string=u'容器库存', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='cascade')
    stock_qty = fields.Float(string=u'库存数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    temp_qty = fields.Float(string=u'未入库数', digits=dp.get_precision('Product Unit of Measure'), default=0.0)



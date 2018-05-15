# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-28 20:50
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

INVENTORY_STATE = [('draft', u'草稿'),('confirm', u'确认'), ('done', u'完成')]

# 库存盘点
class AASStockInventory(models.Model):
    _name = 'aas.stock.inventory'
    _description = 'ASS Stock Inventory'
    _order = 'serialnumber desc'

    name = fields.Char(string=u'名称', copy=False)
    serialnumber = fields.Char(string=u'流水号', copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    state = fields.Selection(selection=INVENTORY_STATE, string=u'状态', default='draft', copy=False)
    create_time = fields.Datetime(string=u'创建时间', default=fields.Datetime.now)
    create_user = fields.Many2one(comodel_name='res.users', string=u'创建人员', default=lambda self: self.env.user)
    isstock = fields.Boolean(string=u'仓库盘点', default=False, copy=False)


    inventory_lines = fields.One2many(comodel_name='aas.stock.inventory.line', inverse_name='inventory_id', string=u'盘点明细')
    inventory_labels = fields.One2many(comodel_name='aas.stock.inventory.label', inverse_name='inventory_id', string=u'盘点标签')
    inventory_adjust = fields.One2many(comodel_name='aas.stock.inventory.adjust', inverse_name='inventory_id', string=u'调整明细')
    inventory_moves = fields.One2many(comodel_name='aas.stock.inventory.move', inverse_name='inventory_id', string=u'盘盈盘亏')

    _sql_constraints = [('uniq_name', 'unique (name)', u'盘点名称不能出现重复！')]

    @api.model
    def create(self, vals):
        vals['serialnumber'] = self.env['ir.sequence'].next_by_code('aas.stock.inventory')
        return super(AASStockInventory, self).create(vals)

    @api.multi
    def unlink(self):
        for record in self:
            if record.state != 'done':
                continue
            raise UserError(u'盘点%s已完成不可以删除！'% record.name)
        return super(AASStockInventory, self).unlink()


    @api.one
    def action_confirm(self):
        """
        确认盘点
        :return:
        """
        flag = self.action_refresh()
        if flag:
            self.write({'state': 'confirm'})
        else:
           raise UserError(u'请检查当前条件下是否有库存！')

    @api.multi
    def action_refresh(self):
        """
        刷新库存
        :return:
        """
        self.ensure_one()
        return self.action_wms_refresh()

    @api.multi
    def action_wms_refresh(self):
        self.ensure_one()
        tempdomain = [('parent_id', '=', False), ('state', 'in', ['normal', 'frozen'])]
        if self.product_id:
            tempdomain.append(('product_id', '=', self.product_id.id))
        if self.product_lot:
            tempdomain.append(('product_lot', '=', self.product_lot.id))
        if self.location_id:
            tempdomain.append(('location_id', 'child_of', self.location_id.id))
        labellist = self.env['aas.product.label'].search(tempdomain)
        if not labellist or len(labellist) <= 0:
            return False
        tempdict = {}
        for tlabel in labellist:
            pkey = 'P_'+str(tlabel.product_id.id)+'_'+str(tlabel.product_lot.id)+'_'+str(tlabel.location_id.id)
            if pkey not in tempdict:
                tempdict[pkey] = {
                    'product_id': tlabel.product_id.id, 'product_lot': tlabel.product_lot.id,
                    'location_id': tlabel.location_id.id, 'stock_qty': tlabel.product_qty
                }
            else:
                tempdict[pkey]['stock_qty'] += tlabel.product_qty
        templines = []
        if self.inventory_lines and len(self.inventory_lines) > 0:
            for iline in self.inventory_lines:
                pkey = 'P_'+str(iline.product_id.id)+'_'+str(iline.product_lot.id)+'_'+str(iline.location_id.id)
                if pkey in tempdict:
                    templines.append((1, iline.id, {'stock_qty': tempdict[pkey]['stock_qty']}))
                    del tempdict[pkey]
                else:
                    templines.append((2, iline.id, False))
        if tempdict and len(tempdict) > 0:
            templines.extend([(0, 0, tval) for tkey, tval in tempdict.items()])
        self.write({'inventory_lines': templines})
        return True



    @api.multi
    def action_addlabels(self):
        """
        向导，触发此方法弹出向导并进行业务处理
        :return:
        """
        self.ensure_one()
        wizardvals = {
            'inventory_id': self.id, 'inventory_location': self.location_id.id
        }
        if self.product_id:
            wizardvals['product_id'] = self.product_id.id
        if self.product_lot:
            wizardvals['product_lot'] = self.product_lot.name
        wizard = self.env['aas.stock.inventory.addlabel.wizard'].create(wizardvals)
        view_form = self.env.ref('aas_wms.view_form_aas_stock_inventory_addlabel_lots_wizard')
        return {
            'name': u"盘点新增标签批次",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.stock.inventory.addlabel.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }



    @api.one
    def action_done(self):
        """
        完成盘点
        :return:
        """
        location_inventory = self.env.ref('stock.location_inventory')
        movelines , current_time = [], fields.Datetime.now()
        if self.inventory_lines and len(self.inventory_lines) > 0:
            for iline in self.inventory_lines:
                if float_is_zero(iline.differ_qty, precision_rounding=0.000001):
                    continue
                movevals = {
                    'name': iline.product_id.name,
                    'product_id': iline.product_id.id,
                    'product_uom': iline.product_id.uom_id.id,
                    'create_date': current_time,
                    'restrict_lot_id': iline.product_lot.id,
                    'product_uom_qty': abs(iline.differ_qty)
                }
                if float_compare(iline.differ_qty, 0.0, precision_rounding=0.000001) > 0.0:
                    movevals.update({'location_id': location_inventory.id, 'location_dest_id': iline.location_id.id})
                else:
                    movevals.update({'location_id': iline.location_id.id, 'location_dest_id': location_inventory.id})
                tempmove = self.env['stock.move'].create(movevals)
                tempmove.action_done()
                movelines.append((0, 0, {'move_id': tempmove.id}))
        if self.inventory_adjust and len(self.inventory_adjust) > 0:
            movedict = {}
            for iadjust in self.inventory_adjust:
                mkey = 'M_'+str(iadjust.product_id.id)+'_'+str(iadjust.product_lot.id)
                location_src_id, location_dest_id = iadjust.location_id.id, location_inventory.id
                if float_compare(iadjust.adjust_product_qty, 0.0, precision_rounding=0.000001) > 0.0:
                    location_src_id, location_dest_id = location_inventory.id, iadjust.location_id.id
                mkey += '_'+str(location_src_id)+'_'+str(location_dest_id)
                if mkey not in movedict:
                    movedict[mkey] = {
                        'name': iadjust.product_id.name,
                        'product_id': iadjust.product_id.id,
                        'product_uom': iadjust.product_id.uom_id.id,
                        'create_date': current_time,
                        'restrict_lot_id': iadjust.product_lot.id,
                        'product_uom_qty': abs(iadjust.adjust_product_qty),
                        'location_id': location_src_id,
                        'location_dest_id': location_dest_id
                    }
                else:
                    movedict[mkey]['product_uom_qty'] += abs(iadjust.adjust_product_qty)
                # 更新标签上的数量
                iadjust.inventory_label.label_id.write({'product_qty': iadjust.adjust_after_qty})
            for tkey, tval in movedict.items():
                tempmove = self.env['stock.move'].create(tval)
                tempmove.action_done()
                movelines.append((0, 0, {'move_id': tempmove.id}))
        inventoryvals = {'state': 'done'}
        if movelines and len(movelines) > 0:
            inventoryvals['inventory_moves'] = movelines
        self.write(inventoryvals)
        if not self.inventory_labels or len(self.inventory_labels) <= 0:
            return
        # 解除标签锁定
        labellist = self.env['aas.product.label']
        for tlabel in self.inventory_labels:
            if tlabel.label_id:
                labellist |= tlabel.label_id
        if labellist and len(labellist) > 0:
            labellist.write({'locked': False, 'locked_order': False})


    @api.model
    def action_scan_label(self, inventory, barcode):
        """扫描标签盘点
        :param barcode:
        :return:
        """
        values = {'success': True, 'message': '', 'ilabel': False}
        if not barcode:
            values.update({'success': False, 'message': u'请仔细检查是否扫描了一个有效的条码！'})
            return values
        barcode = barcode.upper()
        label = self.env['aas.product.label'].search([('barcode', '=', barcode)], limit=1)
        if not label:
            values.update({'success': False, 'message': u'请仔细检查是否扫描有效的标签！'})
            return values
        labeldomain = [('inventory_id', '=', inventory.id), ('label_id', '=', label.id)]
        if self.env['aas.stock.inventory.label'].search_count(labeldomain) > 0:
            values.update({'success': False, 'message': u'标签已存在请不要重复扫描！'})
            return values
        if label.state not in ['normal', 'frezon']:
            values.update({'success': False, 'message': u'标签状态异常，不在盘点范围！'})
            return values
        if inventory.product_id and inventory.product_id.id != label.product_id.id:
            values.update({'success': False, 'message': u'标签产品与需要盘点的产品不一致，不在盘点范围！'})
            return values
        if inventory.product_lot and inventory.product_lot.id != label.product_lot.id:
            values.update({'success': False, 'message': u'标签产品批次与需要盘点的产品批次不一致，不在盘点范围！'})
            return values
        if inventory.location_id:
            ipleft, ipright = inventory.location_id.parent_left, inventory.location_id.parent_right
            lpleft, lpright = label.location_id.parent_left, label.location_id.parent_right
            if lpleft < ipleft or lpright > ipright:
                values.update({'success': False, 'message': u'标签产品库位与需要盘点的产品库位不一致，不在盘点范围！'})
                return values
        try:
            ilabel = self.env['aas.stock.inventory.label'].create({'inventory_id': inventory.id, 'label_id': label.id})
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        values['ilabel'] = {
            'list_id': ilabel.id, 'product_code': ilabel.product_id.default_code,
            'product_lot': ilabel.product_lot.name, 'product_qty': ilabel.product_qty,
            'location_name': ilabel.location_id.name, 'label_name': ilabel.label_id.name, 'container_name': ''
        }
        return values

    @api.model
    def action_scan_container(self, inventory, barcode):
        """扫描容器盘点
        :param barcode:
        :return:
        """
        values = {'success': True, 'message': '', 'ilabel': False}
        if not barcode:
            values.update({'success': False, 'message': u'请仔细检查是否扫描了一个有效的容器！'})
            return values
        barcode = barcode.upper()
        container = self.env['aas.container'].search([('barcode', '=', barcode)], limit=1)
        if not container:
            values.update({'success': False, 'message': u'请仔细检查是否扫描有效的容器！'})
            return values
        cdomain = [('inventory_id', '=', inventory.id), ('container_id', '=', container.id)]
        if self.env['aas.stock.inventory.label'].search_count(cdomain) > 0:
            values.update({'success': False, 'message': u'容器已存在请不要重复扫描！'})
            return values
        if container.isempty:
            values.update({'success': False, 'message': u'当前容器是一个空的容器，不可以盘点！'})
            return values
        productline = container.product_lines[0]
        if inventory.product_id and inventory.product_id.id != productline.product_id.id:
            values.update({'success': False, 'message': u'容器产品与需要盘点的产品不一致，不在盘点范围！'})
            return values
        if inventory.product_lot and inventory.product_lot.id != productline.product_lot.id:
            values.update({'success': False, 'message': u'容器产品批次与需要盘点的产品批次不一致，不在盘点范围！'})
            return values
        if inventory.location_id:
            ipleft, ipright = inventory.location_id.parent_left, inventory.location_id.parent_right
            cpleft, cpright = container.stock_location_id.parent_left, container.stock_location_id.parent_right
            if cpleft < ipleft or cpright > ipright:
                values.update({'success': False, 'message': u'容器产品库位与需要盘点的产品库位不一致，不在盘点范围！'})
                return values
        try:
            ilabel = self.env['aas.stock.inventory.label'].create({'inventory_id': inventory.id, 'container_id': container.id})
        except UserError, ue:
            values.update({'success': False, 'message': ue.name})
            return values
        values['ilabel'] = {
            'list_id': ilabel.id, 'product_code': ilabel.product_id.default_code,
            'product_lot': ilabel.product_lot.name, 'product_qty': ilabel.product_qty,
            'location_name': ilabel.location_id.name, 'label_name': '', 'container_name': ilabel.container_id.name
        }
        return values


    @api.multi
    def action_inventory_with_scanning(self):
        """条码枪扫描盘点
        :return:
        """
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'target': 'self', 'url': '/aaswms/inventory/detail/'+str(self.id)}






class AASStockInventoryLine(models.Model):
    _name = 'aas.stock.inventory.line'
    _description = u"安费诺库存盘点明细"
    _order = 'product_id, product_lot'

    inventory_id = fields.Many2one(comodel_name='aas.stock.inventory', string=u'盘点单', required=True, ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    stock_qty = fields.Float(string=u'账存数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    actual_qty = fields.Float(string=u'实盘数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    differ_qty = fields.Float(string=u'差异数量', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_differ_qty', store=True, help=u'差异数量=实盘数量-账存数量')

    _sql_constraints = [
        ('uniq_product_location_lot', 'unique (inventory_id, location_id, product_lot)', u'盘点明细中相同库位批次不能出现重复！')
    ]


    @api.depends('stock_qty', 'actual_qty')
    def _compute_differ_qty(self):
        for record in self:
            record.differ_qty = record.actual_qty - record.stock_qty


class AASStockInventoryLabel(models.Model):
    _name = 'aas.stock.inventory.label'
    _description = u"安费诺库存盘点标签"
    _order = 'id desc'
    _rec_name = 'label_id'

    inventory_id = fields.Many2one(comodel_name='aas.stock.inventory', string=u'盘点单', required=True, ondelete='cascade')
    line_id = fields.Many2one(comodel_name='aas.stock.inventory.line', string=u'盘点明细', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    temp_qty = fields.Float(string=u'临时数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器')

    _sql_constraints = [
        ('uniq_label', 'unique (inventory_id, label_id)', u'盘点标签中不能出现重复标签！')
    ]

    @api.one
    @api.constrains('label_id')
    def action_check_label(self):
        tlabel, tinventory = self.label_id, self.inventory_id
        if tlabel.state not in ['normal', 'frozen']:
            raise ValidationError(u'无效标签请仔细检查！')
        if tinventory.product_id and tinventory.product_id.id != tlabel.product_id.id:
            raise ValidationError(u'请仔细检查，标签的产品不在盘点范围内！')
        if tinventory.product_lot and tinventory.product_lot.id != tlabel.product_lot.id:
            raise ValidationError(u'请仔细检查，标签产品批次不在盘点范围内！')
        if tinventory.location_id:
            parent_left, parent_right = tinventory.location_id.parent_left, tinventory.location_id.parent_right
            if tlabel.location_id.parent_left < parent_left or tlabel.location_id.parent_right > parent_right:
                raise ValidationError(u'请仔细检查，标签库位不在盘点范围！')

    @api.onchange('label_id')
    def action_change_label(self):
        if self.label_id:
            self.product_id, self.product_lot = self.label_id.product_id.id, self.label_id.product_lot.id
            self.product_qty, self.location_id = self.label_id.product_qty, self.label_id.location_id.id
        else:
            self.prodcut_id, self.product_lot, self.location_id, self.product_qty = False, False, False, 0.0

    @api.onchange('container_id')
    def action_change_container(self):
        container = self.container_id
        if container:
            if container.isempty:
                self.prodcut_id, self.product_lot, self.location_id, self.product_qty = False, False, False, 0.0
            else:
                productline = container.product_lines[0]
                self.prodcut_id, self.product_lot = productline.product_id.id, productline.product_lot.id
                self.location_id, self.product_qty = container.stock_location_id.id, productline.stock_qty
        else:
            self.prodcut_id, self.product_lot, self.location_id, self.product_qty = False, False, False, 0.0



    @api.model
    def action_before_create(self, vals):
        labelid = vals.get('label_id', False)
        containerid = vals.get('container_id', False)
        if not labelid and not containerid:
            raise UserError(u'盘点内容标签或容器必须设置一个！')
        if labelid:
            tlabel = self.env['aas.product.label'].browse(labelid)
            vals.update({
                'product_id': tlabel.product_id.id, 'product_lot': tlabel.product_lot.id,
                'location_id': tlabel.location_id.id, 'product_qty': tlabel.product_qty,
                'temp_qty': tlabel.product_qty
            })
        elif containerid:
            productline = self.env['aas.container.product'].search([('container_id', '=', containerid)], limit=1)
            container = productline.container_id
            vals.update({
                'product_id': productline.product_id.id, 'product_lot': productline.product_lot.id,
                'location_id': container.stock_location_id.id, 'product_qty': productline.stock_qty,
                'temp_qty': productline.stock_qty
            })


    @api.one
    def action_after_create(self):
        linedomain = [('product_id', '=', self.product_id.id), ('product_lot', '=', self.product_lot.id)]
        linedomain.extend([('location_id', '=', self.location_id.id), ('inventory_id', '=', self.inventory_id.id)])
        iline = self.env['aas.stock.inventory.line'].search(linedomain, limit=1)
        if not iline:
            self.inventory_id.action_refresh()
            iline = self.env['aas.stock.inventory.line'].search(linedomain, limit=1)
        self.write({'line_id': iline.id})
        iline.write({'actual_qty': iline.actual_qty+self.product_qty})
        if self.label_id:
            self.label_id.write({'locked': True, 'locked_order': self.inventory_id.serialnumber})

    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        record = super(AASStockInventoryLabel, self).create(vals)
        record.action_after_create()
        return record

    @api.multi
    def unlink(self):
        inventorylinedict, labellist = {}, self.env['aas.product.label']
        for record in self:
            if record.inventory_id.state == 'done':
                raise UserError(u'盘点已完成，请不要删除扫描记录！')
            if record.label_id:
                labellist |= record.label_id
            ikey = 'L'+str(record.line_id.id)
            if ikey not in inventorylinedict:
                inventorylinedict[ikey] = {'line': record.line_id, 'qty': record.product_qty}
            else:
                inventorylinedict[ikey]['qty'] += record.product_qty
        result = super(AASStockInventoryLabel, self).unlink()
        for lkey, lval in inventorylinedict.items():
            inventoryline, temp_qty = lval['line'], lval['qty']
            inventoryline.write({'actual_qty': inventoryline.actual_qty - temp_qty})
        if labellist and len(labellist) > 0:
            labellist.write({'locked': False, 'locked_order': False})
        return result


class AASStockInventoryAdjust(models.Model):
    _name = 'aas.stock.inventory.adjust'
    _description = u"安费诺库存盘点标签调整"

    inventory_id = fields.Many2one(comodel_name='aas.stock.inventory', string=u'盘点单', required=True, ondelete='cascade')
    inventory_label = fields.Many2one(comodel_name='aas.stock.inventory.label', string=u'标签', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次')
    adjust_before_qty = fields.Float(string=u'调整前数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    adjust_after_qty = fields.Float(string=u'调整后数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    adjust_product_qty = fields.Float(string=u'调整数量', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_product_qty', store=True)

    @api.depends('adjust_before_qty', 'adjust_after_qty')
    def _compute_product_qty(self):
        for record in self:
            record.adjust_product_qty = record.adjust_after_qty - record.adjust_before_qty

    @api.one
    @api.constrains('adjust_before_qty', 'adjust_after_qty')
    def action_check_qty(self):
        if float_compare(self.adjust_before_qty, self.adjust_after_qty, precision_rounding=0.000001) == 0.0:
            raise ValidationError(u'标签%s调整前后数量不能相等'% self.inventory_label.label_id.name)
        if float_compare(self.adjust_after_qty, 0.0, precision_rounding=0.000001) < 0.0:
            raise ValidationError(u'标签%s调整后数量不能小于0'% self.inventory_label.label_id.name)

    @api.onchange('inventory_label')
    def action_change_label(self):
        if self.inventory_label:
            self.product_id, self.location_id = self.inventory_label.product_id.id, self.inventory_label.location_id.id
            self.product_lot, self.adjust_before_qty = self.inventory_label.product_lot.id, self.inventory_label.temp_qty
        else:
            self.product_id, self.location_id, self.product_lot, self.adjust_before_qty = False, False, False, 0.0

    @api.model
    def action_before_create(self, vals):
        inventorylabel = self.env['aas.stock.inventory.label'].browse(vals.get('inventory_label'))
        vals.update({
            'product_id': inventorylabel.product_id.id, 'location_id': inventorylabel.location_id.id,
            'product_lot': inventorylabel.product_lot.id, 'adjust_before_qty': inventorylabel.temp_qty
        })

    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        return super(AASStockInventoryAdjust, self).create(vals)





class AASStockInventoryMove(models.Model):
    _name = 'aas.stock.inventory.move'
    _description = u"安费诺库存盘盈盘亏"

    inventory_id = fields.Many2one(comodel_name='aas.stock.inventory', string=u'盘点单', required=True, ondelete='cascade')
    move_id = fields.Many2one(comodel_name='stock.move', string=u'移库明细')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'))
    location_src_id = fields.Many2one(comodel_name='stock.location', string=u'来源库位')
    location_dest_id = fields.Many2one(comodel_name='stock.location', string=u'目标库位')

    @api.model
    def action_before_create(self, vals):
        if not vals.get('move_id'):
            return
        tempmove = self.env['stock.move'].browse(vals.get('move_id'))
        vals.update({
            'product_id': tempmove.product_id.id, 'product_lot': tempmove.restrict_lot_id.id,
            'product_qty': tempmove.product_uom_qty, 'location_src_id': tempmove.location_id.id,
            'location_dest_id': tempmove.location_dest_id.id
        })


    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        return super(AASStockInventoryMove, self).create(vals)

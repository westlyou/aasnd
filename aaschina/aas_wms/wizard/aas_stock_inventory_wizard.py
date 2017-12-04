# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-29 07:48
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import math
import logging

_logger = logging.getLogger(__name__)

class AASStockInventoryAddlabelWizard(models.TransientModel):
    _name = 'aas.stock.inventory.addlabel.wizard'
    _description = 'AAS Stock Inventory Addlabel Wizard'

    inventory_id = fields.Many2one(comodel_name='aas.stock.inventory', string=u'盘点单', ondelete='cascade')
    inventory_location = fields.Many2one(comodel_name='stock.location', string=u'盘点库位', ondelete='set null')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='cascade')
    product_lot = fields.Char(string=u'批次')
    systemstock = fields.Boolean(string=u'系统库存', default=False, copy=False)

    lot_lines = fields.One2many(comodel_name='aas.stock.inventory.addlabel.lots.wizard', inverse_name='wizard_id', string=u'批次明细')
    label_lines = fields.One2many(comodel_name='aas.stock.inventory.addlabel.labels.wizard', inverse_name='wizard_id', string=u'标签明细')

    @api.one
    @api.constrains('product_id')
    def action_check_product(self):
        if self.inventory_id.product_id and self.inventory_id.product_id.id != self.product_id.id:
            raise ValidationError(u'请仔细检查，新增标签的产品和盘点产品不匹配！')


    @api.multi
    def action_lots_split(self):
        self.ensure_one()
        if not self.lot_lines or len(self.lot_lines) <= 0:
            raise UserError(u'请先添加批次明细！')
        label_lines = []
        for templot in self.lot_lines:
            temp_qty = templot.product_qty
            for i in range(0, int(math.ceil(templot.product_qty / templot.label_qty))):
                if float_compare(temp_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                    break
                labelval = {'product_lot': templot.product_lot}
                if float_compare(temp_qty, templot.label_qty, precision_rounding=0.000001) <= 0.0:
                    labelval['label_qty'] = temp_qty
                else:
                    labelval['label_qty'] = templot.label_qty
                temp_qty -= labelval['label_qty']
                label_lines.append((0, 0, labelval))
        self.write({'label_lines': label_lines})
        view_form = self.env.ref('aas_wms.view_form_aas_stock_inventory_addlabel_labels_wizard')
        return {
            'name': u"盘点新增标签",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.stock.inventory.addlabel.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context
        }

    @api.multi
    def action_done(self):
        self.ensure_one()
        if not self.label_lines or len(self.label_lines) <= 0:
            return
        labelist, lotdict = [], {}
        for labelline in self.label_lines:
            if labelline.product_lot not in lotdict:
                templot = self.env['stock.production.lot'].search([('name', '=', labelline.product_lot), ('product_id', '=', self.product_id.id)], limit=1)
                if not templot:
                    templot = self.env['stock.production.lot'].create({
                        'product_id': self.product_id.id, 'name': labelline.product_lot, 'product_uom_id': self.product_id.uom_id.id, 'create_date': fields.Datetime.now()
                    })
                lotdict[labelline.product_lot] = templot.id
            templabel = self.env['aas.product.label'].create({
                'product_id': self.product_id.id, 'product_lot': lotdict[labelline.product_lot],
                'product_qty': labelline.label_qty, 'location_id': self.location_id.id,
                'stocked': True, 'origin_order': self.inventory_id.serialnumber,
                'onshelf_time': fields.Datetime.now(), 'onshelf_date': fields.Date.today()
            })
            labelist.append(templabel)
        movedict, inventory_location, current_time = {}, self.env.ref('stock.location_inventory'), fields.Datetime.now()
        if not self.systemstock:
            for lotline in self.lot_lines:
                templotid = lotdict[lotline.product_lot]
                mkey = 'M_'+str(self.product_id.id)+'_'+str(templotid)+'_'+str(self.location_id.id)+'_'+str(inventory_location.id)
                if mkey in movedict:
                    movedict[mkey]['product_uom_qty'] += lotline.product_qty
                else:
                    movedict[mkey] = {
                        'name': self.product_id.name,
                        'product_id': self.product_id.id,
                        'product_uom': self.product_id.uom_id.id,
                        'create_date': current_time,
                        'restrict_lot_id': templotid,
                        'product_uom_qty': lotline.product_qty,
                        'location_id': inventory_location.id,
                        'location_dest_id': self.location_id.id
                    }
        if movedict and len(movedict) > 0:
            movelist = self.env['stock.move']
            for tkey, tval in movedict.items():
                movelist |= self.env['stock.move'].create(tval)
            movelist.action_done()
        self.inventory_id.action_refresh()
        self.inventory_id.write({'inventory_labels': [(0, 0, {'label_id': tlabel.id}) for tlabel in labelist]})




class AASStockInventoryAddlabelLotsWizard(models.TransientModel):
    _name = 'aas.stock.inventory.addlabel.lots.wizard'
    _description = 'AAS Stock Inventory Addlabel Lots Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.stock.inventory.addlabel.wizard', string=u'Wizard', ondelete='cascade')
    product_lot = fields.Char(string=u'批次名称')
    product_qty = fields.Float(string=u'批次数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    label_qty = fields.Float(string=u'每标签数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    @api.one
    @api.constrains('product_qty', 'label_qty')
    def action_check_qty(self):
        if float_compare(self.product_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise ValidationError(u'批次%s数量不能小于等于0！'% self.product_lot)
        if float_compare(self.label_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise ValidationError(u'批次%s的每标签数量不能小于等于0！'% self.product_lot)
        if float_compare(self.label_qty, self.product_qty, precision_rounding=0.000001) > 0:
            raise ValidationError(u'批次%s每标签数量不能大于批次总数！'% self.product_lot)

    @api.one
    @api.constrains('product_lot')
    def action_check_lot(self):
        if self.wizard_id.product_lot and self.wizard_id.product_lot!=self.product_lot:
            raise ValidationError(u'请仔细检查，新增标签批次名称与盘点批次名称不匹配！')



class AASStockInventoryAddlabelLabelsWizard(models.TransientModel):
    _name = 'aas.stock.inventory.addlabel.labels.wizard'
    _description = 'AAS Stock Inventory Addlabel Labels Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.stock.inventory.addlabel.wizard', string=u'Wizard', ondelete='cascade')
    product_lot = fields.Char(string=u'批次名称')
    label_qty = fields.Float(string=u'标签数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

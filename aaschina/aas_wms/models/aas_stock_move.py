# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-9-4 10:35
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


# 内部调拨
class AASStockMove(models.Model):
    _name = 'aas.stock.move'
    _description = 'AAS Stock Move'
    _order = 'id desc'


    name = fields.Char(string=u'单号', copy=False)
    title = fields.Char(string=u'名称', copy=False)
    location_id = fields.Many2one(comodel_name='stock.location', string=u'目标库位', ondelete='restrict')
    state = fields.Selection(selection=[('draft', u'草稿'), ('confirm', u'确认'), ('done', u'完成')], string=u'状态', default='draft', copy=False)
    note = fields.Text(string=u'备注')
    move_time = fields.Datetime(string=u'调拨时间', copy=False)

    move_lines = fields.One2many(comodel_name='aas.stock.move.line', inverse_name='move_id', string=u'调拨明细')
    move_labels = fields.One2many(comodel_name='aas.stock.move.label', inverse_name='move_id', string=u'调拨标签')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('aas.stock.move')
        return super(AASStockMove, self).create(vals)

    @api.one
    def action_confirm(self):
        if self.state != 'draft':
            return
        if self.move_lines and len(self.move_lines) > 0:
            return
        if not self.move_labels or len(self.move_labels) <= 0:
            return
        productdict = {}
        for mlabel in self.move_labels:
            mkey = 'P-'+str(mlabel.product_id.id)+'-'+str(mlabel.product_lot.id)
            if mkey in productdict:
                productdict[mkey]['product_qty'] += mlabel.label_id.product_qty
            else:
                productdict[mkey] = {
                    'product_id': mlabel.product_id.id,
                    'product_uom': mlabel.product_uom.id,
                    'product_lot': mlabel.product_lot.id,
                    'product_qty': mlabel.label_id.product_qty
                }
        mlines = [(0, 0, mval) for mkey, mval in productdict.items()]
        self.write({'move_lines': mlines, 'state': 'confirm'})

    @api.one
    def action_done(self):
        if self.state != 'confirm':
            return
        if not self.move_labels or len(self.move_labels) <= 0:
            return
        if not self.move_lines or len(self.move_lines) <= 0:
            return
        templabels = self.env['aas.product.label']
        movedict, company_id, currenttime = {}, self.env.user.company_id.id, fields.Datetime.now()
        for mlabel in self.move_labels:
            templabels |= mlabel.label_id
            mkey = 'P-'+str(mlabel.product_id.id)+'-'+str(mlabel.product_lot.id)+'-'+str(mlabel.location_id.id)
            if mkey in movedict:
                movedict[mkey]['product_uom_qty'] += mlabel.label_id.product_qty
            else:
                movedict[mkey] = {
                    'name': self.name, 'product_id': mlabel.product_id.id, 'product_uom': mlabel.product_uom.id,
                    'create_date': currenttime, 'restrict_lot_id': mlabel.product_lot.id, 'product_uom_qty': mlabel.label_id.product_qty,
                    'location_id': mlabel.location_id.id, 'location_dest_id': self.location_id.id, 'company_id': company_id
                }
        movelist = self.env['stock.move']
        for mkey, mval in movedict.items():
            movelist |= self.env['stock.move'].create(mval)
            self.env['aas.receive.deliver'].action_receive(mval['product_id'], mval['location_dest_id'], mval['restrict_lot_id'], mval['product_uom_qty'])
            self.env['aas.receive.deliver'].action_deliver(mval['product_id'], mval['location_id'], mval['restrict_lot_id'], mval['product_uom_qty'])
        movelist.action_done()
        templabels.write({'location_id': self.location_id.id, 'locked': False, 'locked_order': False})
        self.write({'state': 'done', 'move_time': fields.Datetime.now()})

    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(u'%s调拨已完成不可以删除！'% record.name)
        return super(AASStockMove, self).unlink()



class AASStockMoveLine(models.Model):
    _name = 'aas.stock.move.line'
    _description = 'AAS Stock Move Line'
    _order = 'product_id,product_lot'

    move_id = fields.Many2one(comodel_name='aas.stock.move', string=u'调拨单', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

class AASStockMoveLabel(models.Model):
    _name = 'aas.stock.move.label'
    _description = 'AAS Stock Move Label'

    move_id = fields.Many2one(comodel_name='aas.stock.move', string=u'调拨单', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    location_id = fields.Many2one(comodel_name='stock.location', string=u'来源库位', ondelete='restrict')

    _sql_constraints = [
        ('uniq_label', 'unique (move_id, label_id)', u'请不要重复添加同一个标签！')
    ]

    @api.onchange('label_id')
    def action_change_label(self):
        if self.label_id:
            self.product_id, self.product_uom = self.label_id.product_id.id, self.label_id.product_uom.id
            self.product_lot, self.location_id = self.label_id.product_lot.id, self.label_id.location_id.id
            self.product_qty = self.label_id.product_qty
        else:
            self.product_id, self.product_uom = False, False
            self.product_lot, self.location_id, self.product_qty = False, False, 0.0

    @api.model
    def action_before_create(self, vals):
        templabel = self.env['aas.product.label'].browse(vals.get('label_id'))
        vals.update({
            'product_id': templabel.product_id.id, 'product_uom': templabel.product_uom.id,
            'product_lot': templabel.product_lot.id, 'location_id': templabel.location_id.id,
            'product_qty': templabel.product_qty
        })

    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        record = super(AASStockMoveLabel, self).create(vals)
        # 调拨单锁定标签
        record.label_id.write({'locked': True, 'locked_order': record.move_id.name})
        return record

    @api.multi
    def unlink(self):
        labelist = self.env['aas.product.label']
        for record in self:
            labelist |= record.label_id
        result = super(AASStockMoveLabel, self).unlink()
        labelist.write({'locked': False, 'locked_order': False})
        return result
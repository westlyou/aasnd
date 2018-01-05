# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-1-5 12:08
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


CONCESSIONSTATES = [('draft', u'草稿'), ('confirm', u'确认'), ('done', u'完成')]

# 让步接收单
class AASQualityConcession(models.Model):
    _name = 'aas.quality.concession'
    _description = 'AAS Quality Concession'
    _order = 'create_time desc'

    name = fields.Char(string=u'名称', required=True, copy=False)
    create_time = fields.Datetime(string=u'创建时间', default=fields.Datetime.now, copy=False)
    creator_id = fields.Many2one(comodel_name='res.users', string=u'创建人', default=lambda self: self.env.user)
    receipter_id = fields.Many2one(comodel_name='res.users', string=u'收货人', ondelete='restrict')
    receipt_time = fields.Datetime(string=u'收货时间', copy=False)
    state = fields.Selection(selection=CONCESSIONSTATES, string=u'状态', default='draft', copy=False)
    location_dest_id = fields.Many2one(comodel_name='stock.location', string=u'目标库位', ondelete='restrict')
    concession_lines = fields.One2many(comodel_name='aas.quality.concession.line', inverse_name='concession_id', string=u'让步明细')
    concession_labels = fields.One2many(comodel_name='aas.quality.concession.label', inverse_name='concession_id', string=u'让步标签')

    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(u'让步接收已经完成，不可以删除！')
        return super(AASQualityConcession, self).unlink()

    @api.one
    def action_confirm(self):
        if not self.concession_labels or len(self.concession_labels) <= 0:
            raise UserError(u'请先添加需要让步接收处理的标签！')
        labelist = self.env['aas.product.label']
        for clabel in self.concession_labels:
            labelist |= clabel.label_id
        labelist.write({'qualified': True})
        self.write({'state': 'confirm'})


    @api.multi
    def action_receipt(self):
        """
        向导，触发此方法弹出向导并进行业务处理
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.quality.concession.receipt.wizard'].create({'concession_id': self.id})
        view_form = self.env.ref('aas_quality.view_form_aas_quality_concession_receipt_wizard')
        return {
            'name': u"完成收货",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.quality.concession.receipt.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }

    @api.one
    def action_done(self):
        if not self.location_dest_id:
            raise UserError(u'请先设置好收货库位！')
        destlocation = self.location_dest_id
        movedict, labellist = {}, self.env['aas.product.label']
        for clabel in self.concession_labels:
            label = clabel.label_id
            labellist |= label
            mkey = 'M-'+str(label.product_id.id)+'-'+str(label.location_id.id)+'-'+str(label.product_lot.id)
            if mkey in movedict:
                movedict[mkey]['product_uom_qty'] += label.product_qty
            else:
                movedict[mkey] = {
                    'name': label.product_code, 'origin': self.name,
                    'product_id': label.product_id.id, 'product_uom': label.product_uom.id,
                    'create_date': fields.Datetime.now(), 'restrict_lot_id': label.product_lot.id,
                    'product_uom_qty': label.product_qty, 'location_id': label.location_id.id,
                    'location_dest_id': destlocation.id
                }
        concessionmoves = self.env['stock.move']
        for mkey, mval in movedict.items():
            concessionmoves |= self.env['stock.move'].create(mval)
        concessionmoves.action_done()
        labellist.write({'location_id': destlocation.id})
        self.write({'state': 'done', 'receipter_id': self.env.user.id, 'receipt_time': fields.Datetime.now()})



# 让步接收单明细
class AASQualityConcessionLine(models.Model):
    _name = 'aas.quality.concession.line'
    _description = 'AAS Quality Concession Line'

    concession_id = fields.Many2one(comodel_name='aas.quality.concession', string=u'让步接收单', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'))



class AASQualityConcessionLabel(models.Model):
    _name = 'aas.quality.concession.label'
    _description = 'AAS Quality Concession Label'

    concession_id = fields.Many2one(comodel_name='aas.quality.concession', string=u'让步接收单', ondelete='cascade')
    line_id = fields.Many2one(comodel_name='aas.quality.concession.line', string=u'让步明细')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'))
    location_id = fields.Many2one(comodel_name='stock.location', string=u'标签库位', ondelete='restrict')

    _sql_constraints = [
        ('uniq_label', 'unique (concession_id, label_id)', u'请不要重复添加同一个标签！')
    ]

    @api.onchange('label_id')
    def action_change_label(self):
        if not self.label_id:
            self.product_id, self.product_uom = False, False
            self.location_id, self.product_qty = False, 0.0
        else:
            label = self.label_id
            self.product_id, self.product_uom = label.product_id.id, label.product_uom.id
            self.location_id, self.product_qty = label.location_id.id, label.product_qty


    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        record = super(AASQualityConcessionLabel, self).create(vals)
        record.action_after_create()
        return record

    @api.model
    def action_before_create(self, vals):
        if vals.get('label_id', False):
            label = self.env['aas.product.label'].browse(vals.get('label_id'))
            vals.update({
                'product_id': label.product_id.id, 'product_uom': label.product_uom.id,
                'location_id': label.location_id.id, 'product_qty': label.product_qty
            })

    @api.one
    def action_after_create(self):
        concessionline = self.env['aas.quality.concession.line'].search([('concession_id', '=', self.concession_id.id), ('product_id', '=', self.product_id.id)], limit=1)
        if not concessionline:
            concessionline = self.env['aas.quality.concession.line'].create({
                'concession_id': self.concession_id.id, 'product_id': self.product_id.id,
                'product_uom': self.product_uom.id, 'product_qty': self.product_qty
            })
        else:
            concessionline.write({'product_qty': concessionline.product_qty+self.product_qty})
        self.write({'line_id': concessionline.id})


    @api.multi
    def unlink(self):
        concessionlinedict = {}
        for record in self:
            ckey = 'L'+str(record.line_id.id)
            if ckey in concessionlinedict:
                concessionlinedict[ckey]['product_qty'] += record.product_qty
            else:
                concessionlinedict[ckey] = {'line': record.line_id, 'product_qty': record.product_qty}
        result = super(AASQualityConcessionLabel, self).unlink()
        for tkey, tval in concessionlinedict.items():
            concessionline, product_qty = tval['line'], tval['product_qty']
            concessionline.write({'product_qty': concessionline.product_qty - product_qty})
        return result




class AASQualityConcessionReceiptWizard(models.TransientModel):
    _name = 'aas.quality.concession.receipt.wizard'
    _description = 'AAS Quality Concession Receipt Wizard'

    concession_id = fields.Many2one(comodel_name='aas.quality.concession', string=u'让步接收单', ondelete='cascade')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'收货库位')

    @api.one
    def action_done(self):
        if not self.location_id:
            raise UserError(u'请先设置收货库位！')
        self.concession_id.write({'location_dest_id': self.location_id.id})
        self.concession_id.action_done()

# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-3-23 15:34
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import math
import logging

_logger = logging.getLogger(__name__)


# 生产杂入
class AASMESSundryin(models.Model):
    _name = 'aas.mes.sundryin'
    _description = 'AAS MES Sundryin'
    _rec_name = 'product_id'

    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_lot = fields.Char(string=u'批次')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')
    sundryin_qty = fields.Float(string=u'杂入数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    everyone_qty = fields.Float(string=u'每标签数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    sundry_note = fields.Text(string=u'说明信息')
    operate_time = fields.Datetime(string=u'杂入时间', default=fields.Datetime.now, copy=False)
    operater_id = fields.Many2one(comodel_name='res.users', string=u'操作员', default=lambda self: self.env.user)
    state = fields.Selection(selection=[('draft', u'草稿'), ('done', u'完成')], string=u'状态', default='draft', copy=False)
    label_lines = fields.One2many(comodel_name='aas.mes.sundryin.label', inverse_name='sundryin_id', string=u'标签明细')
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    @api.one
    def action_done(self):
        if self.state == 'done':
            return
        if self.label_lines and len(self.label_lines) > 0:
            raise UserError(u'已生成标签明细请不要重复操作！')
        if float_compare(self.sundryin_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise UserError(u'杂入总数不能小于0！')
        if float_compare(self.everyone_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise UserError(u'每标签数量不能小于0！')
        if float_compare(self.sundryin_qty, self.everyone_qty, precision_rounding=0.000001) < 0.0:
            raise UserError(u"每标签数量不可以大于杂入总数！")
        temp_qty, labellines = self.sundryin_qty, []

        productlot = self.env['stock.production.lot'].action_checkout_lot(self.product_id.id, self.product_lot)
        for index in range(0, int(math.ceil(self.sundryin_qty / self.everyone_qty))):
            if float_compare(temp_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                break
            if float_compare(temp_qty, self.everyone_qty, precision_rounding=0.000001) >= 0.0:
                labelqty = self.everyone_qty
            else:
                labelqty = temp_qty
            tlabel = self.env['aas.product.label'].create({
                'product_id': self.product_id.id, 'product_lot': productlot.id,
                'location_id': self.location_id.id, 'stocked': True, 'product_qty': labelqty
            })
            labellines.append((0, 0, {'label_id': tlabel.id, 'product_qty': labelqty}))
            temp_qty -= labelqty
        self.write({'label_lines': labellines, 'state': 'done'})
        company_id, tproduct = self.env.user.company_id.id, self.product_id
        sundrylocation = self.env.ref('aas_wms.stock_location_sundry')
        self.env['stock.move'].create({
            'name': u'杂入%s'% tproduct.default_code, 'product_id': tproduct.id,
            'product_uom': tproduct.uom_id.id, 'create_date': fields.Datetime.now(),
            'restrict_lot_id': productlot.id, 'product_uom_qty': self.sundryin_qty,
            'location_id': sundrylocation.id, 'location_dest_id': self.location_id.id, 'company_id': company_id
        }).action_done()

    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(u'已完成的杂入操作不可以删除！')
        return super(AASMESSundryin, self).unlink()


    @api.multi
    def action_showlabels(self):
        self.ensure_one()
        if not self.label_lines or len(self.label_lines) <= 0:
            raise UserError(u'当前还没有标签清单！')
        labelids = [str(tlabel.label_id.id) for tlabel in self.label_lines]
        if len(labelids) == 1:
            labeldomain = "[('id','=',"+labelids[0]+")]"
        else:
            labelidsstr = ','.join(labelids)
            labeldomain = "[('id','in',("+labelidsstr+"))]"
        view_form = self.env.ref('aas_wms.view_form_aas_product_label')
        view_tree = self.env.ref('aas_wms.view_tree_aas_product_label')
        return {
            'name': u"标签清单",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'aas.product.label',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'target': 'self',
            'context': self.env.context,
            'domain': labeldomain
        }



# 生产杂入生成的标签
class AASMESSundryinLabel(models.Model):
    _name = 'aas.mes.sundryin.label'
    _description = 'AAS MES Sundryin Label'


    sundryin_id = fields.Many2one(comodel_name='aas.mes.sundryin', string=u'生产杂入', ondelete='restrict')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', default=lambda self: self.env.user.company_id)

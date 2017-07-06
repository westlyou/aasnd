# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-6 09:31
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

CHECK_STATE = [('draft', u'草稿'), ('tocheck', u'待检'), ('checking', u'检测中'), ('done', u'完成'), ('cancel', u'取消')]

class AASQualityOrder(models.Model):
    _name = 'aas.quality.order'
    _description = 'AAS Quality Order'
    _order = 'id desc'

    name = fields.Char(string=u'名称', copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'业务伙伴', ondelete='restrict')
    state = fields.Selection(selection=CHECK_STATE, string=u'状态', default='draft', copy=False)
    product_qty = fields.Float(string=u'报检数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    qualified_qty = fields.Float(string=u'合格数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    concession_qty = fields.Float(string=u'让步数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    unqualified_qty = fields.Float(string=u'不合格数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    commit_user = fields.Many2one(comodel_name='res.users', string=u'报检人员', ondelete='restrict')
    commit_time = fields.Datetime(string=u'报检时间', default=fields.Datetime.now, copy=False)
    check_user = fields.Many2one(comodel_name='res.users', string=u'质检人员', ondelete='restrict')
    check_time = fields.Datetime(string=u'质检时间')
    remark = fields.Text(string=u'备注', copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)

    label_lines = fields.One2many(comodel_name='aas.quality.label', inverse_name='order_id', string=u'质检明细')
    operation_lines = fields.One2many(comodel_name='aas.quality.operation', inverse_name='order_id', string=u'作业明细')
    rejection_lines = fields.One2many(comodel_name='aas.quality.rejection', inverse_name='order_id', string=u'不合格品')

    @api.model
    def action_before_create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('aas.quality.order')
        if not vals.get('product_uom'):
            product = self.env['product.product'].browse(vals.get('product_id'))
            vals['product_uom'] = product.uom_id.id

    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        return super(AASQualityOrder, self).create(vals)


    @api.onchange('label_lines')
    def action_change_label_lines(self):
        if self.label_lines and len(self.label_lines) > 0:
            self.product_qty = sum([qlabel.product_qty for qlabel in self.label_lines])
        else:
            self.product_qty = 0.0


    @api.multi
    def action_refresh_checking(self):
        """
        刷新质检详情
        :return:
        """
        for record in self:
            qualified_qty, concession_qty, unqualified_qty = 0.0, 0.0, 0.0
            if record.operation_lines and len(record.operation_lines):
                for opline in record.operation_lines:
                    if float_is_zero(opline.product_qty, precision_rounding=0.000001):
                        continue
                    qualified_qty += opline.qualified_qty
                    concession_qty += opline.concession_qty
                    unqualified_qty += opline.unqualified_qty
            record.write({'qualified_qty': qualified_qty, 'concession_qty': concession_qty, 'unqualified_qty': unqualified_qty})

    @api.one
    def action_confirm(self):
        """
        确认质检单，等待质检
        :return:
        """
        if not self.label_lines or len(self.label_lines) <= 0:
            raise UserError(u'请先添加质检表现明细！')
        self.write({'state': 'tocheck'})

    @api.multi
    def action_commit_quality(self, commiter=None):
        """
        批量报检
        :param commiter:
        :return:
        """
        for record in self:
            if not record.label_lines or len(record.label_lines) <= 0:
                raise UserError(u'质检单%s还没有添加标签明细！'% record.name)
        qvals = {'state': 'tocheck', 'commit_time': fields.Datetime.now()}
        if not commiter:
            qvals['commit_user'] = self.env.user.id
        else:
            qvals['commit_user'] = commiter.id
        self.write(qvals)

    @api.one
    def action_all_qualified(self):
        """
        一次性未检测的标签全部合格
        :return:
        """
        qlabels = self.env['aas.quality.label'].search([('order_id', '=', self.id), ('label_checked', '=', False)])
        if qlabels and len(qlabels) > 0:
            self.write({'operation_lines': [(0, 0, {'qlabel_id': qlabel.id}) for qlabel in qlabels]})

    @api.multi
    def action_done(self):
        self.ensure_one()
        qlabels = self.env['aas.quality.label'].search([('order_id', '=', self.id), ('label_checked', '=', False)])
        if qlabels and len(qlabels) > 0:
            raise UserError(u'您还有部分标签还未检测')




    @api.none
    def action_all_unqualified(self):
        """
        一次性未质检的标签全部不合格
        :return:
        """
        qlabels = self.env['aas.quality.label'].search([('order_id', '=', self.id), ('label_checked', '=', False)])
        if qlabels and len(qlabels) > 0:
            self.write({'operation_lines': [(0, 0, {'qlabel_id': qlabel.id, 'unqualified_qty': qlabel.product_qty}) for qlabel in qlabels]})


    @api.multi
    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(u'质检单%s已经开始执行，请不要删除'% record.name)
        return super(AASQualityOrder, self).unlink()


class AASQualityLabel(models.Model):
    _name = 'aas.quality.label'
    _description = 'AAS Quality Label'
    _order = 'id desc'
    _rec_name = 'label_id'

    order_id = fields.Many2one(comodel_name='aas.quality.order', string=u'质检单', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    origin_order = fields.Char(string=u'来源单据', copy=False)
    label_checked = fields.Boolean(string=u'是否检测', default=False, copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)
    # 报检单据信息
    commit_id = fields.Integer(string=u'报检单据ID')
    commit_model = fields.Char(string=u'报检单据Model')
    commit_order = fields.Char(string=u'报检单据名称')

    _sql_constraints = [
        ('uniq_label', 'unique (order_id, label_id)', u'请不要重复添加同一个标签！')
    ]

    @api.onchange('label_id')
    def action_change_label(self):
        self.product_id, self.product_uom = self.label_id.product_id.id, self.label_id.product_uom.id
        self.product_lot, self.product_qty = self.label_id.product_lot.id, self.label_id.product_qty
        self.origin_order = self.label_id.origin_order


    @api.model
    def action_before_create(self, vals):
        label = self.env['aas.product.label'].browse(vals.get('label_id'))
        vals.update({
            'product_id': label.product_id.id, 'product_uom': label.product_uom.id,
            'product_lot': label.product_lot.id, 'product_qty': label.product_qty,
            'origin_order': label.origin_order
        })

    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        return super(AASQualityLabel, self).create(vals)



class AASQualityOperation(models.Model):
    _name = 'aas.quality.operation'
    _description = 'AAS Quality Operation'

    order_id = fields.Many2one(comodel_name='aas.quality.order', string=u'质检单', ondelete='cascade')
    qlabel_id = fields.Many2one(comodel_name='aas.quality.label', string=u'标签', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    product_qty = fields.Float(string=u'报检数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    qualified_qty = fields.Float(string=u'合格数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    concession_qty = fields.Float(string=u'让步数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    unqualified_qty = fields.Float(string=u'不合格数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)

    # 报检单据信息
    commit_id = fields.Integer(string=u'报检单据ID')
    commit_model = fields.Char(string=u'报检单据Model')
    commit_order = fields.Char(string=u'报检单据名称')

    _sql_constraints = [
        ('uniq_qlabel', 'unique (order_id, qlabel_id)', u'请不要重复添加同一个标签！')
    ]

    @api.onchange('concession_qty', 'unqualified_qty')
    def action_change_unqualified_concession(self):
        self.qualified_qty = self.product_qty - self.concession_qty - self.unqualified_qty

    @api.one
    @api.constrains('concession_qty', 'unqualified_qty')
    def action_check_unqualified_concession(self):
        if float_compare(self.concession_qty, 0,0, precision_rounding=0.000001) < 0.0:
            raise ValidationError(u'%s让步数量不能小于零'% self.qlabel_id.label_id.name)
        if float_compare(self.concession_qty, self.product_qty, precision_rounding=0.000001) > 0.0:
            raise ValidationError(u'%s让步数量不能大于报检数量'% self.qlabel_id.label_id.name)
        if float_compare(self.unqualified_qty, 0.0, precision_rounding=0.000001) < 0.0:
            raise ValidationError(u'%s不合格数量不能小于零'% self.qlabel_id.label_id.name)
        if float_compare(self.unqualified_qty, self.product_qty, precision_rounding=0.000001) > 0.0:
            raise ValidationError(u'%s不合格数量不能大于报检数量'% self.qlabel_id.label_id.name)
        if float_compare(self.concession_qty+self.unqualified_qty, self.product_qty, precision_rounding=0.000001) > 0.0:
            raise ValidationError(u'%s不合格与让步数量之和不能大于报检数量'% self.qlabel_id.label_id.name)

    @api.onchange('qlabel_id')
    def action_change_qlabel(self):
        self.product_id, self.product_uom = self.qlabel_id.product_id.id, self.qlabel_id.product_uom.id
        self.product_lot, self.product_qty = self.qlabel_id.product_lot.id, self.qlabel_id.product_qty


    @api.model
    def action_before_create(self, vals):
        qlabel = self.env['aas.quality.label'].browse(vals.get('qlabel_id'))
        vals.update({
            'product_id': qlabel.product_id.id, 'product_uom': qlabel.product_uom.id,
            'product_lot': qlabel.product_lot.id, 'product_qty': qlabel.product_qty,
            'commit_id': qlabel.commit_id, 'commit_model': qlabel.commit_model, 'commit_order': qlabel.commit_order
        })

    @api.one
    def action_after_create(self):
        self.order_id.action_refresh_checking()
        self.qlabel_id.write({'label_checked': True})

    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        record = super(AASQualityOperation, self).create(vals)
        record.action_after_create()
        return record



    @api.multi
    def write(self, vals):
        result = super(AASQualityOperation, self).write(vals)
        self.action_after_write(vals)
        return result

    @api.multi
    def action_after_write(self, vals):
        # 更新质检单 合格数量、让步数量、不合格数量信息
        if not vals.get('concession_qty') and  not vals.get('unqualified_qty'):
            return True
        qualityids = []
        for qoperation in self:
            qorder = qoperation.order_id
            if qorder.id in qualityids:
                continue
            qorder.action_refresh_checking()
            qualityids.append(qorder.id)

    @api.multi
    def unlink(self):
        qualityids, qualityorders, qualitylabels = [], self.env['aas.quality.order'], self.env['aas.quality.label']
        for record in self:
            qualitylabels |= record.qlabel_id
            qorder = record.order_id
            if qorder.id in qualityids:
                continue
            else:
                qualityorders |= qorder
                qualityids.append(qorder.id)
        result = super(AASQualityOperation, self).unlink()
        qualityorders.action_refresh_checking()
        qualitylabels.write({'label_checked': False})
        return result



class AASQualityRejection(models.Model):
    _name = 'aas.quality.rejection'
    _description = 'AAS Quality Rejection'

    order_id = fields.Many2one(comodel_name='aas.quality.order', string=u'质检单', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    origin_order = fields.Char(string=u'来源单据', copy=False)
    current_label = fields.Boolean(string=u'新建标签', default=False, copy=False, help=u'由其他标签部分不合格品中拆分而来；如果为False说明那个标签全部不合格')
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)

    # 报检单据信息
    commit_id = fields.Integer(string=u'报检单据ID')
    commit_model = fields.Char(string=u'报检单据Model')
    commit_order = fields.Char(string=u'报检单据名称')

    _sql_constraints = [
        ('uniq_label', 'unique (order_id, label_id)', u'请不要重复添加同一个标签！')
    ]

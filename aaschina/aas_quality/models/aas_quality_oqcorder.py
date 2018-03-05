# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-3-5 09:59
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


OQCCHECKSTATES = [('draft', u'草稿'), ('confirm', u'确认'), ('checking', u'检验中'), ('done', u'完成')]

class AASQualityOQCOrder(models.Model):
    _name = 'aas.quality.oqcorder'
    _description = 'AAS Quality OQCOrder'

    name = fields.Char(string=u'名称', copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_qty = fields.Float(string=u'报检数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    commit_user = fields.Many2one('res.users', string=u'报检人员', ondelete='restrict', default=lambda self:self.env.user)
    commit_time = fields.Datetime(string=u'报检时间', default=fields.Datetime.now, copy=False)
    remark = fields.Text(string=u'备注', copy=False)
    state = fields.Selection(selection=OQCCHECKSTATES, string=u'状态', default='draft', copy=False)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    label_lines = fields.One2many(comodel_name='aas.quality.oqcorder.label', inverse_name='order_id', string=u'标签清单')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('aas.quality.oqcorder')
        return super(AASQualityOQCOrder, self).create(vals)


    @api.multi
    def action_oqccheck(self):
        """
        向导，触发此方法弹出向导并进行业务处理
        :return:
        """
        self.ensure_one()
        wizard = self.env['wizard.name'].create({})
        view_form = self.env.ref('moudle_name.view_name')
        return {
            'name': u"向导名称",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.name',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }

    @api.multi
    def unlink(self):
        for record in self:
            if record.state in ['checking', 'done']:
                raise UserError(u'OQC质检单%s已经在执行或已完成，不可以删除！'% record.name)
        return super(AASQualityOQCOrder, self).unlink()



class AASQualityOQCOrder(models.Model):
    _name = 'aas.quality.oqcorder.label'
    _description = 'AAS Quality OQCOrder Label'
    _rec_name = 'label_id'

    order_id = fields.Many2one(comodel_name='aas.quality.oqcorder', string='Order', ondelete='cascade', index=True)
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict', index=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    checked = fields.Boolean(string=u'是否检验', default=False, copy=False)
    checker_id = fields.Many2one(comodel_name='res.users', string=u'检验员', ondelete='restrict')
    checking_time = fields.Datetime(string=u'检验时间', copy=False)
    qualified = fields.Boolean(string=u'是否合格', default=False, copy=False)


    @api.one
    def action_checking(self, qualified=False):
        """OQC检测判定
        :param qualified:
        :return:
        """
        self.write({
            'checked': True, 'checker_id': self.env.user.id,
            'checking_time': fields.Datetime.now(), 'qualified': qualified
        })
        if qualified:
            self.label_id.write({'oqcpass': True})
        checkedcount, totalcount = 0, 0
        if self.order_id.label_lines and len(self.order_id.label_lines) > 0:
            totalcount = len(self.order_id.label_lines)
            for oqclabel in self.order_id.label_lines:
                if oqclabel.checked:
                    checkedcount += 1
        if checkedcount == 0:
            self.order_id.write({'state': 'confirm'})
        elif checkedcount < totalcount:
            self.order_id.write({'state': 'checking'})
        elif checkedcount == totalcount:
            self.order_id.write({'state': 'done'})










##################################向导Wizard#################################


class AASMESQualityOQCCheckingWizard(models.TransientModel):
    _name = 'aas.mes.quality.oqcchecking.wizard'
    _description = 'AAS MES Quality OQCChecking Wizard'

    oqcorder_id = fields.Many2one(comodel_name='aas.quality.oqcorder', string=u'检验单', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    commit_user = fields.Many2one(comodel_name='res.users', string=u'报检人员', ondelete='restrict')
    commit_time = fields.Datetime(string=u'报检时间', default=fields.Datetime.now, copy=False)

    label_lines = fields.One2many('aas.mes.quality.oqcchecking.label.wizard', inverse_name='wizard_id', string=u'标签清单')


class AASMESQualityOQCCheckingLabelWizard(models.TransientModel):
    _name = 'aas.mes.quality.oqcchecking.label.wizard'
    _description = 'AAS MES Quality OQCChecking Label Wizard'

    wizard_id = fields.Many2one('aas.mes.quality.oqcchecking.wizard', string='Wizard', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.quality.oqcorder.label', string=u'标签', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    qualified = fields.Boolean(string=u'是否合格', default=False, copy=False)
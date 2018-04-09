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

BACKSTATIONS = [('functiontest', u'功能测试'), ('finalchecking', u'最终检查'), ('gp12checking', u'GP12检查')]
OQCCHECKSTATES = [('draft', u'草稿'), ('confirm', u'确认'), ('checking', u'检验中'), ('done', u'完成')]

class AASQualityOQCOrder(models.Model):
    _name = 'aas.quality.oqcorder'
    _description = 'AAS Quality OQCOrder'
    _order = 'id desc'

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


    @api.one
    def action_confirm(self):
        if not self.label_lines or len(self.label_lines) <= 0:
            raise UserError(u'当前还未添加报检明细！')
        if self.state != 'draft':
            return
        ## 移动库存到出货区
        mainbase = self.env['stock.warehouse'].get_default_warehouse()
        outputlocation = mainbase.wh_output_stock_loc_id
        movedict, labelist = {}, self.env['aas.product.label']
        for oqclabel in self.label_lines:
            tlabel = oqclabel.label_id
            if tlabel.location_id.id == outputlocation.id:
                continue
            mkey = 'M-'+str(tlabel.product_lot.id)+'-'+str(tlabel.location_id.id)
            if mkey not in movedict:
                movedict[mkey] = {
                    'name': self.name,
                    'product_id': self.product_id.id,  'product_uom': self.product_uom.id,
                    'restrict_lot_id': tlabel.product_lot.id, 'product_uom_qty': tlabel.product_qty,
                    'location_id': tlabel.location_id.id, 'location_dest_id': outputlocation.id,
                    'create_date': fields.Datetime.now(), 'company_id': self.env.user.company_id.id
                }
            else:
                movedict[mkey]['product_uom_qty'] += tlabel.product_qty
            labelist |= tlabel
        if movedict and len(movedict) > 0:
            movelist = self.env['stock.move']
            for mkey, mval in movedict.items():
                movelist |= self.env['stock.move'].sudo().create(mval)
            movelist.sudo().action_done()
        if labelist and len(labelist) > 0:
            labelist.with_context({'operate_order': self.name}).write({'location_id': outputlocation.id})
        self.sudo().write({'state': 'confirm'})

    @api.multi
    def action_oqccheck(self):
        """
        OQC 出货检测
        :return:
        """
        self.ensure_one()
        if not self.label_lines or len(self.label_lines) <= 0:
            raise UserError(u'当前还未添加待检测标签！')
        labelids = [templabel.label_id.id for templabel in self.label_lines]
        tempdomain = [('label_id', 'in', labelids), ('isserialnumber', '=', True)]
        needback = True if self.env['aas.mes.production.label'].search_count(tempdomain) > 0 else False
        wizard = self.env['aas.quality.oqcchecking.wizard'].create({
            'oqcorder_id': self.id, 'product_id': self.product_id.id,
            'commit_user': self.commit_user.id, 'commit_time': self.commit_time, 'needback': needback
        })
        view_form = self.env.ref('aas_quality.view_form_aas_quality_oqcchecking_wizard')
        return {
            'name': u"OQC检测",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.quality.oqcchecking.wizard',
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



class AASQualityOQCOrderLabel(models.Model):
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
    backstation = fields.Selection(selection=BACKSTATIONS, string=u'回退站点', copy=False)


    @api.one
    def action_checking(self, qualified, backstation=False):
        self.write({
            'checked': True, 'qualified': qualified,
            'checking_time': fields.Datetime.now(), 'checker_id': self.env.user.id
        })
        self.label_id.write({'oqcpass': qualified})
        if not qualified and backstation:
            self.action_backlabel(self.label_id, backstation)


    @api.one
    def action_backlabel(self, label, backstation):
        if not label or not backstation:
            return
        productionlabel = self.env['aas.mes.production.label'].search([('label_id', '=', label.id)], limit=1)
        if not productionlabel or not productionlabel.isserialnumber:
            return
        serialnumberlist = self.env['aas.mes.serialnumber'].search([('label_id', '=', label.id)])
        serialnumberlist.sudo().write({
            'label_id': False, 'reworked': True,
            'reworksource': 'oqccehcking', 'badmode_name': u'OQC出货检测'
        })
        operationlist = self.env['aas.mes.operation']
        for tserialnumber in serialnumberlist:
            operationlist |= tserialnumber.operation_id
        operationvals = {'labeled': False, 'label_id': False}
        if backstation == 'functiontest':
            operationvals.update({
                'function_test': False, 'functiontest_record_id': False, 'final_quality_check': False,
                'fqccheck_record_id': False, 'fqccheck_date': False, 'gp12_check': False, 'gp12_date': False,
                'gp12_record_id': False, 'gp12_time': False
            })
        elif backstation == 'finalchecking':
            operationvals.update({
                'final_quality_check': False, 'fqccheck_record_id': False, 'fqccheck_date': False,
                'gp12_check': False, 'gp12_date': False, 'gp12_record_id': False, 'gp12_time': False
            })
        else:
            operationvals.update({
                'gp12_check': False, 'gp12_date': False, 'gp12_record_id': False, 'gp12_time': False
            })
        operationlist.sudo().write(operationvals)
        productionlabel.sudo().unlink()
        oqcorder = self.order_id.name
        pdtlocation = self.env.ref('stock.location_production')
        self.env['stock.move'].sudo().create({
            'name': oqcorder,
            'product_id': label.product_id.id,  'product_uom': label.product_uom.id,
            'restrict_lot_id': label.product_lot.id, 'product_uom_qty': label.product_qty,
            'location_id': label.location_id.id, 'location_dest_id': pdtlocation.id,
            'create_date': fields.Datetime.now(), 'company_id': self.env.user.company_id.id
        }).action_done()
        label.with_context({'operate_note': u'OQC: %s回退'% oqcorder}).write({'state': 'over', 'product_qty': 0.0})








##################################向导Wizard#################################


class AASQualityOQCCheckingWizard(models.TransientModel):
    _name = 'aas.quality.oqcchecking.wizard'
    _description = 'AAS Quality OQCChecking Wizard'

    oqcorder_id = fields.Many2one(comodel_name='aas.quality.oqcorder', string=u'检验单', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    commit_user = fields.Many2one(comodel_name='res.users', string=u'报检人员', ondelete='restrict')
    commit_time = fields.Datetime(string=u'报检时间', default=fields.Datetime.now, copy=False)
    needback = fields.Boolean(string=u'是否需要回退', default=False, copy=False)
    backstation = fields.Selection(selection=BACKSTATIONS, string=u'回退站点', copy=False)

    label_lines = fields.One2many('aas.quality.oqcchecking.label.wizard', inverse_name='checking_id', string=u'标签清单')

    @api.one
    def action_done(self):
        if not self.label_lines or len(self.label_lines) <= 0:
            raise UserError(u'请先添加检测标签信息！')
        for templabel in self.label_lines:
            oqclabel = templabel.label_id
            if templabel.qualified:
                oqclabel.action_checking(True)
            else:
                if not self.needback:
                    oqclabel.action_checking(False)
                elif self.backstation:
                    oqclabel.action_checking(False, backstation=self.backstation)
                else:
                    raise UserError(u'不合格标签需要指定回退站点！')
        oqcorder = self.oqcorder_id
        checkall = all([tlabel.checked for tlabel in oqcorder.label_lines])
        oqcorder.write({'state': 'checking' if not checkall else 'done'})






class AASQualityOQCCheckingLabelWizard(models.TransientModel):
    _name = 'aas.quality.oqcchecking.label.wizard'
    _description = 'AAS Quality OQCChecking Label Wizard'

    checking_id = fields.Many2one('aas.quality.oqcchecking.wizard', string='Wizard', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.quality.oqcorder.label', string=u'标签', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    qualified = fields.Boolean(string=u'是否合格', default=True, copy=False)

    @api.onchange('label_id')
    def action_change_label(self):
        checklabel = self.label_id
        if checklabel:
            self.product_id = checklabel.product_id.id
            self.product_lot, self.product_qty = checklabel.product_lot.id, checklabel.product_qty
        else:
            self.product_id, self.product_lot, self.product_qty = False, False, 0.0

    @api.model
    def create(self, vals):
        record = super(AASQualityOQCCheckingLabelWizard, self).create(vals)
        templabel = record.label_id
        record.write({
            'product_id': templabel.product_id.id,
            'product_lot': templabel.product_lot.id, 'product_qty': templabel.product_qty
        })
        return record
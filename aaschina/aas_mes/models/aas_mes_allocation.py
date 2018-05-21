# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-11-19 15:19
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

# 产线调拨
class AASMESAllocation(models.Model):
    _name = 'aas.mes.allocation'
    _description = 'AAS MES Allocation'
    _order = 'id desc'

    name = fields.Char(string=u'名称', copy=False)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    allotuser_id = fields.Many2one(comodel_name='res.users', string=u'调拨用户', rondelete='restrict')
    operator_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'操作员', ondelete='restrict')
    operation_time = fields.Datetime(string=u'操作时间', default=fields.Datetime.now, copy=False)
    state = fields.Selection(selection=[('draft', u'草稿'), ('done', u'完成')], string=u'状态', default='draft')
    company_id = fields.Many2one('res.company', string=u'公司', index=True, default=lambda self: self.env.user.company_id)
    allocation_lines = fields.One2many('aas.mes.allocation.line', inverse_name='allocation_id', string=u'调拨明细')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('aas.mes.allocation')
        return super(AASMESAllocation, self).create(vals)

    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(u'%s已经完成，不可以删除！'% record.name)
        return super(AASMESAllocation, self).unlink()


    @api.multi
    def action_operate(self):
        """
        调拨操作
        :return:
        """
        self.ensure_one()
        containnerids, containnerlines, labellines = [], [], []
        if self.allocation_lines and len(self.allocation_lines) > 0:
            for cline in self.allocation_lines:
                if cline.container_id and (cline.container_id.id not in containnerids):
                    productdict = {}
                    for cpline in cline.container_id.product_lines:
                        pkey = 'P'+str(cpline.product_id.id)
                        if pkey in productdict:
                            productdict[pkey]['product_qty'] += cpline.product_qty
                        else:
                            productdict[pkey] = {'product_code': cpline.product_id.default_code, 'product_qty': cpline.product_qty}
                    ccontext = ';'.join([pval['product_code']+':'+str(pval['product_qty']) for pval in productdict.values()])
                    containnerlines.append((0, 0, {'container_id': cline.container_id.id, 'container_context': ccontext}))
                if cline.label_id:
                    tlabel = cline.label_id
                    labellines.append((0, 0, {
                        'product_id': tlabel.product_id.id, 'product_lot': tlabel.product_lot.id,
                        'product_qty': tlabel.product_qty, 'label_id': tlabel.id, 'location_id': tlabel.location_id.id
                    }))
        allocatevals = {'allocation_id': self.id, 'mesline_id': self.mesline_id.id}
        if containnerlines and len(containnerlines) > 0:
            allocatevals['container_lines'] = containnerlines
        if labellines and len(labellines) > 0:
            allocatevals['label_lines'] = labellines
        wizard = self.env['aas.mes.allocation.wizard'].create(allocatevals)
        view_form = self.env.ref('aas_mes.view_form_aas_mes_allocation_wizard')
        return {
            'name': u"调拨操作",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.allocation.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }

    @api.one
    def action_done(self):
        if not self.allocation_lines or len(self.allocation_lines) <= 0:
            raise UserError(u'当前还未添加调拨明细，不可以结束调拨操作！')
        if not self.mesline_id.location_material_list or len(self.mesline_id.location_material_list) <= 0:
            raise UserError(u'产线%s还未设置原料库位！'% self.mesline_id.name)
        destlocation = self.mesline_id.location_material_list[0].location_id
        containerids, containerlist = [], self.env['aas.container']
        movedict, labellist = {}, self.env['aas.product.label']
        for aline in self.allocation_lines:
            if aline.container_id and (aline.container_id.id not in containerids):
                containerids.append(aline.container_id.id)
                containerlist |= aline.container_id
            alabel = aline.label_id
            if alabel:
                labellist |= alabel
                mkey = 'M-'+str(alabel.product_id.id)+'-'+str(alabel.product_lot.id)+'-'+str(alabel.location_id.id)
                if mkey in movedict:
                    movedict[mkey]['product_uom_qty'] += alabel.product_qty
                else:
                    movedict[mkey] = {
                        'name': self.name, 'product_id': alabel.product_id.id, 'product_uom': alabel.product_uom.id,
                        'create_date': fields.Datetime.now(), 'restrict_lot_id': alabel.product_lot.id,
                        'product_uom_qty': alabel.product_qty, 'location_id': alabel.location_id.id,
                        'location_dest_id': destlocation.id, 'company_id': self.env.user.company_id.id
                    }
        if movedict and len(movedict) > 0:
            movelist = self.env['stock.move']
            for mkey, mval in movedict.items():
                movelist |= self.env['stock.move'].create(mval)
            movelist.action_done()
        if containerlist and len(containerlist) > 0:
            containerlist.write({'location_id': destlocation.id})
        if labellist and len(labellist) > 0:
            labellist.write({'location_id': destlocation.id})
        self.write({'state': 'done'})


    @api.model
    def action_allocation(self, mesline_id, operator_id, containerids=[], labelids=[]):
        values = {'success': True, 'message': ''}
        productlines = []
        if containerids and len(containerids) > 0:
            containerlist = self.env['aas.container'].browse(containerids)
            for container in containerlist:
                if container.isempty:
                    continue
                for cpline in container.product_lines:
                    productlines.append((0, 0, {
                        'product_id': cpline.product_id.id, 'product_uom': cpline.product_id.uom_id.id,
                        'product_lot': cpline.product_lot.id, 'product_qty': cpline.product_qty,
                        'container_id': container.id, 'location_id': container.location_id.id
                    }))
        if labelids and len(labelids) > 0:
            labellist = self.env['aas.product.label'].browse(labelids)
            for tlabel in labellist:
                productlines.append((0, 0, {
                    'product_id': tlabel.product_id.id, 'product_uom': tlabel.product_uom.id,
                    'product_lot': tlabel.product_lot.id, 'product_qty': tlabel.product_qty,
                    'label_id': tlabel.id, 'location_id': tlabel.location_id.id
                }))
        self.env['aas.mes.allocation'].create({
            'mesline_id': mesline_id, 'operator_id': operator_id, 'allocation_lines': productlines
        }).action_done()
        return values


class AASMESAllocationLine(models.Model):
    _name = 'aas.mes.allocation.line'
    _description = 'AAS MES Allocation Line'

    allocation_id = fields.Many2one(comodel_name='aas.mes.allocation', string=u'调拨', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='restrict')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='restrict', index=True,
                                 default=lambda self: self.env.user.company_id)



# 向导

class AASMESAllocationWizard(models.TransientModel):
    _name = 'aas.mes.allocation.wizard'
    _description = 'AAS MES Allocation Wizard'

    allocation_id = fields.Many2one(comodel_name='aas.mes.allocation', string=u'调拨', ondelete='cascade')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade')
    container_lines = fields.One2many(comodel_name='aas.mes.allocation.container.wizard', inverse_name='wizard_id', string=u'容器明细')
    label_lines= fields.One2many(comodel_name='aas.mes.allocation.label.wizard', inverse_name='wizard_id', string=u'标签明细')

    @api.one
    def action_done(self):
        oldcontainerids, oldlabelids = [], []
        if self.allocation_id.allocation_lines and len(self.allocation_id.allocation_lines) > 0:
            for aline in self.allocation_id.allocation_lines:
                if aline.container_id and aline.container_id.id not in oldcontainerids:
                    oldcontainerids.append(aline.container_id.id)
                if aline.label_id and aline.label_id.id not in oldlabelids:
                    oldlabelids.append(aline.label_id.id)
        if self.container_lines and len(self.container_lines) > 0:
            for cline in self.container_lines:
                if cline.container_id.id in oldcontainerids:
                    oldcontainerids.remove(cline.container_id.id)
                else:
                    self.allocation_id.write({'allocation_lines': [(0, 0, {
                        'product_id': pline.product_id.id, 'product_uom': pline.product_id.uom_id.id,
                        'product_lot': pline.product_lot.id, 'product_qty': pline.product_qty,
                        'container_id': cline.container_id.id, 'location_id': cline.container_id.location_id.id
                    }) for pline in cline.container_id.product_lines]})
        if self.label_lines and len(self.label_lines) > 0:
            for lline in self.label_lines:
                tlabel = lline.label_id
                if tlabel.id in oldlabelids:
                    oldlabelids.remove(lline.label_id.id)
                else:
                    self.allocation_id.write({'allocation_lines': [(0, 0, {
                        'product_id': tlabel.product_id.id, 'product_uom': tlabel.product_uom.id,
                        'product_lot': tlabel.product_lot.id, 'product_qty': tlabel.product_qty,
                        'label_id': tlabel.id, 'location_id': tlabel.location_id.id
                    })]})
        if oldcontainerids and len(oldcontainerids) > 0:
            containerlist = self.env['aas.mes.allocation.line'].search([('container_id', 'in', oldcontainerids)])
            if containerlist and len(containerlist) > 0:
                containerlist.unlink()
        if oldlabelids and len(oldlabelids) > 0:
            labellist = self.env['aas.mes.allocation.line'].search([('label_id', 'in', oldlabelids)])
            if labellist and len(labellist) > 0:
                labellist.unlink()





class AASMESAllocationContainerWizard(models.TransientModel):
    _name = 'aas.mes.allocation.container.wizard'
    _description = 'AAS MES Allocation Container Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.mes.allocation.wizard', string='Wizard', ondelete='cascade')
    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='cascade')
    container_context = fields.Text(string=u'容器内容')

    _sql_constraints = [
        ('uniq_container', 'unique (wizard_id, container_id)', u'请不要重复添加同一个容器！')
    ]

    @api.onchange('container_id')
    def action_change_container(self):
        if not self.container_id:
            self.container_context = False
        else:
            productdict = {}
            for pline in self.container_id.product_lines:
                pkey = 'P'+str(pline.product_id.id)
                if pkey not in productdict:
                    productdict[pkey] = {'product_code': pline.product_id.default_code, 'product_qty': pline.product_qty}
                else:
                    productdict[pkey]['product_qty'] += pline.product_qty
            ccontext = ';'.join([pval['product_code']+':'+str(pval['product_qty']) for pval in productdict.values()])
            self.container_context = ccontext



class AASMESAllocationLabelWizard(models.TransientModel):
    _name = 'aas.mes.allocation.label.wizard'
    _description = 'AAS MES Allocation Label Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.mes.allocation.wizard', string='Wizard', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='cascade')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='cascade')

    _sql_constraints = [
        ('uniq_label', 'unique (wizard_id, label_id)', u'请不要重复添加同一个标签！')
    ]

    @api.onchange('label_id')
    def action_change_label(self):
        label = self.label_id
        if label:
            self.product_id, self.product_lot,  = label.product_id.id, label.product_lot.id
            self.product_qty, self.location_id = label.product_qty, label.location_id.id
        else:
            self.product_id, self.product_lot = False, False
            self.product_qty, self.location_id = 0.0, False

    @api.model
    def create(self, vals):
        record = super(AASMESAllocationLabelWizard, self).create(vals)
        label = record.label_id
        record.write({
            'product_id': label.product_id.id, 'product_lot': label.product_lot.id,
            'product_qty': label.product_qty, 'location_id': label.location_id.id
        })
        return record

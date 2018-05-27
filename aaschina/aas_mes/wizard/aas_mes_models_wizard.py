# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-8-21 13:31
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class AASMESEmployeeAllocateMESLineWizard(models.TransientModel):
    _name = 'aas.mes.employee.allocate.mesline.wizard'
    _description = 'AAS MES Employee Allocate MESLine Wizard'

    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', ondelete='cascade')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade')

    @api.one
    def action_done(self):
        tempvals = {'employee_id': self.employee_id.id}
        if self.mesline_id:
            tempvals['mesline_id'] = self.mesline_id.id
        self.env['aas.mes.line.employee'].create(tempvals)



class AASMESLineAllocateWizard(models.TransientModel):
    _name = 'aas.mes.line.allocate.wizard'
    _description = 'AAS MES Line Allocate Wizard'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade')
    employee_lines = fields.One2many(comodel_name='aas.mes.line.employee.allocate.wizard', inverse_name='wizard_id', string=u'员工清单')

    @api.one
    def action_done(self):
        if not self.employee_lines or len(self.employee_lines) <= 0:
            raise UserError(u'请先添加需要分配的员工！')
        for tempemployee in self.employee_lines:
            self.env['aas.mes.line.employee'].create({'mesline_id': self.mesline_id.id, 'employee_id': tempemployee.employee_id.id})


class AASMESLineEmployeeAllocateWizard(models.TransientModel):
    _name = 'aas.mes.line.employee.allocate.wizard'
    _description = 'AAS MES Line Employee Allocate Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.mes.line.allocate.wizard', string='Wizard', ondelete='cascade')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', ondelete='cascade')

    _sql_constraints = [
        ('uniq_employee', 'unique (wizard_id, employee_id)', u'请不要重复添加同一个员工！')
    ]


class AASMESFeedmaterialTransferWizard(models.TransientModel):
    _name = 'aas.mes.feedmaterial.transfer.wizard'
    __description = u'产线上料信息转移'


    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    srcline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'来源产线', ondelete='cascade')
    destline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'目标产线', ondelete='cascade')

    @api.one
    def action_done(self):
        if self.srcline_id.id == self.destline_id:
            raise UserError(u'来源产线和目标产线不可以相同！')
        if not self.srcline_id.location_material_list or len(self.srcline_id.location_material_list) <= 0:
            raise UserError(u'来源产线还未设置原料库位！')
        if not self.destline_id.location_material_list or len(self.destline_id.location_material_list) <= 0:
            raise UserError(u'目标产线还未设置原料库位！')
        srclocation = self.srcline_id.location_material_list[0].location_id
        destlocation = self.destline_id.location_material_list[0].location_id
        needstockmove = True if srclocation.id != destlocation.id else False
        materialids = self.env['aas.mes.bom'].action_load_consumematerialids(self.product_id.id)
        if not materialids or len(materialids) <= 0:
            raise UserError(u'当前产品无需转移上料信息')
        feedomain = [('mesline_id', '=', self.srcline_id.id), ('material_id', 'in', materialids)]
        feedmateriallines = self.env['aas.mes.feedmaterial'].search(feedomain)
        print feedmateriallines
        if not feedmateriallines or len(feedmateriallines) <= 0:
            raise UserError(u'上料信息可能已经消耗完毕，无需转移')
        feedmateriallist, dellist, movelines = self.env['aas.mes.feedmaterial'], self.env['aas.mes.feedmaterial'], []
        for feedmaterial in feedmateriallines:
            material, materialot = feedmaterial.material_id, feedmaterial.material_lot
            tempdomain = [('mesline_id', '=', self.destline_id.id)]
            tempdomain += [('material_id', '=', material.id), ('material_lot', '=', materialot.id)]
            tempfeedmaterial = self.env['aas.mes.feedmaterial'].search(tempdomain, limit=1)
            if not tempfeedmaterial:
                feedmateriallist |= feedmaterial
            else:
                dellist |= feedmaterial
            if needstockmove:
                movelines.append({
                    'name': u'上料信息转移产线', 'product_id': material.id, 'product_uom': material.uom_id.id,
                    'create_date': fields.Datetime.now(), 'company_id': self.env.user.company_id.id,
                    'restrict_lot_id': feedmaterial.material_lot.id, 'location_id': srclocation.id,
                    'location_dest_id': destlocation.id, 'product_uom_qty': feedmaterial.material_qty
                })
        if feedmateriallist and len(feedmateriallist) > 0:
            feedmateriallist.write({'mesline_id': self.destline_id.id})
        if dellist and len(dellist) > 0:
            dellist.unlink()
        if movelines and len(movelines) > 0:
            movelist = self.env['stock.move']
            for mline in movelines:
                movelist |= self.env['stcok.move'].create(mline)
            movelist.action_done()

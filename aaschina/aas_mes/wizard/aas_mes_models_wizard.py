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
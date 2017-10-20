# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-10-9 10:38
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

ROLELIST = [('gp12checker', u'GP12'), ('checker', u'考勤员'), ('serialnumber', u'序列号'), ('cutline', u'切线员'), ('fqcchecker', u'最终检查')]


# 产线关联账号
class AASMESLineusers(models.Model):
    _name = 'aas.mes.lineusers'
    _description = 'AAS MES Line Users'
    _rec_name = 'lineuser_id'

    lineuser_id = fields.Many2one(comodel_name='res.users', string=u'用户', ondelete='restrict')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')
    isfeeder = fields.Boolean(string=u'上料员', default=False, copy=False)
    mesrole = fields.Selection(selection=ROLELIST, string=u'角色', copy=False)

    _sql_constraints = [
        ('uniq_lineuser', 'unique (lineuser_id)', u'请不要重复添加同一个用户！')
    ]


    @api.model
    def create(self, vals):
        record = super(AASMESLineusers, self).create(vals)
        record.action_after_create()
        return record

    @api.one
    def action_after_create(self):
        uservals = {}
        if not self.lineuser_id.has_group('aas_mes.group_aas_manufacture_user'):
            uservals['groups_id'] = [(4, self.env.ref('aas_mes.group_aas_manufacture_user').id, False)]
        if self.mesrole:
            if self.mesrole == 'checker':
                uservals['action_id'] = self.env.ref('aas_mes.aas_mes_attendance_scanner').id
            if self.mesrole == 'serialnumber':
                uservals['action_id'] = self.env.ref('aas_mes.aas_mes_serialnumber_creation').id
            if self.mesrole == 'gp12checker':
                uservals['action_id'] = self.env.ref('aas_mes.aas_mes_gp12_checking').id
        if uservals and len(uservals) > 0:
            self.lineuser_id.write(uservals)



    @api.multi
    def write(self, vals):
        userlist = self.env['res.users']
        for record in self:
            userlist |= record.lineuser_id
        result = super(AASMESLineusers, self).write(vals)
        tempuserlist = self.env['res.users']
        for record in self:
            if not record.lineuser_id.has_group('aas_mes.group_aas_manufacture_user'):
                tempuserlist |= record.lineuser_id
        if tempuserlist and len(tempuserlist) > 0:
            tempuserlist.write({'groups_id': [(4, self.env.ref('aas_mes.group_aas_manufacture_user').id, False)]})
        uservals = {'action_id': False}
        role = vals.get('mesrole', False)
        if role:
            if role == 'checker':
                uservals['action_id'] = self.env.ref('aas_mes.aas_mes_attendance_scanner').id
            if role == 'serialnumber':
                uservals['action_id'] = self.env.ref('aas_mes.aas_mes_serialnumber_creation').id
            if role == 'gp12checker':
                uservals['action_id'] = self.env.ref('aas_mes.aas_mes_gp12_checking').id
        userlist.write(uservals)
        return result


    @api.multi
    def unlink(self):
        userlist = self.env['res.users']
        for record in self:
            userlist |= record.lineuser_id
        result = super(AASMESLineusers, self).unlink()
        userlist.write({'action_id': False})
        return result
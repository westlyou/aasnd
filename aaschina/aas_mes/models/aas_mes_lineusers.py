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

# 产线关联账号
class AASMESLineusers(models.Model):
    _name = 'aas.mes.lineusers'
    _description = 'AAS MES Line Users'
    _rec_name = 'lineuser_id'

    lineuser_id = fields.Many2one(comodel_name='res.users', string=u'用户', ondelete='restrict')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    ischecker = fields.Boolean(string=u'考勤员', default=False, copy=False)
    isforeman = fields.Boolean(string=u'领班', default=False, copy=False)


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
        if self.ischecker:
            uservals['action_id'] = self.env.ref('aas_mes.aas_mes_attendance_scanner').id
            uservals['groups_id'] = [(4, self.env.ref('aas_mes.group_aas_attendance_checker').id, False)]
        if self.isforeman:
            if uservals.get('groups_id', False):
                uservals['groups_id'].append((4, self.env.ref('aas_mes.group_aas_manufacture_foreman').id, False))
            else:
                uservals['groups_id'] = [(4, self.env.ref('aas_mes.group_aas_manufacture_foreman').id, False)]
        if uservals and  len(uservals) > 0:
            self.lineuser_id.write(uservals)



    @api.multi
    def write(self, vals):
        oldcheckers, oldforemen = self.env['res.users'], self.env['res.users']
        for record in self:
            if record.ischecker:
                oldcheckers |= record.lineuser_id
            if record.isforeman:
                oldforemen |= record.lineuser_id
        result = super(AASMESLineusers, self).write(vals)
        if oldcheckers and len(oldcheckers) > 0:
            oldcheckers.write({
                'action_id': False,
                'groups_id': [(3, self.env.ref('aas_mes.group_aas_attendance_checker').id, False)]
            })
        if oldforemen and len(oldforemen) > 0:
            oldforemen.write({
                'groups_id': [(3, self.env.ref('aas_mes.group_aas_manufacture_foreman').id, False)]
            })
        newcheckers, newforemen = self.env['res.users'], self.env['res.users']
        for trecord in self:
            if trecord.ischecker:
                newcheckers |= trecord.lineuser_id
            if trecord.isforeman:
                newforemen |= trecord.lineuser_id
        if newcheckers and len(newcheckers) > 0:
            newcheckers.write({
                'action_id': self.env.ref('aas_mes.aas_mes_attendance_scanner').id,
                'groups_id': [(4, self.env.ref('aas_mes.group_aas_attendance_checker').id, False)]
            })
        if newforemen and len(newforemen) > 0:
            newforemen.write({
                'groups_id': [(4, self.env.ref('aas_mes.group_aas_manufacture_foreman').id, False)]
            })
        return result


    @api.multi
    def unlink(self):
        checkers, foremen = self.env['res.users'], self.env['res.users']
        for record in self:
            if record.ischecker:
                checkers |= record.lineuser_id
            if record.isforeman:
                foremen |= record.lineuser_id
        result = super(AASMESLineusers, self).unlink()
        if checkers and len(checkers) > 0:
            checkers.write({
                'action_id': False,
                'groups_id': [(3, self.env.ref('aas_mes.group_aas_attendance_checker').id, False)]
            })
        if foremen and len(foremen) > 0:
            foremen.write({
               'groups_id': [(3, self.env.ref('aas_mes.group_aas_manufacture_foreman').id, False)]
            })
        return result
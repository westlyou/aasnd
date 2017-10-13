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
    isfeeder = fields.Boolean(string=u'上料员', default=False, copy=False)
    ischecker = fields.Boolean(string=u'考勤员', default=False, copy=False)
    isserialnumber = fields.Boolean(string=u'序列号', default=False, copy=False)



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
        if self.ischecker or self.isfeeder or self.isserialnumber:
            if not self.lineuser_id.has_group('aas_mes.group_aas_manufacture_user'):
                uservals['groups_id'] = [(4, self.env.ref('aas_mes.group_aas_manufacture_user').id, False)]
        if self.ischecker:
            uservals['action_id'] = self.env.ref('aas_mes.aas_mes_attendance_scanner').id
        if self.isserialnumber:
            uservals['action_id'] = self.env.ref('aas_mes.aas_mes_serialnumber_creation').id
        if uservals and len(uservals) > 0:
            self.lineuser_id.write(uservals)



    @api.multi
    def write(self, vals):
        userlist = self.env['res.users']
        for record in self:
            if record.ischecker or record.isserialnumber:
                userlist |= record.lineuser_id
        result = super(AASMESLineusers, self).write(vals)
        if userlist and len(userlist) > 0:
            userlist.write({'action_id': False})
        tempuserlist = self.env['res.users']
        newcheckers, newserialnumbers = self.env['res.users'], self.env['res.users']
        for record in self:
            if not record.lineuser_id.has_group('aas_mes.group_aas_manufacture_user'):
                tempuserlist |= record.lineuser_id
            if record.ischecker:
                newcheckers |= record.lineuser_id
            if record.isserialnumber:
                newserialnumbers |= record.lineuser_id
        if tempuserlist and len(tempuserlist) > 0:
            tempuserlist.write({'groups_id': [(4, self.env.ref('aas_mes.group_aas_manufacture_user').id, False)]})
        if newcheckers and len(newcheckers) > 0:
            newcheckers.write({'action_id': self.env.ref('aas_mes.aas_mes_attendance_scanner').id})
        if newserialnumbers and len(newserialnumbers) > 0:
            newcheckers.write({'action_id': self.env.ref('aas_mes.aas_mes_serialnumber_creation').id})
        return result


    @api.multi
    def unlink(self):
        userlist = self.env['res.users']
        for record in self:
            userlist |= record.lineuser_id
        result = super(AASMESLineusers, self).unlink()
        userlist.write({'action_id': False})
        return result
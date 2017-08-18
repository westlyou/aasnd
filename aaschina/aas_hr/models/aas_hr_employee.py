# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-8-17 21:18
"""

from odoo import api, fields, models, tools, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError
from odoo.modules.module import get_module_resource

import logging

_logger = logging.getLogger(__name__)

EMPLOYEESTATES = [('working', u'工作'), ('leave', u'离开'), ('atop', u'事假'), ('vacation', u'休假'), ('dimission', u'离职')]


class AASHREmployee(models.Model):
    _name = 'aas.hr.employee'
    _description = 'AAS HR Employee'

    @api.model
    def _default_image(self):
        image_path = get_module_resource('aas_hr', 'static/src/images', 'default_image.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))

    name = fields.Char(string=u'名称')
    code = fields.Char(string=u'工号')
    barcode = fields.Char(string=u'条码')
    leader_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'领导')
    login_user = fields.Many2one(comodel_name='res.users', string=u'登录账号')
    active = fields.Boolean(string=u'是否有效', default=True, copy=False)
    state = fields.Selection(selection=EMPLOYEESTATES, string=u'状态', default='leave', readonly=True)
    state_color = fields.Integer(string=u'状态颜色值', compute='_compute_state_color', store=True)
    birthday = fields.Date(string=u'生日', copy=False)
    identification_id = fields.Char(string=u'身份证号')
    gender = fields.Selection(selection=[('male', u'男'), ('female', u'女')], string=u'性别', default='male', copy=False)
    marital = fields.Selection([
        ('single', u'单身'), ('married', u'已婚'), ('divorced', u'离异'), ('widower', u'丧偶')
    ], string=u'婚姻状况', default='single')
    mobile_phone = fields.Char(string=u'手机号码')
    address_home = fields.Char(string=u'家庭住址', copy=False)
    work_phone = fields.Char(string=u'工作电话')
    work_email = fields.Char(string=u'工作邮箱')
    work_location = fields.Char(string=u'办公地址')
    company = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)


    image = fields.Binary("Photo", default=_default_image, attachment=True,
        help="This field holds the image used as photo for the employee, limited to 1024x1024px.")
    image_medium = fields.Binary("Medium-sized photo", attachment=True,
        help="Medium-sized photo of the employee. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved. "
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary("Small-sized photo", attachment=True,
        help="Small-sized photo of the employee. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")


    @api.depends('state')
    def _compute_state_color(self):
        statedict = {'working': 1, 'leave': 2, 'atop': 3, 'vacation': 4, 'dimission': 5}
        for record in self:
            record.state_color = statedict[record.state]

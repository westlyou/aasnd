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

GENDERS = [('male', u'男'), ('female', u'女')]
MARITALS = [('single', u'单身'), ('married', u'已婚'), ('other', u'其他')]

JOBS = [('worker', u'工人'), ('ipqc', 'IPQC')]

class AASHREmployee(models.Model):
    _name = 'aas.hr.employee'
    _description = 'AAS HR Employee'

    @api.model
    def _default_image(self):
        image_path = get_module_resource('aas_hr', 'static/src/images', 'default_image.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))

    name = fields.Char(string=u'名称', index=True)
    code = fields.Char(string=u'工号', index=True)
    barcode = fields.Char(string=u'条码', compute='_compute_barcode', store=True, index=True)
    leader_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'领导')
    login_user = fields.Many2one(comodel_name='res.users', string=u'登录账号')
    active = fields.Boolean(string=u'是否有效', default=True, copy=False)
    state = fields.Selection(selection=EMPLOYEESTATES, string=u'状态', default='leave', index=True, readonly=True)
    state_color = fields.Integer(string=u'状态颜色值', compute='_compute_state_color', store=True)
    birthday = fields.Date(string=u'生日', copy=False)
    identification_id = fields.Char(string=u'身份证号')
    gender = fields.Selection(selection=GENDERS, string=u'性别', default='male', copy=False)
    marital = fields.Selection(selection=MARITALS, string=u'婚姻状况', default='single', copy=False)
    mobile_phone = fields.Char(string=u'手机号码', copy=False)
    address_home = fields.Char(string=u'家庭住址', copy=False)
    work_phone = fields.Char(string=u'工作电话')
    work_email = fields.Char(string=u'工作邮箱')
    work_location = fields.Char(string=u'办公地址')
    entry_time = fields.Datetime(string=u'入职时间', default=fields.Datetime.now, copy=False)
    dimission_time = fields.Datetime(string=u'离职时间', copy=False)
    job = fields.Selection(selection=JOBS, string=u'岗位', copy=False, default='worker')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)


    image = fields.Binary("Photo", default=_default_image, attachment=True,
        help="This field holds the image used as photo for the employee, limited to 1024x1024px.")
    image_medium = fields.Binary("Medium-sized photo", attachment=True,
        help="Medium-sized photo of the employee. It is automatically resized as a 128x128px image, with aspect ratio preserved. "
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary("Small-sized photo", attachment=True,
        help="Small-sized photo of the employee. It is automatically resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")

    _sql_constraints = [
        ('uniq_code', 'unique (code)', u'员工工号不可以重复！')
    ]

    @api.multi
    def name_get(self):
        return [(record.id, '%s[%s]' % (record.name, record.code)) for record in self]

    @api.depends('state')
    def _compute_state_color(self):
        statedict = {'working': 1, 'leave': 2, 'atop': 3, 'vacation': 4, 'dimission': 5}
        for record in self:
            record.state_color = statedict[record.state]


    @api.multi
    @api.depends('code')
    def _compute_barcode(self):
        for record in self:
            record.barcode = 'AM'+record.code


    @api.model
    def action_print_label(self, printer_id, ids=[], domain=[]):
        values = {'success': True, 'message': ''}
        printer = self.env['aas.label.printer'].browse(printer_id)
        if not printer.field_lines or len(printer.field_lines) <= 0:
            values.update({'success': False, 'message': u'请联系管理员标签打印未指定具体打印内容！'})
            return values
        values.update({'printer': printer.name, 'serverurl': printer.serverurl})
        field_list = [fline.field_name for fline in printer.field_lines]
        if ids and len(ids) > 0:
            labeldomain = [('id', 'in', ids)]
        else:
            labeldomain = domain
        if not labeldomain or len(labeldomain) <= 0:
            return {'success': False, 'message': u'您可能已经选择了所有员工或未选择任何员工，请选中需要打印标签的员工！'}
        records = self.search_read(domain=labeldomain, fields=field_list)
        if not records or len(records) <= 0:
            values.update({'success': False, 'message': u'未搜索到需要打印的员工！'})
            return values
        records = printer.action_correct_records(records)
        values['records'] = records
        return values


    @api.multi
    def action_dimission(self):
        self.write({'dimission_time': fields.Datetime.now(), 'state': 'dimission', 'active': False})

    @api.multi
    def action_entry(self):
        self.write({'entry_time': fields.Datetime.now(), 'state': 'leave', 'active': True})

    @api.model
    def action_scanning(self, barcode):
        """扫描员工卡
        :param barcode:
        :return:
        """
        values = {'success': True, 'message': ''}
        if not barcode:
            values.update({'success': False, 'message': u'未获取到条码信息！'})
            return values
        temployee = self.env['aas.hr.employee'].search([('barcode', '=', barcode)], limit=1)
        if not temployee:
            values.update({'success': False, 'message': u'未获取到员工信息，请仔细核对条码信息！'})
            return values
        values.update({
            'eid': temployee.id, 'ename': temployee.name,
            'ecode': temployee.code, 'job': '' if not temployee.job else temployee.job
        })
        return values



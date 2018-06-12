# -*-  coding: utf-8 -*-

"""
@version: 2.0
@author: luforn
@license: LGPL V3
@time: 2017-12-12 13:57
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)




class AASMESSettings(models.TransientModel):
    _name = 'aas.mes.settings'
    _inherit = 'res.config.settings'


    default_worktime_min = fields.Float(string=u'最短工时', default=6.0, default_model='aas.mes.settings',
                                        help=u'最短在岗工时，满足此工时表明已完成正常的八小时工作制工时')
    default_worktime_max = fields.Float(string=u'最长工时', default=11.0, default_model='aas.mes.settings',
                                        help=u'最长在岗工时，满足此工时表明已完成正常工时和加班工时')
    default_worktime_standard = fields.Float(string=u'标准工时', default=8.0, default_model='aas.mes.settings',
                                             help=u'正常工作时数，超过则即为加班；默认为8小时')
    default_worktime_advance = fields.Float(string=u'提前工时', default=0.5, default_model='aas.mes.settings',
                                            help=u'提前班次开始时间段，在此时间段都默认为接下来的班次')
    default_worktime_delay = fields.Float(string=u'延迟工时', default=0.5, default_model='aas.mes.settings',
                                            help=u'延迟离岗时间')

    default_closeorder_method = fields.Selection(selection=[('total', u'实做总数与计划数相同即可结单'), ('equal', u'合格品数与计划数相同才可结单')],
                                                 string=u'结单方式', default='equal', copy=False, default_model='aas.mes.settings')


    @api.one
    @api.constrains('default_worktime_min', 'default_worktime_max', 'default_worktime_standard')
    def action_check_worktime(self):
        if not self.default_worktime_min and \
                        float_compare(self.default_worktime_min, 0.0, precision_rounding=0.000001) < 0.0:
            raise ValidationError(u"最短工时数不可以小于零！")
        if not self.default_worktime_max and \
                        float_compare(self.default_worktime_max, 0.0, precision_rounding=0.000001) < 0.0:
            raise ValidationError(u"最长工时数不可以小于零！")
        if not self.default_worktime_advance and \
                        float_compare(self.default_worktime_advance, 0.0, precision_rounding=0.000001) < 0.0:
            raise ValidationError(u"提前工时数不可以小于零！")
        if not self.default_worktime_standard and \
                        float_compare(self.default_worktime_standard, 0.0, precision_rounding=0.000001) < 0.0:
            raise ValidationError(u"标准工时数不可以小于零！")
        if self.default_worktime_min and self.default_worktime_standard and \
                        float_compare(self.default_worktime_min, self.default_worktime_standard, precision_rounding=0.000001) > 0.0:
            raise ValidationError(u'最短工时数不可以超过标准工时！')
        if self.default_worktime_standard and self.default_worktime_max and \
                        float_compare(self.default_worktime_standard, self.default_worktime_max, precision_rounding=0.000001) > 0.0:
            raise ValidationError(u'标准工时数不可以超过最长工时！')


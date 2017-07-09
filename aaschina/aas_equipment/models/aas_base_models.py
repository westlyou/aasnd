# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-9 15:20
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

class AASBaseCron(models.Model):
    _inherit = 'aas.base.cron'


    @api.model
    def action_hour_cron(self):
        super(AASBaseCron, self).action_hour_cron()
        # 将缓存中的设备数据存到PG中
        self.env['aas.equipment.data'].action_persist_data()





# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


DELIVERY_TYPE = [('manufacture', u'生产领料'), ('purchase', u'采购退货'), ('sales', u'销售发货'), ('sundry', u'杂项出库')]
DELIVERY_STATE = [('draft', u'草稿'), ('confirm', u'确认'), ('picking', u'拣货'), ('done', u'完成'), ('cancel', u'取消')]



class AASStockDelivery(models.Model):
    _name = 'aas.stock.delivery'
    _description = u'发货单'
    _order = 'id desc'



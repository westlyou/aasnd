# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-1-6 16:03
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


# 成品标签记录
class AASMESProductionLabel(models.Model):
    _name = 'aas.mes.production.label'
    _description = 'AAS MES Production Label'
    _rec_name = 'label_id'
    _order = 'id desc'

    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', index=True)
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', index=True)
    action_date = fields.Char(string=u'日期', copy=False, index=True)
    action_time = fields.Datetime(string=u'时间', default=fields.Datetime.now, copy=False)
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工')
    operator_id = fields.Many2one(comodel_name='res.users', string=u'用户')
    customer_code = fields.Char(string=u'客户编码', copy=False)
    product_code = fields.Char(string=u'产品编码', copy=False)
    lot_id = fields.Many2one(comodel_name='stock.production.lot', string=u'批次')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)


    @api.model
    def action_gp12_dolabel(self, product_id, productlot_id, product_qty, location_id, customer_code=False):
        label = self.env['aas.product.label'].create({
            'product_id': product_id, 'product_lot': productlot_id, 'product_qty': product_qty, 'stocked': True,
            'location_id': location_id, 'company_id': self.env.user.company_id.id, 'customer_code': customer_code
        })
        chinadate = fields.Datetime.to_china_string(fields.Datetime.now())[0:10]
        self.env['aas.mes.production.label'].create({
            'label_id': label.id, 'product_id': product_id,  'product_qty': product_qty,
            'lot_id': productlot_id, 'product_code': label.product_code, 'customer_code': customer_code,
            'operator_id': self.env.user.id, 'action_date': chinadate
        })
        return label


    @api.multi
    def action_show_serialnumbers(self):
        self.ensure_one()
        view_form = self.env.ref('aas_mes.view_form_aas_mes_serialnumber')
        view_tree = self.env.ref('aas_mes.view_tree_aas_mes_serialnumber')
        return {
            'name': u"成品清单",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'aas.mes.serialnumber',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'target': 'self',
            'context': self.env.context,
            'domain': "[('label_id','=',"+str(self.label_id.id)+")]"
        }
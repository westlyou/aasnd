# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-1-3 18:04
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class AASContainer(models.Model):
    _inherit = 'aas.container'

    @api.model
    def action_print_label(self, printer_id, ids=[], domain=[]):
        currentuser = self.env.user
        values = {'success': True, 'message': ''}
        if not currentuser.has_group('aas_mes.group_aas_manufacture_foreman'):
            values.update({'success': False, 'message': u'领班级别以上才可以打印容器二维码！'})
            return values
        values = super(AASContainer, self).action_print_label(printer_id, ids, domain)
        return values

    @api.multi
    def action_surplus(self):
        """
        容器添加余料
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.container.surplus.wizard'].create({'container_id': self.id})
        view_form = self.env.ref('aas_mes.view_form_aas_container_surplus_wizard')
        return {
            'name': u"容器添加余料",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.container.surplus.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }



# 添加余料到容器
class AASContainerSurplusWizard(models.TransientModel):
    _name = 'aas.container.surplus.wizard'
    _description = 'AAS Container Surplus Wizard'

    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器', ondelete='cascade')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='cascade')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)


    @api.one
    def action_done(self):
        if not self.product_qty or float_compare(self.product_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise UserError(u'请设置有效的余料数量！')
        container, product = self.container_id, self.product_id
        pdomain = [('container_id', '=', container.id)]
        pdomain += [('product_id', '=', product.id), ('product_lot', '=', self.product_lot.id)]
        pline = self.env['aas.container.product'].search(pdomain, limit=1)
        if pline:
            pline.write({'stock_qty': pline.stock_qty + self.product_qty})
        else:
            self.env['aas.container.product'].create({
                'container_id': container.id, 'product_id': product.id,
                'product_lot': self.product_lot.id, 'stock_qty': self.product_qty
            })
        srclocation = self.mesline_id.location_material_list[0].location_id
        destlocation = container.stock_location_id
        self.env['stock.move'].create({
            'name': container.name, 'product_id': product.id, 'product_uom': product.uom_id.id,
            'create_date': fields.Datetime.now(), 'company_id': self.env.user.company_id.id,
            'restrict_lot_id': self.product_lot.id, 'location_id': srclocation.id,
            'location_dest_id': destlocation.id, 'product_uom_qty': self.product_qty
        }).action_done()

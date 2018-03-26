# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-3-22 10:43
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import re
import logging

_logger = logging.getLogger(__name__)

class AASMaterialPlanner(models.Model):
    _name = 'aas.material.planner'
    _description = 'AAS Material Planner'
    _order = 'id desc'
    _rec_name = 'planner_email'

    planner_name = fields.Char(string=u'计划员', copy=False)
    planner_email = fields.Char(string=u'电子邮箱', copy=False)
    copy_emails = fields.Text(string=u'抄送邮箱', copy=False)

    costcenter_lines = fields.One2many(comodel_name='aas.material.costcenter', inverse_name='planner_id', string=u'成本中心')

    _sql_constraints = [
        ('uniq_email', 'unique (planner_email)', u'请不要重复添加同一个电子邮箱！')
    ]


    @api.one
    @api.constrains('planner_email')
    def action_check_constrains(self):
        if not self.planner_email:
            raise ValidationError(u"电子邮箱不可以为空！")
        if not re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", self.planner_email):
            raise ValidationError(u'请填写一个有效的电子邮箱账号！')

    @api.model
    def loading_inventory_information(self, product):
        values = {'success': True, 'email': '', 'notice': {}, 'copys': ''}
        if not product.costcenter or (not product.stockmin and not product.stockmax):
            values['success'] = False
            return values
        tempdomain = [('costcenter', '=', product.costcenter)]
        tcostcenter = self.env['aas.material.costcenter'].search(tempdomain, limit=1)
        if not tcostcenter:
            values['success'] = False
            return values
        currentinventory = self.env['product.product'].loading_current_inventory(product.id)
        if float_compare(currentinventory, 0.0, precision_rounding=0.000001) == 0.0:
            values['success'] = False
            return values
        tempgap = 0.0
        if float_compare(currentinventory, product.stockmin, precision_rounding=0.000001) < 0.0:
            tempgap = currentinventory - product.stockmin
        if float_compare(product.stockmax, 0.0, precision_rounding=0.000001) > 0.0 and \
                        float_compare(currentinventory, product.stockmax, precision_rounding=0.000001) > 0.0:
            tempgap = currentinventory - product.stockmax
        if float_compare(tempgap, 0.0, precision_rounding=0.000001) == 0.0:
            values['success'] = False
            return values
        values.update({
            'email': tcostcenter.planner_id.planner_email,
            'copys': tcostcenter.planner_id.copy_emails,
            'notice': {
                'product_code': product.default_code, 'product_name': product.name,
                'costcenter': product.costcenter, 'current_inventory': currentinventory,
                'stockmin': product.stockmin, 'stockmax': product.stockmax, 'stockgap': tempgap,
                'report_date': fields.Datetime.to_china_today()
            }
        })
        return values


    @api.model
    def action_send_emails(self, messages):
        if not messages or len(messages) <= 0:
            return
        mail_server = self.env['ir.mail_server'].sudo().search([('name', '=', 'System')], limit=1)
        if not mail_server:
            _logger.info(u'管理员还未配置名称为System的smtp服务器信息，请联系管理员配置！')
            return
        if not mail_server.smtp_user or not mail_server.smtp_pass:
            _logger.info(u"邮件发送账号未正确设置，请联系管理员！")
            return
        for email, tmessage in messages.items():
            mailvals = {
                'message_type': 'email', 'subject': 'Inventory Alert',
                'email_from': mail_server.smtp_user,  'email_to': email,
                'mail_server_id': mail_server.id
            }
            emailcc = tmessage.get('copys', False)
            if emailcc:
                mailvals['email_cc'] = emailcc
            bodyhtml = u"""
                Hi,
                    <p> Amphenol Inventory Alert </p>
                    <table border="1" cellspacing="0" cellpadding="0">
                        <tr style='border:1px solid #000000;'>
                            <td>Reporting date</td> <td>Part number</td> <td>Part description</td>
                            <td>Cost center</td> <td>Min inventory</td> <td>Max inventory</td>
                            <td>Current inventory</td> <td>GAP</td>
                        </tr>
            """
            for temproduct in tmessage['products']:
                items = [temproduct['report_date'], temproduct['product_code'], temproduct['product_name']]
                items += [temproduct['costcenter'], temproduct['stockmin'], temproduct['stockmax']]
                items += [temproduct['current_inventory'], temproduct['stockgap']]
                if float_compare(temproduct['stockgap'], 0.0, precision_rounding=0.000001) > 0.0:
                    bodyhtml += u"""<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td style='color:red'>%s</td> </tr>"""% tuple(items)
                else:
                    bodyhtml += u"""<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td style='color:blue'>%s</td> </tr>"""% tuple(items)
            bodyhtml += u""" </table> """
            mailvals['body_html'] = bodyhtml
            self.env['mail.mail'].create(mailvals).send(auto_commit=True)




class AASMaterialCostcenter(models.Model):
    _name = 'aas.material.costcenter'
    _description = 'AAS Material Costcenter'
    _order = 'id desc'

    planner_id = fields.Many2one(comodel_name='aas.material.planner', string=u'计划员', ondelete='cascade')
    costcenter = fields.Char(string=u'成本中心', required=True, copy=False)

    _sql_constraints = [
        ('uniq_email', 'unique (planner_email)', u'请不要重复添加同一个成本中心！')
    ]



class AASStockReceiptLine(models.Model):
    _inherit = "aas.stock.receipt.line"

    @api.one
    def action_confirm(self):
        super(AASStockReceiptLine, self).action_confirm()
        nmessages = {}
        tempvals = self.env['aas.material.planner'].loading_inventory_information(self.product_id)
        if not tempvals.get('success', False):
            return
        nmkey = tempvals['email']
        nmessages[nmkey] = {'copys': tempvals.get('copys', ''), 'products': [tempvals['notice']]}
        if nmessages and len(nmessages) > 0:
            self.env['aas.material.planner'].action_send_emails(nmessages)


class AASStockDeliveryLine(models.Model):
    _inherit = 'aas.stock.delivery.line'


    @api.one
    def action_deliver(self):
        super(AASStockDeliveryLine, self).action_deliver()
        nmessages = {}
        tempvals = self.env['aas.material.planner'].loading_inventory_information(self.product_id)
        if not tempvals.get('success', False):
            return
        nmkey = tempvals['email']
        nmessages[nmkey] = {'copys': tempvals.get('copys', ''), 'products': [tempvals['notice']]}
        if nmessages and len(nmessages) > 0:
            self.env['aas.material.planner'].action_send_emails(nmessages)
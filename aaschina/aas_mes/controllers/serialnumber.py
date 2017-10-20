# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-10-12 14:34
"""

import logging
import werkzeug

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)


class AASMESSerialnumberController(http.Controller):

    def checking_serialnumber_information(self):
        values = {
            'success': True, 'message': '', 'serial_count': 0,
            'customer_code': '', 'mesline_name': '', 'product_code': '',
            'serial_supplier': '2', 'serial_extend': '0', 'serial_type': '8', 'lastserialnumber': ''
        }
        isocalendar = fields.Datetime.to_timezone_time(fields.Datetime.now(), 'Asia/Shanghai').isocalendar()
        values['serial_year'] = str(isocalendar[0])[2:]
        values['serial_week'] = str(100+isocalendar[1])[1:]
        values['serial_weekday'] = str(isocalendar[2])
        login = request.env.user
        values['checker'] = login.name
        lineuser = request.env['aas.mes.lineusers'].search([('lineuser_id', '=', login.id)], limit=1)
        if not lineuser:
            values['success'] = False
            values['message'] = u'当前登录用户并非序列号创建用户；如果确实需要创建序列号，请联系领班为其配置权限！'
            return values
        if not lineuser.isserialnumber:
            values['success'] = False
            values['message'] = u'当前登录用户虽与产线绑定，但并未分配创建序列号权限；如果确实需要创建序列号，请联系领班为其配置权限！'
            return values
        values['mesline_name'] = lineuser.mesline_id.name
        workorder = lineuser.mesline_id.workorder_id
        if not workorder:
            values['success'] = False
            values['message'] = u'当前产线还未绑定需要生产的工单，请联系领班设置本产线需要生产的工单！'
            return values
        else:
            if workorder.product_id.customer_product_code:
                values.update({
                    'product_id': workorder.product_id.id, 'product_code': workorder.product_id.default_code,
                    'customer_code': workorder.product_id.customer_product_code
                })
            else:
                values['success'] = False
                values['message'] = u'产品%s还未设置客户方的编码，请联系领班设置客户编码！'% workorder.product_id.default_code
                return values
        regular_code = values['serial_supplier'] + values['serial_year'] + values['serial_week'] + values['serial_weekday']
        regular_code += values['serial_type'] + values['serial_extend']
        values['regular_code'] = regular_code
        serialdomain = [('regular_code', '=', regular_code)]
        maxserialnumber = request.env['aas.mes.serialnumber'].search(serialdomain, order='sequence desc', limit=1)
        if maxserialnumber:
            values['lastserialnumber'] = maxserialnumber.name
        values['serial_count'] = request.env['aas.mes.serialnumber'].search_count(serialdomain)
        return values

    @http.route('/aasmes/serialnumber', type='http', auth="user")
    def aasmes_serialnumber(self):
        values = self.checking_serialnumber_information()
        return request.render('aas_mes.aas_serialnumber_creation', values)




    @http.route('/aasmes/serialnumber/checkingmesline', type='json', auth="user")
    def aasmes_serialnumber_checkingmesline(self):
        return self.checking_serialnumber_information()


    @http.route('/aasmes/serialnumber/adddone', type='json', auth="user")
    def aasmes_serialnumber_addone(self, serialcount):
        values = self.checking_serialnumber_information()
        if not values['success']:
            return values
        regular_code = values.get('regular_code')
        serialdomain = [('regular_code', '=', regular_code)]
        maxserialnumber = request.env['aas.mes.serialnumber'].search(serialdomain, order='sequence desc', limit=1)
        if maxserialnumber:
            sequence = maxserialnumber.sequence
        else:
            sequence = 0
        if serialcount + sequence > 9999:
            values.update({'success': False, 'message': u'序列号已超出最大数9999，请确认调整后继续操作！'})
            return values
        serialnumbers = []
        customercode = values['customer_code'].replace('-', '')
        current_date = fields.Datetime.to_timezone_string(fields.Datetime.now(), 'Asia/Shanghai')[0:10]
        lastserialnumber = values['lastserialnumber']
        for index in range(0, serialcount):
            sequence += 1
            sequencestr = str(10000+sequence)[1:]
            sequence_code = regular_code + sequencestr
            temp_name = customercode + sequence_code
            tserialnumber = request.env['aas.mes.serialnumber'].create({
                'regular_code': regular_code, 'sequence': sequence,
                'sequence_code': sequence_code, 'name': temp_name,
                'action_date': current_date, 'product_id': values.get('product_id', False),
                'internal_product_code': values['product_code'], 'customer_product_code': values['customer_code']
            })

            serialnumbers.append({
                'serialid': tserialnumber.id,
                'serialname': tserialnumber.name,
                'sequencecode': tserialnumber.sequence_code,
                'product_code': tserialnumber.internal_product_code,
                'customer_code': tserialnumber.customer_product_code
            })
            lastserialnumber = tserialnumber.name
        values['serialnumbers'] = serialnumbers
        values['lastserialnumber'] = lastserialnumber
        values['serial_count'] = request.env['aas.mes.serialnumber'].search_count([('regular_code', '=', regular_code)])
        return values



    @http.route('/aasmes/serialnumber/loadingserialnumbers', type='json', auth="user")
    def aasmes_serialnumber_loadingserialnumbers(self, printerid, serialids):
        return request.env['aas.mes.serialnumber'].action_print_label(printerid, serialids)




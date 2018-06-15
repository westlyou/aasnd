# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-6-15 16:26
"""

import xlwt
import logging
from cStringIO import StringIO


from odoo import http, fields
from odoo.http import request
from odoo.tools.float_utils import float_compare, float_repr
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

class AASMESInventoryExportController(http.Controller):

    @http.route('/aasmes/inventory/export/<int:meslineid>/<int:firstinventoryid>/<int:lastinventoryid>', type='http', auth="user")
    def action_mes_inventory_export(self, meslineid, firstinventoryid, lastinventoryid):
        tempdomain = [('id', '>=', firstinventoryid), ('id', '<=', lastinventoryid), ('isproductionline', '=', True)]
        if meslineid:
            tempdomain.append(('mesline_id', '=', meslineid))
        inventorylist = request.env['aas.stock.inventory'].search(tempdomain)
        workbook = xlwt.Workbook(style_compression=2)
        worksheet = workbook.add_sheet(u'库存盘点')
        base_style = xlwt.easyxf('align: wrap yes')
        worksheet.write(0, 0, u'产线名称', base_style)
        worksheet.write(0, 1, u'盘点名称', base_style)
        worksheet.write(0, 2, u'盘点时间', base_style)
        worksheet.write(0, 3, u'盘点库位', base_style)
        worksheet.write(0, 4, u'盘点产品', base_style)
        worksheet.write(0, 5, u'客户料号', base_style)
        worksheet.write(0, 6, u'盘点批次', base_style)
        worksheet.write(0, 7, u'账存数量', base_style)
        worksheet.write(0, 8, u'实盘数量', base_style)
        worksheet.write(0, 9, u'差异数量', base_style)
        rowindex = 1
        if inventorylist and len(inventorylist) > 0:
            for tinventory in inventorylist:
                if not tinventory.inventory_lines or len(tinventory.inventory_lines) <= 0:
                    continue
                for invenline in tinventory.inventory_lines:
                    product = tinventory.product_id
                    customercode = '' if not product.customer_product_code else product.customer_product_code
                    worksheet.write(rowindex, 0, tinventory.mesline_id.name, base_style)
                    worksheet.write(rowindex, 1, tinventory.name, base_style)
                    worksheet.write(rowindex, 2, fields.Datetime.to_china_string(tinventory.create_time), base_style)
                    worksheet.write(rowindex, 3, invenline.location_id.name, base_style)
                    worksheet.write(rowindex, 4, product.default_code, base_style)
                    worksheet.write(rowindex, 5, customercode, base_style)
                    worksheet.write(rowindex, 6, invenline.product_lot.name, base_style)
                    worksheet.write(rowindex, 7, invenline.stock_qty, base_style)
                    worksheet.write(rowindex, 8, invenline.actual_qty, base_style)
                    worksheet.write(rowindex, 9, invenline.differ_qty, base_style)
                    rowindex += 1
        stream = StringIO()
        workbook.save(stream)
        outvalues = stream.getvalue()
        timestr = fields.Datetime.to_china_string(fields.Datetime.now())
        filename = 'Inventory %s'% timestr.replace('-', '').replace(':', '').replace(' ', '')
        xlshttpheaders = [
            ('Content-Type', 'application/vnd.ms-excel'), ('Content-Length', len(outvalues)),
            ('Content-Disposition', 'attachment; filename=%s.xls;'% filename)
        ]
        return request.make_response(outvalues, headers=xlshttpheaders)



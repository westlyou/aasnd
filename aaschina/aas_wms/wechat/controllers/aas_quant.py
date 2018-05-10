# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-21 10:39
"""

import logging
import werkzeug

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied,UserError,ValidationError

logger = logging.getLogger(__name__)


class AASStockQuantWechatController(http.Controller):

    @http.route('/aaswechat/wms/stocklist', type='http', auth="user")
    def aas_wechat_wms_stocklist(self, limit=20):
        values = request.params.copy()
        values.update({'stocklist': [], 'stockindex': 0})
        stocklist = request.env['aas.stock.quant.report'].search([('company_id', '=', request.env.user.company_id.id)], limit=limit)
        if stocklist and len(stocklist) > 0:
            values['stocklist'] = [{
                'product_id': tempstock.product_id.id, 'product_code': tempstock.product_id.default_code,
                'product_qty': tempstock.product_qty, 'location_id': tempstock.location_id.id,
                'location_name': tempstock.location_id.name, 'stock_id': tempstock.id
            } for tempstock in stocklist]
            values['stockindex'] = len(stocklist)
        return request.render('aas_wms.wechat_wms_stock_list', values)

    @http.route('/aaswechat/wms/stockmore', type='json', auth="user")
    def aas_wechat_wms_stockmore(self, stockindex=0, skey=None, limit=20):
        values = {'success': True, 'message': '', 'stocklist': [], 'stockindex': stockindex, 'stockcount': 0}
        companyid = request.env.user.company_id.id
        stockdomain = [('company_id', '=', companyid), ('location_id.usage', '=', 'internal')]
        if skey:
            searchdomain = ['|', ('product_code', 'ilike', '%'+skey+'%'), ('location_name', 'ilike', '%'+skey+'%')]
            stockdomain.insert(0, '&')
            stockdomain.extend(searchdomain)
        stocklist = request.env['aas.stock.quant.report'].search(stockdomain, offset=stockindex, limit=limit)
        if stocklist and len(stocklist) > 0:
            values['stocklist'] = [{
                'product_id': tempstock.product_id.id, 'product_code': tempstock.product_id.default_code,
                'product_qty': tempstock.product_qty, 'location_id': tempstock.location_id.id,
                'location_name': tempstock.location_id.name, 'stock_id': tempstock.id
            } for tempstock in stocklist]
            values['stockcount'] = len(stocklist)
            values['stockindex'] = values['stockcount'] + stockindex
        return values

    @http.route('/aaswechat/wms/stocksearch', type='json', auth="user")
    def aas_wechat_wms_stocksearch(self, skey=None, limit=20):
        values = {'success': True, 'message': '', 'stocklist': [], 'stockindex': 0}
        companyid = request.env.user.company_id.id
        stockdomain = [('company_id', '=', companyid), ('location_id.usage', '=', 'internal')]
        if skey:
            searchdomain = ['|', ('product_code', 'ilike', '%'+skey+'%'), ('location_name', 'ilike', '%'+skey+'%')]
            stockdomain.insert(0, '&')
            stockdomain.extend(searchdomain)
        stocklist = request.env['aas.stock.quant.report'].search(stockdomain, limit=limit)
        if stocklist and len(stocklist) > 0:
            values['stocklist'] = [{
                'product_id': tempstock.product_id.id, 'product_code': tempstock.product_id.default_code,
                'product_qty': tempstock.product_qty, 'location_id': tempstock.location_id.id,
                'location_name': tempstock.location_id.name, 'stock_id': tempstock.id
            } for tempstock in stocklist]
            values['stockindex'] = len(stocklist)
        return values


    @http.route('/aaswechat/wms/stockdetail/<int:stockid>', type='http', auth="user")
    def aas_wechat_wms_stockdetail(self, stockid):
        values = {'lotlist': []}
        tempstock = request.env['aas.stock.quant.report'].browse(stockid)
        values.update({
            'product_code': tempstock.product_id.default_code, 'product_qty': tempstock.product_qty,
            'location_name': tempstock.location_id.name
        })
        lotlist = request.env['stock.quant'].search([('product_id', '=', tempstock.product_id.id), ('location_id', '=', tempstock.location_id.id)])
        if lotlist and len(lotlist) > 0:
            values['lotlist'] = [{
               'lot_name': templot.lot_id.name, 'lot_qty': templot.qty
            } for templot in lotlist]
        return request.render('aas_wms.wechat_wms_stock_detail', values)





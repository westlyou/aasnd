# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-6-18 23:42
"""

import logging

from odoo import http, fields
from odoo.http import request

logger = logging.getLogger(__name__)

class AASTraceController(http.Controller):

    @http.route('/aastrace/serialnumber/forward/tracing/<int:productionid>', type='http', auth="user")
    def aastrace_serialnumber_forward_tracing(self, productionid):
        values = {'success': True, 'message': '', 'materiallist': []}
        login = request.env.user
        values['checker'] = login.name
        production = request.env['aas.production.product'].browse(productionid)
        values.update({
            'serialnumber': production.serialnumber_id.name,
            'product_code': production.product_id.default_code,
            'product_lot': False if not production.product_lot else production.product_lot.name
        })
        tvalues = request.env['aas.production.product.material.report'].action_serialnumber_forward_tracing(productionid)
        materiallines = tvalues.get('materiallist', [])
        if materiallines and len(materiallines) > 0:
            for material in materiallines:
                material['mid'] = 'material-'+str(material['material_id'])+'-'+str(material['material_lot'])
            values['materiallist'] = materiallines
        return request.render('aas_mes.aastrace_forword_material', values)

    @http.route('/aastrace/serialnumber/forward/allinone/<int:productionid>', type='http', auth="user")
    def aastrace_serialnumber_forward_allinone(self, productionid):
        values = request.env['aas.production.product.material.report'].action_serialnumber_forward_oneinall(productionid)
        production = request.env['aas.production.product'].browse(productionid)
        values.update({
            'serialnumber': production.serialnumber_id.name,
            'product_code': production.product_id.default_code,
            'product_lot': '' if not production.product_lot else production.product_lot.name
        })
        values['checker'] = request.env.user.name
        return request.render('aas_mes.aastrace_forword_allinone', values)


    @http.route('/aastrace/product/forward/tracing/<int:productid>/<int:prolotid>', type='http', auth="user")
    def aastrace_product_forward_tracing(self, productid, prolotid):
        values = {'success': True, 'message': '', 'materiallist': []}
        login = request.env.user
        values['checker'] = login.name
        productlot = request.env['stock.production.lot'].browse(prolotid)
        values.update({
            'serialnumber': '', 'product_lot': productlot.name,
            'product_code': productlot.product_id.default_code
        })
        tvalues = request.env['aas.production.product.material.report'].action_loading_materiallist(productid, prolotid)
        materiallines = tvalues.get('materiallist', [])
        if materiallines and len(materiallines) > 0:
            for material in materiallines:
                material['mid'] = 'material-'+str(material['material_id'])+'-'+str(material['material_lot'])
            values['materiallist'] = materiallines
        return request.render('aas_mes.aastrace_forword_material', values)


    @http.route('/aastrace/product/forward/allinone/<int:productid>/<int:prolotid>', type='http', auth="user")
    def aastrace_product_forward_allinone(self, productid, prolotid):
        values = request.env['aas.production.product.material.report'].action_product_forward_oneinall(productid, prolotid)
        productlot = request.env['stock.production.lot'].browse(prolotid)
        values.update({
            'serialnumber': '', 'product_lot': productlot.name,
            'product_code': productlot.product_id.default_code, 'checker': request.env.user.name
        })
        return request.render('aas_mes.aastrace_forword_allinone', values)


    @http.route('/aasmes/product/forward/loadingmaterialist', type='json', auth="user")
    def aastrace_product_forward_loadingmaterialist(self, productid, protlotid):
        values = {'success': True, 'message': '', 'materiallist': []}
        tvalues = request.env['aas.production.product.material.report'].action_loading_materiallist(productid, protlotid)
        materialines = tvalues.get('materiallist', '')
        if materialines and len(materialines) > 0:
            for material in materialines:
                material['mid'] = 'material-'+str(material['material_id'])+'-'+str(material['material_lot'])
            values['materiallist'] = materialines
        return values



    @http.route('/aastrace/material/reverse/tracing/<int:materialid>/<int:matllotid>', type='http', auth="user")
    def aastrace_material_reverse_tracing(self, materialid, matllotid):
        values = {'success': True, 'message': '', 'productlist': []}
        materiallot = request.env['stock.production.lot'].browse(matllotid)
        values.update({
            'material_lot': materiallot.name,
            'material_code': materiallot.product_id.default_code, 'checker': request.env.user.name
        })
        tvalues = request.env['aas.production.product.material.report'].action_loading_productlist(materialid, matllotid)
        templist = tvalues.get('productlist', [])
        if templist and len(templist) > 0:
            productlist = []
            for product in templist:
                if not product['product_lot']:
                    product['pid'] = 'product-'+str(product['product_id'])+'-0'
                else:
                    product['pid'] = 'product-'+str(product['product_id'])+'-'+str(product['product_lot'])
                productlist.append(product)
            values['productlist'] = productlist
        return request.render('aas_mes.aastrace_reverse_product', values)


    @http.route('/aastrace/material/reverse/allinone/<int:materialid>/<int:matllotid>', type='http', auth="user")
    def aastrace_material_reverse_allinone(self, materialid, matllotid):
        values = request.env['aas.production.product.material.report'].action_product_reverse_oneinall(materialid, matllotid)
        materiallot = request.env['stock.production.lot'].browse(matllotid)
        values.update({
            'material_lot': materiallot.name,
            'material_code': materiallot.product_id.default_code, 'checker': request.env.user.name
        })
        productlines = values.get('productlist', [])
        productlist, pkeys = [], []
        if productlines and len(productlines) > 0:
            for temproduct in productlines:
                pkey = 'P-'+str(temproduct['mesline_id'])+'-'+str(temproduct['product_id'])
                if temproduct['product_lot']:
                    pkey += '-'+str(temproduct['product_lot'])
                else:
                    pkey += '-0'
                if pkey in pkeys:
                    continue
                else:
                    pkeys.append(pkey)
                    productlist.append(temproduct)
        values['productlist'] = productlist
        return request.render('aas_mes.aastrace_reverse_allinone', values)


    @http.route('/aasmes/material/reverse/loadingproductlist', type='json', auth="user")
    def aastrace_material_reverse_loadingproductlist(self, materialid, matllotid):
        values = {'success': True, 'message': '', 'productlist': []}
        tvalues = request.env['aas.production.product.material.report'].action_loading_productlist(materialid, matllotid)
        productlines = tvalues.get('productlist', '')
        if productlines and len(productlines) > 0:
            productlist = []
            for product in productlines:
                if not product['product_lot']:
                    product['pid'] = 'product-'+str(product['product_id'])+'-0'
                else:
                    product['pid'] = 'product-'+str(product['product_id'])+'-'+str(product['product_lot'])
                productlist.append(product)
            values['productlist'] = productlist
        return values





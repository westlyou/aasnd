# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-9-22 15:56
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging
from odoo.tools.sql import drop_view_if_exists

_logger = logging.getLogger(__name__)


# 产出消耗报表
class AASProductionProductMaterialReport(models.Model):
    _auto = False
    _rec_name = 'product_id'
    _name = 'aas.production.product.material.report'
    _description = 'AAS Production Product Material Report'
    _order = 'mesline_id,product_id,product_lot,material_id,material_lot'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线')
    mesline_name = fields.Char(string=u'产线名称')
    product_id = fields.Many2one(comodel_name='product.product', string=u'成品')
    product_code = fields.Char(string=u'产品编码')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'成品批次')
    protlot_code = fields.Char(string=u'成品批次')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料')
    material_code = fields.Char(string=u'原料编码')
    material_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'原料批次')
    matllot_code = fields.Char(string=u'原料批次')

    def _select_sql(self):
        _select_sql = """
        SELECT MIN(pmaterial.id) AS id,
        pproduct.mesline_id AS mesline_id,
        pproduct.mesline_name AS mesline_name,
        pproduct.product_id AS product_id,
        pproduct.product_code AS product_code,
        pproduct.product_lot AS product_lot,
        pproduct.protlot_code AS protlot_code,
        pmaterial.material_id AS material_id,
        pmaterial.material_code AS material_code,
        pmaterial.material_lot AS material_lot,
        pmaterial.matllot_code AS matllot_code
        FROM aas_production_product pproduct join aas_production_material pmaterial on pproduct.id = pmaterial.production_id
        WHERE pproduct.tracing = true
        GROUP BY pproduct.mesline_id, pproduct.mesline_name, pproduct.product_id, pproduct.product_code,
        pproduct.product_lot, pproduct.protlot_code, pmaterial.material_id, pmaterial.material_code, pmaterial.material_lot, pmaterial.matllot_code
        """
        return _select_sql


    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (self._table, self._select_sql()))

    @api.model
    def action_serialnumber_forward_tracing(self, productionid):
        """根据序列号逐级追溯
        :param productionid:
        :return:
        """
        values = {'success': True, 'message': '', 'materiallist': []}
        production = self.env['aas.production.product'].browse(productionid)
        if not production:
            return values
        if production.material_lines and len(production.material_lines) > 0:
            values['materiallist'] = [{
                'mesline_id': production.mesline_id.id, 'mesline_name': production.mesline_id.name,
                'material_id': matline.material_id.id, 'material_code': matline.material_code,
                'material_lot': matline.material_lot.id, 'matllot_code': matline.matllot_code
            } for matline in production.material_lines]
        return values


    @api.model
    def action_serialnumber_forward_oneinall(self, productionid):
        """根据序列号已检追溯原材料
        :param productionid:
        :return:
        """
        values = {'success': True, 'message': '', 'materiallist': []}
        production = self.env['aas.production.product'].browse(productionid)
        if not production.material_lines or len(production.material_lines) <= 0:
            return values
        materiallist = []
        for matline in production.material_lines:
            meslineid, meslinename = production.mesline_id.id, production.mesline_id.name
            materialid, materialcode = matline.material_id.id, matline.material_code
            materiallotid, matllotcode = matline.material_lot.id, matline.matllot_code
            if matline.material_id.ismaterial:
                materiallist.append({
                    'mesline_id': meslineid, 'mesline_name': meslinename,
                    'material_id': materialid, 'material_code': materialcode,
                    'material_lot': materiallotid, 'matllot_code': matllotcode
                })
            else:
                materiallist += self.action_loading_oneinall_materiallist(materialid, materialcode, materiallotid,
                                                                          matllotcode, meslineid, meslinename)
        values['materiallist'] = materiallist
        return values

    @api.model
    def action_product_forward_oneinall(self, productid, protlotid):
        """根据成品信息已检追溯原材料
        :param productid:
        :param protlotid:
        :return:
        """
        values = {'success': True, 'message': '', 'materiallist': []}
        tempdomain = [('product_id', '=', productid), ('product_lot', '=', protlotid)]
        reportlist = self.env['aas.production.product.material.report'].search(tempdomain)
        if not reportlist or len(reportlist) <= 0:
            return values
        materiallist = []
        for report in reportlist:
            meslineid, meslinename = report.mesline_id.id, report.mesline_id.name
            materialid, materialcode = report.material_id.id, report.material_code
            materiallotid, matllotcode = report.material_lot.id, report.matllot_code
            if report.material_id.ismaterial:
                materiallist.append({
                    'mesline_id': meslineid, 'mesline_name': meslinename,
                    'material_id': materialid, 'material_code': materialcode,
                    'material_lot': materiallotid, 'matllot_code': matllotcode
                })
            else:
                materiallist += self.action_loading_oneinall_materiallist(materialid, materialcode, materiallotid,
                                                                          matllotcode, meslineid, meslinename)
        values['materiallist'] = materiallist
        return values



    @api.model
    def action_loading_oneinall_materiallist(self, productid, protcode, protlotid, lotcode, meslineid, meslinename):
        """递归获取最终原材料信息
        :param productid:
        :param protcode:
        :param protlotid:
        :param lotcode:
        :param meslineid:
        :param meslinename:
        :return:
        """
        materiallist = []
        sql_query = """
            SELECT mesline_id, mesline_name, material_id, material_code, material_lot, matllot_code
            FROM aas_production_product_material_report
            WHERE product_id = %s AND product_lot = %s
            """
        self.env.cr.execute(sql_query, (productid, protlotid))
        materials = self.env.cr.dictfetchall()
        if not materials or len(materials) <= 0:
            materiallist.append({
                'mesline_id': meslineid, 'mesline_name': meslinename,
                'material_id': productid, 'material_code': protcode,
                'material_lot': protlotid, 'matllot_code': lotcode
            })
        else:
            for material in materials:
                materialid, materialcode = material['material_id'], material['material_code']
                matllotid, matllotcode = material['material_lot'], material['matllot_code']
                meslineid, meslinename = material['mesline_id'], material['mesline_name']
                materiallist += self.action_loading_oneinall_materiallist(materialid, materialcode, matllotid,
                                                                          matllotcode, meslineid, meslinename)
        return materiallist


    @api.model
    def action_loading_materiallist(self, productid, protlotid):
        """根据成品批次信息后院原料批次信息
        :param productid:
        :param protlotid:
        :return:
        """
        values = {'success': True, 'message': '', 'materiallist': []}
        sql_query = """
            SELECT mesline_id, mesline_name, material_id, material_code, material_lot, matllot_code
            FROM aas_production_product_material_report
            WHERE product_id = %s AND product_lot = %s
            """
        self.env.cr.execute(sql_query, (productid, protlotid))
        materials = self.env.cr.dictfetchall()
        if materials and len(materials) > 0:
            values['materiallist'] = [{
                'mesline_id': material['mesline_id'], 'mesline_name': material['mesline_name'],
                'material_id': material['material_id'], 'material_code': material['material_code'],
                'material_lot': material['material_lot'], 'matllot_code': material['matllot_code']
            } for material in materials]
        return values



    @api.model
    def action_loading_productlist(self, materialid, matllotid):
        """根据原料批次获取成品批次信息
        :param materialid:
        :param matllotid:
        :return:
        """
        values = {'success': True, 'message': '', 'productlist': []}
        sql_query = """
            SELECT mesline_id, mesline_name, product_id, product_code, product_lot, protlot_code
            FROM aas_production_product_material_report
            WHERE material_id = %s AND material_lot = %s
            """
        self.env.cr.execute(sql_query, (materialid, matllotid))
        products = self.env.cr.dictfetchall()
        if products and len(products) > 0:
            values['productlist'] = [{
                'mesline_id': product['mesline_id'], 'mesline_name': product['mesline_name'],
                'product_id': product['product_id'], 'product_code': product['product_code'],
                'product_lot': product['product_lot'], 'protlot_code': product['protlot_code']
            } for product in products]
        return values


    @api.model
    def action_loading_oneinall_productlist(self, materialid, matlcode, matllotid, lotcode, meslineid, meslinename):
        """根据原料信息递归追溯成品信息
        :param materialid:
        :param matlcode:
        :param matllotid:
        :param lotcode:
        :param meslineid:
        :param meslinename:
        :return:
        """
        productlist = []
        sql_query = """
            SELECT mesline_id, mesline_name, product_id, product_code, product_lot, protlot_code
            FROM aas_production_product_material_report
            WHERE material_id = %s AND material_lot = %s
            """
        templotid = False if not matllotid else matllotid
        self.env.cr.execute(sql_query, (materialid, templotid))
        products = self.env.cr.dictfetchall()
        if not products or len(products) <= 0:
            productlist.append({
                'mesline_id': meslineid, 'mesline_name': meslinename,
                'product_id': materialid, 'material_code': matlcode,
                'product_lot': matllotid, 'protlot_code': lotcode
            })
        else:
            for product in products:
                productid, productcode = product['material_id'], product['material_code']
                protlotid, protlotcode = product['material_lot'], product['matllot_code']
                meslineid, meslinename = product['mesline_id'], product['mesline_name']
                productlist += self.action_loading_oneinall_productlist(productid, productcode, protlotid,
                                                                          protlotcode, meslineid, meslinename)
        return productlist


    @api.model
    def action_product_reverse_oneinall(self, materialid, matllotid):
        """根据原材料反向已检追溯成品
        :param materialid:
        :param matllotid:
        :return:
        """
        values = {'success': True, 'message': '', 'productlist': []}
        tempdomain = [('material_id', '=', materialid), ('material_lot', '=', matllotid)]
        reportlist = self.env['aas.production.product.material.report'].search(tempdomain)
        if not reportlist or len(reportlist) <= 0:
            return values
        productlist = []
        for report in reportlist:
            productid, productcode = report.product_id.id, report.product_code
            if report.product_lot:
                protlotid, protlotcode = report.product_lot.id, report.protlot_code
            else:
                protlotid, protlotcode = '', ''
            meslineid, meslinename = report.mesline_id.id, report.mesline_id.name
            productlist += self.action_loading_oneinall_productlist(productid, productcode, protlotid,
                                                                          protlotcode, meslineid, meslinename)
        return productlist












    @api.multi
    def action_trace_materialist(self):
        """原料追溯
        :return:
        """
        self.ensure_one()
        mdomain = [('product_id', '=', self.material_id.id), ('product_lot', '=', self.material_lot.id)]
        if self.env['aas.production.product.material.report'].search_count(mdomain) <= 0:
            raise UserError(u'当前没有原料信息可以追溯！')
        tempdomain = [('product_id', '=', self.material_id.id), ('product_lot', '=', self.material_lot.id)]
        view_form = self.env.ref('aas_mes.view_form_aas_production_product_material_report')
        view_tree = self.env.ref('aas_mes.view_tree_aas_production_product_material_report')
        return {
            'name': u"原料追溯",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'aas.production.product.material.report',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'target': 'self',
            'context': self.env.context,
            'domain': tempdomain
        }


    @api.multi
    def action_trace_productlist(self):
        """成品追溯
        :return:
        """
        self.ensure_one()
        pdomain = [('material_id', '=', self.product_id.id), ('material_lot', '=', self.product_lot.id)]
        if self.env['aas.production.product.material.report'].search_count(pdomain) <= 0:
            raise UserError(u'当前没有成品信息可以追溯！')
        tempdomain = [('material_id', '=', self.product_id.id), ('material_lot', '=', self.product_lot.id)]
        view_form = self.env.ref('aas_mes.view_form_aas_production_product_material_report')
        view_tree = self.env.ref('aas_mes.view_tree_aas_production_product_material_report')
        return {
            'name': u"成品追溯",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'aas.production.product.material.report',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'target': 'self',
            'context': self.env.context,
            'domain': tempdomain
        }


    @api.model
    def action_loading_productlist_oneinall(self, materialid, materialot, productkeys=[]):
        """递归获取最终成品批次集合
        :param materialid:
        :param materialot:
        :param productkeys:
        :return:
        """
        mdomain = [('material_id', '=', materialid), ('material_lot', '=', materialot)]
        reportlist = self.env['aas.production.product.material.report'].search(mdomain)
        if not reportlist or len(reportlist) <= 0:
            return
        for treport in reportlist:
            mesline = treport.mesline_id
            temproduct, templot = treport.product_id, treport.product_lot
            if templot:
                lotid = templot.id
            else:
                lotid = 0
            pkey = str(mesline.id)+'-'+str(temproduct.id)+'-'+str(lotid)
            if pkey in productkeys:
                continue
            tempdomain = [('material_id', '=', temproduct.id), ('material_lot', '=', templot.id)]
            templist = self.env['aas.production.product.material.report'].search(tempdomain)
            if not templist or len(templist) <= 0:
                productkeys.append(pkey)
                continue
            self.action_loading_productlist_oneinall(temproduct.id, templot.id, productkeys)





class AASProductionFinalProductReport(models.Model):
    _auto = False
    _rec_name = 'product_id'
    _name = 'aas.production.final.product.report'
    _description = 'AAS Production Final Product Report'
    _order = 'mesline_id,product_id,product_lot'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线')
    product_id = fields.Many2one(comodel_name='product.product', string=u'成品')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'成品批次')
    product_qty = fields.Float(string=u'成品数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    def _select_sql(self):
        _select_sql = """
        SELECT MIN(pproduct.id) AS id,
        pproduct.mesline_id AS mesline_id,
        pproduct.product_id AS product_id,
        pproduct.product_lot AS product_lot,
        sum(pproduct.product_qty) AS product_qty
        FROM aas_production_product pproduct
        WHERE pproduct.tracing = true
        GROUP BY pproduct.mesline_id, pproduct.product_id, pproduct.product_lot
        """
        return _select_sql


    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (self._table, self._select_sql()))



class AASProductionFinalMaterialReport(models.Model):
    _auto = False
    _rec_name = 'material_id'
    _name = 'aas.production.final.material.report'
    _description = 'AAS Production Final Material Report'
    _order = 'mesline_id,material_id,material_lot'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料')
    material_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'原料批次')
    material_qty = fields.Float(string=u'原料数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    def _select_sql(self):
        _select_sql = """
        SELECT MIN(pmaterial.id) AS id,
        pproduct.mesline_id AS mesline_id,
        pmaterial.material_id AS material_id,
        pmaterial.material_lot AS material_lot,
        sum(pmaterial.material_qty) AS material_qty
        FROM aas_production_product pproduct join aas_production_material pmaterial on pproduct.id = pmaterial.production_id
        WHERE pproduct.tracing = true
        GROUP BY pproduct.mesline_id, pmaterial.material_id, pmaterial.material_lot
        """
        return _select_sql


    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (self._table, self._select_sql()))




##########################向导###############################

class AASProductionForwardTracingWizard(models.TransientModel):
    _name = 'aas.production.forword.tracing.wizard'
    _description = 'AAS Production Forward Tracing Wizard'

    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号')
    product_id = fields.Many2one(comodel_name='product.product', string=u'成品')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次')


    @api.multi
    def action_tracing(self):
        self.ensure_one()
        if not self.serialnumber_id and (not self.product_id or not self.product_lot):
            raise UserError(u'如果未设置序列号，请设置好成品和批次信息！')
        tempdomain = []
        serialnumber, product, prolot = self.serialnumber_id, self.product_id, self.product_lot
        if serialnumber:
            mdomain = [('tracing', '=', True), ('serialnumber_id', '=', serialnumber.id)]
            production = self.env['aas.production.product'].search(mdomain, limit=1)
            if not production or not production.material_lines or len(production.material_lines) <= 0:
                raise UserError(u'未获取到追溯信息！')
            reportids = []
            meslineid, productid = production.mesline_id.id, production.product_id.id
            productlot = False if not production.product_lot else production.product_lot.id
            for mline in production.material_lines:
                pmdomain = [('mesline_id', '=', meslineid)]
                pmdomain += [('product_id', '=', productid), ('product_lot', '=', productlot)]
                pmdomain += [('material_id', '=', mline.material_id.id), ('material_lot', '=', mline.material_lot.id)]
                pmreport = self.env['aas.production.product.material.report'].search(pmdomain, limit=1)
                if not pmreport:
                    continue
                reportids.append(pmreport.id)
            tempdomain += [('id', 'in', reportids)]
        else:
            tempdomain += [('product_id', '=', product.id), ('product_lot', '=', prolot.id)]
        action = self.env.ref('aas_mes.action_aas_production_product_material_report').read()[0]
        action['domain'] = tempdomain
        return action

    @api.multi
    def action_trace_oneinall(self):
        """最终原料追溯
        :return:
        """
        self.ensure_one()
        if not self.serialnumber_id and (not self.product_id or not self.product_lot):
            raise UserError(u'如果未设置序列号，请设置好成品和批次信息！')
        serialnumber, product, prolot = self.serialnumber_id, self.product_id, self.product_lot
        tempdomain = [('tracing', '=', True)]
        if serialnumber:
            tempdomain.append(('serialnumber_id', '=', serialnumber.id))
        else:
            tempdomain += [('product_id', '=', product.id), ('product_lot', '=', prolot.id)]
        productionlist = self.env['aas.production.product'].search(tempdomain)
        if not productionlist or len(productionlist) <= 0:
            raise UserError(u'未获取到追溯信息！')
        productkeys, materialkeys = [], []
        for pproduction in productionlist:
            self.env['aas.production.product'].action_loading_materialist_oneinall(pproduction, productkeys, materialkeys)
        if not materialkeys or len(materialkeys) <= 0:
            raise UserError(u'未获取到相关追溯信息！')
        finalmaterialids = []
        for mkey in materialkeys:
            tkeys = mkey.split('-')
            mlid, mtid, mlot = int(tkeys[0]), int(tkeys[1]), int(tkeys[2])
            mdomain = [('mesline_id', '=', mlid), ('material_id', '=', mtid), ('material_lot', '=', mlot)]
            finalmaterial = self.env['aas.production.final.material.report'].search(mdomain, limit=1)
            if finalmaterial:
                finalmaterialids.append(finalmaterial.id)
        action = self.env.ref('aas_mes.action_aas_production_final_material_report').read()[0]
        action['domain'] = [('id', 'in', finalmaterialids)]
        return action






class AASProductionReverseTracingWizard(models.TransientModel):
    _name = 'aas.production.reverse.tracing.wizard'
    _description = 'AAS Production Reverse Tracing Wizard'

    material_id = fields.Many2one(comodel_name='product.product', string=u'原料')
    material_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次')

    @api.multi
    def action_tracing(self):
        self.ensure_one()
        tempdomain = [('material_id', '=', self.material_id.id), ('material_lot', '=', self.material_lot.id)]
        action = self.env.ref('aas_mes.action_aas_production_product_material_report').read()[0]
        action['domain'] = tempdomain
        return action


    @api.multi
    def action_trace_oneinall(self):
        """最终成品追溯
        :return:
        """
        self.ensure_one()
        materialid, materialot, productkeys = self.material_id.id, self.material_lot.id, []
        self.env['aas.production.product.material.report'].action_loading_productlist_oneinall(materialid, materialot,
                                                                                               productkeys)
        if not productkeys or len(productkeys) <= 0:
            raise UserError(u"未获取到相关追溯信息")
        finalproductids = []
        for pkey in productkeys:
            keys = pkey.split('-')
            mlid, ptid, plot = int(keys[0]), int(keys[1]), int(keys[2])
            if not plot:
                plot = False
            pdomain = [('mesline_id', '=', mlid), ('product_id', '=', ptid), ('product_lot', '=', plot)]
            temproduct = self.env['aas.production.final.product.report'].search(pdomain, limit=1)
            if temproduct:
                finalproductids.append(temproduct.id)
        if not finalproductids or len(finalproductids) <= 0:
            raise UserError(u'未获取到相关追溯信息！')
        action = self.env.ref('aas_mes.action_aas_production_final_product_report').read()[0]
        action['domain'] = [('id', 'in', finalproductids)]
        return action



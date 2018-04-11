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
    product_id = fields.Many2one(comodel_name='product.product', string=u'成品')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'成品批次')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料')
    material_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'原料批次')

    def _select_sql(self):
        _select_sql = """
        SELECT MIN(pmaterial.id) AS id,
        pproduct.mesline_id AS mesline_id,
        pproduct.product_id AS product_id,
        pproduct.product_lot AS product_lot,
        pmaterial.material_id AS material_id,
        pmaterial.material_lot AS material_lot
        FROM aas_production_product pproduct join aas_production_material pmaterial on pproduct.id = pmaterial.production_id
        WHERE pproduct.tracing = true
        GROUP BY pproduct.mesline_id, pproduct.product_id, pproduct.product_lot, pmaterial.material_id, pmaterial.material_lot
        """
        return _select_sql


    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s )""" % (self._table, self._select_sql()))


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



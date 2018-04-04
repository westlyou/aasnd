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
    def action_loading_materialist_oneinall(self, productid, productlot):
        """递归获取最终原料批次信息id集合
        :param productid:
        :param productlot:
        :return:
        """
        materialreportids = []
        tempdomain = [('product_id', '=', productid), ('product_lot', '=', productlot)]
        reportlist = self.env['aas.production.product.material.report'].search(tempdomain)
        if not reportlist or len(reportlist) <= 0:
            return materialreportids
        for treport in reportlist:
            tmesline = treport.mesline_id
            mateiral, materialot = treport.material_id, treport.material_lot
            if mateiral.ismaterial:
                mdomain = [('mesline_id', '=', tmesline.id)]
                mdomain += [('mateiral_id', '=', mateiral.id), ('material_lot', '=', materialot.id)]
                finalmaterial = self.env['aas.production.final.material.report'].search(mdomain, limit=1)
                if finalmaterial:
                    materialreportids.append(finalmaterial.id)
            else:
                materialreportids += self.action_loading_materialist_oneinall(mateiral.id, materialot.id)
        return materialreportids


    @api.model
    def action_loading_productlist_oneinall(self, materialid, materialot):
        """递归获取最终成品批次id集合
        :param materialid:
        :param materialot:
        :return:
        """
        productreportids = []
        mdomain = [('material_id', '=', materialid), ('material_lot', '=', materialot)]
        reportlist = self.env['aas.production.product.material.report'].search(mdomain)
        if not reportlist or len(reportlist) <= 0:
            return productreportids
        for treport in reportlist:
            mesline = treport.mesline_id
            temproduct, templot = treport.product_id, treport.product_lot
            tempdomain = [('material_id', '=', temproduct.id), ('material_lot', '=', templot.id)]
            if self.env['aas.production.product.material.report'].search_count(tempdomain) <= 0:
                rdomain = [('mesline_id', '=', mesline.id)]
                rdomain += [('product_id', '=', temproduct.id), ('product_lot', '=', templot.id)]
                preport = self.env['aas.production.final.product.report'].search(rdomain, limit=1)
                if preport:
                    productreportids.append(preport.id)
            else:
                productreportids += self.action_loading_productlist_oneinall(temproduct.id, templot.id)
        return productreportids





class AASProductionFinalProductReport(models.Model):
    _auto = False
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
            mesline = serialnumber.mesline_id
            tproduct, tprolot = serialnumber.product_id, serialnumber.product_lot
            tempdomain += [('mesline_id', '=', mesline.id), ('product_id', '=', tproduct.id)]
            if tprolot:
                tempdomain += [('product_lot', '=', tprolot.id)]
            else:
                tempdomain += [('product_lot', '=', False)]
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
        finalmaterialids = []
        for pproduction in productionlist:
            if not pproduction.material_lines or len(pproduction.material_lines) <= 0:
                continue
            for pmaterial in pproduction.material_lines:
                materialid, materialotid = pmaterial.material_id.id, pmaterial.material_lot.id
                tempids = self.env['aas.production.product.material.report'].action_loading_materialist_oneinall(
                    materialid, materialotid)
                finalmaterialids += tempids
        if not finalmaterialids or len(finalmaterialids) <= 0:
            raise UserError(u'未获取到相关追溯信息！')
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
        finalproductids = self.env['aas.production.product.material.report'].action_loading_productlist_oneinall(
            self.material_id.id, self.material_lot.id)
        if not finalproductids or len(finalproductids) <= 0:
            raise UserError(u'未获取到相关追溯信息！')
        action = self.env.ref('aas_mes.action_aas_production_final_product_report').read()[0]
        action['domain'] = [('id', 'in', finalproductids)]
        return action



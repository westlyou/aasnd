# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError, ValidationError
from odoo.tools.sql import drop_view_if_exists

import logging
_logger = logging.getLogger(__name__)


class Warehouse(models.Model):
    _inherit = 'stock.warehouse'


    @api.model
    def create(self, vals):
        warehouse = super(Warehouse, self).create(vals)
        warehouse.action_after_create()
        return warehouse

    @api.one
    def action_after_create(self):
        locations = self.env['stock.location']
        locations |= self.wh_input_stock_loc_id
        locations |= self.wh_output_stock_loc_id
        locations.write({'active': True})

    @api.model
    def action_upgrade_aas_stock_warehouse(self):
        warehouses = self.env['stock.warehouse'].search([])
        if not warehouses or len(warehouses) <= 0:
            return
        for warehouse in warehouses:
            warehouse.action_after_create()

    @api.model
    def get_default_warehouse(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], order='id', limit=1)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    need_warranty = fields.Boolean(string=u'质保期', default=False, help=u"收货时是否需要设置质保期")
    stock_age = fields.Integer(string=u"库龄", default=0, help=u'物料在仓库保存时间，超过时间要给出提醒')
    push_location = fields.Many2one(comodel_name='stock.location', string=u'推荐库位', help=u'最近上架库位')
    virtual_material = fields.Boolean(string=u'虚拟物料', default=False, copy=False)
    split_qty = fields.Float(string=u'拆分批次数量', digits=dp.get_precision('Product Unit of Measure'), help=u'主工单拆分成子工单，子工单的生产数量')
    product_yield = fields.Float(string=u'良率', digits=dp.get_precision('Product Unit of Measure'), default=1.0)
    weld_count = fields.Integer(string=u'焊接次数', default=1)
    customer_product_code = fields.Char(string=u'客户料号', copy=False, help=u'产品在客户方的料号')

    _sql_constraints = [
        ('uniq_defaultcode', 'unique(default_code)', u'产品料号不可以重复！')
    ]

    @api.one
    @api.constrains('split_qty', 'product_yield')
    def action_check_template(self):
        if self.split_qty and float_compare(self.split_qty, 0.0, precision_rounding=0.000001) < 0.0:
            raise ValidationError(u'拆分批次必须是一个大于零的正数！')
        if self.product_yield and (float_compare(self.product_yield, 0.0, precision_rounding=0.000001) <= 0.0 or
                                           float_compare(self.product_yield, 1.0, precision_rounding=0.000001) > 0.0):
            raise ValidationError(u'良率必须是一个介于0到1之间的数但不包含0！')

    @api.onchange('uom_id')
    def action_change_uom(self):
        self.uom_po_id = self.uom_id.id





class AASProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def name_get(self):
        if len(self) <= 0:
            return []
        return [(record.id, record.default_code) for record in self]


class Location(models.Model):
    _inherit = 'stock.location'

    mrblocation = fields.Boolean(string=u'MRB库位', default=False, copy=False)
    edgelocation = fields.Boolean(string=u'生产线边库', default=False, copy=False)
    usage = fields.Selection(selection_add=[('sundry', u'杂项'), ('container', u'容器')])
    container_id = fields.Many2one(comodel_name='aas.container', string=u'容器')

    @api.one
    @api.constrains('location_id')
    def action_check_location(self):
        if self.location_id and self.location_id.usage == 'container':
            raise ValidationError(u'容器库位下不可以添加子库位！')

    @api.model
    def create(self, vals):
        if vals.get('name', False):
            vals['barcode'] = 'AA'+vals.get('name')
        if vals.get('location_id', False):
            parentlocation = self.env['stock.location'].browse(vals.get('location_id'))
            vals.update({'mrblocation': parentlocation.mrblocation, 'edgelocation': parentlocation.edgelocation})
        return super(Location, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('name', False):
            vals['barcode'] = 'AA'+vals.get('name')
        if vals.get('location_id', False):
            parentlocation = self.env['stock.location'].browse(vals.get('location_id'))
            vals.update({'mrblocation': parentlocation.mrblocation, 'edgelocation': parentlocation.edgelocation})
        return super(Location, self).write(vals)



    @api.model
    def action_print_label(self, printer_id, ids=[], domain=[]):
        values = {'success': True, 'message': ''}
        printer = self.env['aas.label.printer'].browse(printer_id)
        if not printer.field_lines or len(printer.field_lines) <= 0:
            values.update({'success': False, 'message': u'请联系管理员标签打印未指定具体打印内容！'})
            return values
        values.update({'printer': printer.name, 'serverurl': printer.serverurl})
        field_list = [fline.field_name for fline in printer.field_lines]
        if ids and len(ids) > 0:
            locationdomain = [('id', 'in', ids)]
        else:
            locationdomain = domain
        records = self.search_read(domain=locationdomain, fields=field_list)
        if not records or len(records) <= 0:
            values.update({'success': False, 'message': u'未搜索到需要打印的标签！'})
            return values
        records = printer.action_correct_records(records)
        values['records'] = records
        return values

    @api.multi
    def action_stocklist(self):
        self.ensure_one()
        quantlist = self.env['stock.quant'].search([('location_id', 'child_of', self.id), ('qty', '!=', 0.0)])
        if not quantlist or len(quantlist) <= 0:
            raise UserError(u'当前库位下还未存放任何物品！')
        quantidsstr = ','.join([str(qid) for qid in quantlist.ids])
        view_tree = self.env.ref('aas_wms.view_tree_stock_quant_location')
        view_form = self.env.ref('aas_wms.view_form_stock_quant_location')
        return {
            'name': u"库存清单",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.quant',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'target': 'self',
            'context': self.env.context,
            'domain': "[('id','in',("+quantidsstr+"))]"
        }



class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    @api.model
    def action_checkout_lot(self, product_id, lot_name):
        """
        获取批次信息；如果系统中不存在则立即新建一个
        :param product_id:
        :param lot_name:
        :return:
        """
        stocklot = self.env['stock.production.lot'].search([('product_id', '=', product_id), ('name', '=', lot_name)], limit=1)
        if not stocklot:
            stocklot = self.env['stock.production.lot'].create({
                'name': lot_name, 'product_id': product_id, 'create_date': fields.Datetime.now()
            })
        return stocklot




class StockQuant(models.Model):
    _inherit = 'stock.quant'

    product_code = fields.Char(string=u'产品编码')
    location_name = fields.Char(string=u'库位名称')

    @api.model
    def create(self, vals):
        record = super(StockQuant, self).create(vals)
        record.write({'product_code': record.product_id.default_code, 'location_name': record.location_id.name})
        return record

    @api.multi
    def write(self, vals):
        if vals.get('product_id'):
            product = self.env['product.product'].browse(vals.get('product_id'))
            vals['product_code'] = product.default_code
        if vals.get('location_id'):
            location = self.env['stock.location'].browse(vals.get('location_id'))
            vals['location_name'] = location.name
        return super(StockQuant, self).write(vals)


class AASStockQuantReport(models.Model):
    _auto = False
    _name = 'aas.stock.quant.report'
    _description = u'库存报表'

    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', readonly=True)
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', related='product_id.uom_id', readonly=True)
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), readonly=True)
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位',  readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', readonly=True)
    product_code = fields.Char(string=u'产品编码', readonly=True)
    location_name = fields.Char(string=u'库位名称', readonly=True)


    def _select(self):
        select_str = """
        SELECT min(asq.id) as id,
        asq.product_id as product_id,
        sum(asq.qty) as product_qty,
        asq.company_id as company_id,
        asq.location_id as location_id,
        asq.product_code as product_code,
        asq.location_name as location_name
        """
        return select_str


    def _from(self):
        from_str = """
        stock_quant asq
        """
        return from_str


    def _group_by(self):
        group_by_str = """
        GROUP BY asq.product_id,asq.company_id,asq.location_id,asq.product_code,asq.location_name
        """
        return group_by_str


    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s FROM %s %s )""" % (self._table, self._select(), self._from(), self._group_by()))



class StockSettings(models.TransientModel):
    _inherit = 'stock.config.settings'


    @api.model
    def action_init_aaswms(self):
        self = self.with_context(active_test=False)
        classified = self._get_classified_fields()
        check_group_fields = ['group_stock_multiple_locations', 'group_stock_production_lot', 'group_uom']
        for name, groups, implied_group in classified['group']:
            if name in check_group_fields:
                groups.write({'implied_ids': [(4, implied_group.id)]})


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def action_done(self):
        result = super(StockMove, self).action_done()
        ardmodel = self.env['aas.receive.deliver'].sudo()
        for record in self:
            product_lot = record.restrict_lot_id
            if not product_lot:
                continue
            # 更新收发汇总
            product_id, product_qty = record.product_id.id, record.product_uom_qty
            locationdestid, locationsrcid = record.location_dest_id.id, record.location_id.id
            if record.location_dest_id.usage == 'internal':
                ardmodel.action_receive(product_id, locationdestid, product_lot.id, product_qty)
            if record.location_id.usage == 'internal':
                ardmodel.action_deliver(product_id, locationsrcid, product_lot.id, product_qty)
        return result



# -*- coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-2 15:44
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError
from odoo.tools.sql import drop_view_if_exists

import logging
_logger = logging.getLogger(__name__)


DELIVERY_TYPE = [('manufacture', u'生产领料'), ('purchase', u'采购退货'), ('sales', u'销售发货'), ('sundry', u'杂项出库')]
DELIVERY_STATE = [('draft', u'草稿'), ('confirm', u'确认'), ('picking', u'拣货'), ('done', u'完成'), ('cancel', u'取消')]



class AASStockDelivery(models.Model):
    _name = 'aas.stock.delivery'
    _description = u'发货单'
    _order = 'id desc'


    name = fields.Char(string=u'名称')
    order_user = fields.Many2one(comodel_name='res.users', string=u'下单人', ondelete='restrict', default=lambda self: self.env.user)
    order_time = fields.Datetime(string=u'下单时间', default=fields.Datetime.now)
    state = fields.Selection(selection=DELIVERY_STATE, string=u'状态', default='draft')
    delivery_type = fields.Selection(selection=DELIVERY_TYPE, string=u'发货类型')
    done_time = fields.Datetime(string=u'完成时间')
    origin_order = fields.Char(string=u'来源单据', copy=False)
    remark = fields.Text(string=u'备注')
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'业务伙伴', ondelete='restrict')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string=u'仓库', ondelete='restrict')
    picking_confirm = fields.Boolean(string=u'拣货确认', default=False, copy=False, help=u'发货员确认货物已分拣')
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)

    delivery_lines = fields.One2many(comodel_name='aas.stock.delivery.line', inverse_name='delivery_id', string=u'发货明细')
    picking_list = fields.One2many(comodel_name='aas.stock.picking.list', inverse_name='delivery_id', string=u'拣货清单')
    operation_lines = fields.One2many(comodel_name='aas.stock.delivery.operation', inverse_name='delivery_id', string=u'拣货作业')
    move_lines = fields.One2many(comodel_name='aas.stock.delivery.move', inverse_name='delivery_id', string=u'执行明细')



    @api.one
    def action_confirm(self):
        """
        确认发货单，当发货单确认后仓库人员才可以开始拣货
        :return:
        """
        if not self.delivery_lines or len(self.delivery_lines) <= 0:
            raise UserError(u'您还没有添加明细，请新添加明细！')
        dlines = [(1, dline.id, {'state': 'confirm'}) for dline in self.delivery_lines]
        self.write({'state': 'confirm', 'delivery_lines': dlines})


    @api.one
    def action_picking_confirm(self):
        """
        拣货确认，仓库人员拣货结束后需要确认拣货，然后诸如生产领料员就可以检查并确认收货
        :return:
        """
        operation_lines = self.env['aas.stock.delivery.operation'].search([('delivery_id', '=', self.id), ('deliver_done', '=', False)])
        if not operation_lines or len(operation_lines) <= 0:
            raise UserError(u'您还没有添加拣货作业，不可以确认拣货')
        self.write({'picking_confirm': True})


    @api.multi
    def action_label_deliver(self):
        """
        标签发货，直接添加标签而生成发货明细，主要是采购退货使用
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.stock.delivery.label.wizard'].create({'delivery_id': self.id})
        view_form = self.env.ref('aas_wms.view_form_aas_stock_delivery_label_wizard')
        return {
            'name': u"标签明细",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.stock.delivery.label.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }


    @api.one
    def action_deliver_done(self):
        """
        仓库已拣货，收货人员检查并确认收货；此时产品库存会扣减
        :return:
        """
        operation_lines = self.env['aas.stock.delivery.operation'].search([('delivery_id', '=', self.id), ('deliver_done', '=', False)])
        if not operation_lines or len(operation_lines) <= 0:
            raise UserError(u'还没有添加拣货明细，不可以确认！')
        if not self.picking_confirm:
            raise UserError(u'仓库人员还没有确认拣货结束，不可以操作！')
        movedict, oplines= {}, []
        for doperation in operation_lines:
            oplines.append((1, doperation.id, {'deliver_done': True}))
            dkey = 'D_'+str(doperation.product_id.id)+'_'+str(doperation.product_lot.id)+'_'+str(doperation.location_id.id)
            if dkey not in movedict:
                movedict[dkey]['product_qty'] += doperation.product_qty
            else:
                movedict[dkey] = {
                    'product_id': doperation.product_id.id, 'product_uom': doperation.product_uom.id,
                    'product_lot': doperation.product_lot.id, 'origin_order': self.origin_order,
                    'delivery_type': self.delivery_type, 'product_qty': doperation.product_qty,
                    'location_src_id': doperation.location_id.id, 'location_dest_id': self.location_id.id,
                    'partner_id': self.partner_id and self.partner_id.id
                }
        deliveryvals = {'picking_confirm': False, 'operation_lines': oplines, 'move_lines': [(0, 0, mval) for mkey, mval in movedict]}
        dlines = self.env['aas.stock.delivery.line'].search([('delivery_id', '=', self.id), ('picking_qty', '>', 0.0)])
        if dlines and len(dlines) > 0:
            deliverylines = []
            for dline in dlines:
                delivery_qty = dline.delivery_qty + dline.picking_qty
                lineval = {'delivery_qty':delivery_qty, 'picking_qty': 0.0}
                if float_compare(dline.product_qty, delivery_qty, precision_rounding=0.000001) <= 0.0:
                    lineval['state'] = 'done'
                deliverylines.append((1, dline.id, lineval))
            deliveryvals['delivery_lines'] = deliverylines
        self.write(deliveryvals)
        if all([line.state=='done' for line in self.delivery_lines]):
            self.write({'state': 'done'})







class AASStockDeliveryLine(models.Model):
    _name = 'aas.stock.delivery.line'
    _description = u'发货明细'
    _rec_name = 'product_id'
    _order = 'id desc'

    delivery_id = fields.Many2one(comodel_name='aas.stock.delivery', string=u'发货单', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_qty = fields.Float(string=u'应发数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    state = fields.Selection(selection=DELIVERY_STATE, string=u'状态', default='draft')
    delivery_type = fields.Selection(selection=DELIVERY_TYPE, string=u'发货类型')
    delivery_qty = fields.Float(string=u'已发数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    picking_qty = fields.Float(string=u'拣货数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)

    picking_list = fields.One2many(comodel_name='aas.stock.picking.list', inverse_name='delivery_line', string=u'拣货清单')
    operation_lines = fields.One2many(comodel_name='aas.stock.delivery.operation', inverse_name='delivery_line', string=u'拣货作业')

    _sql_constraints = [
        ('uniq_prodcut', 'unique (delivery_id, product_id)', u'请不要重复添加同一个产品！')
    ]

    @api.one
    def action_clear_list(self):
        """
        清理当前产品的拣货清单
        :return:
        """
        pick_list = self.env['aas.stock.picking.list'].search([('delivery_id', '=', self.delivery_id.id), ('product_id', '=', self.product_id.id)])
        if pick_list and len(pick_list) > 0:
            pick_list.unlink()


    @api.multi
    def action_building_picking_list(self, picking_qty, labels):
        """
        根据指定的分拣数量和标签生成分拣清单记录
        :param picking_qty:
        :param labels:
        :return:
        """
        self.ensure_one()
        tempkey, pickingdict, label_qty, label_ids = False, {}, 0.0, []
        if not labels or len(labels) <= 0:
            return []
        for label in labels:
            lkey = 'P_'+str(label.location_id.id)+'_'+str(label.product_lot.id)
            if not tempkey:
                tempkey = lkey
            elif tempkey != lkey:
                if float_compare(label_qty, picking_qty, precision_rounding=0.000001) >= 0.0:
                    break
                else:
                    tempkey = lkey
            if lkey in pickingdict:
                pickingdict[lkey]['product_qty'] += label.product_qty
            else:
                pickingdict[lkey] = {
                    'delivery_line': self.id, 'product_id': label.product_id.id, 'product_uom': label.product_uom.id,
                    'product_lot': label.product_lot.id, 'product_qty': label.product_qty, 'location_id': label.location_id.id
                }
            label_qty += label.product_qty
            label_ids.append(label.id)
        self.delivery_id.write({'picking_list': [(0, 0, pval) for pkey, pval in pickingdict]})
        picking_qty -= label_qty
        return label_ids




    @api.one
    def action_picking_list(self, prioritized_lots=None):
        """
        生成分拣清单
        :param prioritized_lots:
        :return:
        """
        self.action_clear_list()
        picking_qty, excludelabelids = self.product_qty - self.delivery_qty, []
        if float_compare(picking_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            return
        stock_location = self.delivery_id.warehouse_id.view_location_id.id
        labeldomain = [('product_id', '=', self.product_id.id), ('state', '=', 'normal'), ('qualified', '=', True), ('stocked', '=', True)]
        labeldomain.extend([('parent_id', '=', False), ('locked', '=', False), ('company_id', '=', self.company_id.id), ('location_id', 'child_of', stock_location)])
        labelorder, label_qty, pickingdict, tempkey = 'onshelf_date,product_lot', 0.0, {}, False
        # 优先处理的标签，可能是生产退料的物料需要优先处理掉
        prioritizedomain = labeldomain + [('prioritized', '=', True)]
        prioritizedlabels = self.env['aas.product.label'].search(prioritizedomain, order=labelorder)
        excludelabelids = self.action_building_picking_list(picking_qty, prioritizedlabels)
        # 优先批次，添加优先处理的批次
        if float_compare(picking_qty, 0.0, precision_rounding=0.000001) > 0 and prioritized_lots:
            prioritizedlotsdomain, prioritizedlotslabels = [], []
            prioritizedlots = self.env['stock.production.lot'].search([('product_id', '=', self.product_id.id), ('name', 'in', prioritized_lots.split(','))])
            if prioritizedlots and len(prioritizedlots) > 0:
                prioritizedlotsdomain = labeldomain + [('product_lot', 'in', prioritizedlots.ids)]
                if excludelabelids and len(excludelabelids) > 0:
                    prioritizedlotsdomain += [('id', 'not in', excludelabelids)]
                prioritizedlotslabels = self.env['aas.product.label'].search(prioritizedlotsdomain, order=labelorder)
            excludelabelids += self.action_building_picking_list(picking_qty, prioritizedlotslabels)
        # 正常条件下，先进先出原则
        if float_compare(picking_qty, 0.0, precision_rounding=0.000001) > 0:
            commondomain = labeldomain
            if excludelabelids and len(excludelabelids) > 0:
                commondomain = labeldomain + [('id', 'not in', excludelabelids)]
            commonlabels = self.env['aas.product.label'].search(commondomain, order=labelorder)
            self.action_building_picking_list(picking_qty, commonlabels)







class AASStockPickingList(models.Model):
    _name = 'aas.stock.picking.list'
    _description = u'拣货清单'

    delivery_id = fields.Many2one(comodel_name='aas.stock.delivery', string=u'发货单', ondelete='cascade')
    delivery_line = fields.Many2one(comodel_name='aas.stock.delivery.line', string=u'发货明细', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位',  ondelete='restrict')
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)




class AASStockDeliveryOperation(models.Model):
    _name = 'aas.stock.delivery.operation'
    _description = u'拣货作业'
    _order = 'id desc'

    delivery_id = fields.Many2one(comodel_name='aas.stock.delivery', string=u'发货单', ondelete='cascade')
    delivery_line = fields.Many2one(comodel_name='aas.stock.delivery.line', string=u'发货明细', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    product_qty = fields.Float(string=u'应发数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    location_id = fields.Many2one(comodel_name='stock.location', string=u'标签库位',  ondelete='restrict')
    pick_user = fields.Many2one(comodel_name='res.users', string=u'拣货人', ondelete='restrict', default=lambda self: self.env.user)
    pick_time = fields.Datetime(string=u'拣货时间', default=fields.Datetime.now)
    check_user = fields.Many2one(comodel_name='res.users', string=u'确认人', ondelete='restrict')
    check_time = fields.Datetime(string=u'确认时间')
    deliver_done = fields.Boolean(string=u'是否发货', default=False, copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)


    _sql_constraints = [
        ('uniq_label', 'unique (delivery_id, label_id)', u'请不要重复添加同一个标签！')
    ]

    @api.onchange('label_id')
    def action_change_label(self):
        if self.label_id:
            self.product_id, self.product_uom = self.label_id.product_id.id, self.label_id.product_uom.id
            self.product_lot, self.product_qty = self.label_id.product_lot.id, self.label_id.product_qty
            self.location_id = self.label_id.location_id.id
        else:
            self.product_id, self.product_uom, self.product_lot, self.product_qty, self.location_id= False, False, False, 0.0, False


    @api.model
    def action_before_create(self, vals):
        label, dline = self.env['aas.product.label'].browse(vals.get('label_id')), False
        if vals.get('delivery_line') and not vals.get('delivery_id'):
            dline = self.env['aas.stock.delivery.line'].browse(vals.get('delivery_line'))
            vals.update({'delivery_id': dline.delivery_id.id})
        elif vals.get('delivery_id') and not vals.get('delivery_line'):
            dline = self.env['aas.stock.delivery.line'].search([('delivery_id', '=', vals.get('delivery_id')), ('product_id', '=', label.product_id.id)], limit=1)
            vals.update({'delivery_line': dline.id})
        if self.env['aas.stock.delivery.line'].search_count([('delivery_id', '=', vals.get('delivery_id')), ('product_id', '=', label.product_id.id)]) <= 0:
            raise UserError(u'非法标签，当前标签货物不在发货明细中,请重新拣货！')
        vals.update({
            'product_id': label.product_id.id, 'product_uom': label.product_uom.id,
            'product_lot': label.product_lot.id, 'location_id': label.location_id.id,
            'product_qty': label.product_qty
        })

    @api.one
    def action_after_create(self):
        dline = self.delivery_line
        lineval = {'picking_qty': dline.picking_qty + self.product_qty}
        if dline.state!='picking':
            lineval['state'] = 'picking'
        dline.write(lineval)


    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        record = super(AASStockDeliveryOperation, self).create(vals)
        record.action_after_create()
        return record




    @api.multi
    def unlink(self):
        linedict = {}
        for record in self:
            if record.delivery_id.picking_confirm:
                raise UserError(u'%s已确认拣货，不可以删除！'% record.delivery_id.name)
            if record.deliver_done:
                raise UserError(u'%s已经发货，不可以删除！'% record.label_id.name)
            lkey = 'L'+str(record.delivery_line.id)
            if lkey not in linedict:
                linedict[lkey] = {'line': record.delivery_line, 'product_qty': record.product_qty}
            else:
                linedict[lkey]['product_qty'] += record.product_qty
        result = super(AASStockDeliveryOperation, self).unlink()
        for lkey, lval in linedict.items():
            dline, product_qty = lval['line'], lval['product_qty']
            product_qty = dline.picking_qty - product_qty
            if float_compare(product_qty, 0.0, precision_rounding=0.000001) < 0.0:
                product_qty = 0.0
            dline.write({'picking_qty': product_qty})
        return result



class AASStockDeliveryMove(models.Model):
    _name = 'aas.stock.delivery.move'
    _description = u'执行明细'
    _order = "id desc"

    delivery_id = fields.Many2one(comodel_name='aas.stock.delivery', string=u'发货单', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品名称', ondelete='restrict')
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'产品单位')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'产品批次', ondelete='restrict')
    origin_order = fields.Char(string=u'来源单据', copy=False)
    delivery_note = fields.Text(string=u'备注')
    delivery_type = fields.Selection(selection=DELIVERY_TYPE, string=u'发货类型')
    delivery_date = fields.Date(string=u'收货日期', default=fields.Date.today)
    delivery_time = fields.Datetime(string=u'收货时间', default=fields.Datetime.now)
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'业务伙伴', ondelete='restrict')
    delivery_user = fields.Many2one(comodel_name='res.users', string=u'收货员工', ondelete='restrict')
    location_src_id = fields.Many2one(comodel_name='stock.location', string=u'来源库位', ondelete='restrict')
    location_dest_id = fields.Many2one(comodel_name='stock.location', string=u'目标库位', ondelete='restrict')
    product_qty = fields.Float(string=u'收货数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)


    @api.model
    def create(self, vals):
        record = super(AASStockDeliveryMove, self).create(vals)
        record.action_receive_deliver()
        record.action_stock_move()
        return record


    @api.one
    def action_receive_deliver(self):
        """
        更新收发汇总表
        :return:
        """
        if self.location_src_id.usage == 'internal':
            self.env['aas.receive.deliver'].action_deliver(self.product_id.id, self.location_src_id.id, self.product_lot.id, self.product_qty)
        if self.location_dest_id.usage == 'internal':
            self.env['aas.receive.deliver'].action_receive(self.product_id.id, self.location_dest_id.id, self.product_lot.id, self.product_qty)


    @api.one
    def action_stock_move(self):
        """
        生成移库单，更新库存
        :return:
        """
        self.env['stock.move'].create({
            'name': self.delivery_id.name, 'product_id': self.product_id.id, 'product_uom': self.product_uom.id,
            'create_date': fields.Datetime.now(), 'restrict_lot_id': self.product_lot.id, 'product_uom_qty': self.product_qty,
            'location_id': self.location_src_id.id, 'location_dest_id': self.location_dest_id.id, 'company_id': self.company_id.id
        }).action_done()



class AASStockDeliveryMoveReport(models.Model):
    _auto = False
    _name = "aas.stock.delivery.move.report"
    _order = "delivery_date desc, product_id"

    product_id = fields.Many2one(comodel_name='product.product', string=u'产品名称', readonly=True)
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'产品单位', readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', readonly=True)
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'产品批次', readonly=True)
    delivery_date = fields.Date(string=u'发货日期', readonly=True)
    origin_order = fields.Char(string=u'来源单据', readonly=True)
    delivery_user = fields.Many2one(comodel_name='res.users', string=u'发货员工', readonly=True)
    location_src_id = fields.Many2one(comodel_name='stock.location', string=u'来源库位', readonly=True)
    location_dest_id = fields.Many2one(comodel_name='stock.location', string=u'目标库位', readonly=True)
    product_qty = fields.Float(string=u'发货数量', digits=dp.get_precision('Product Unit of Measure'), readonly=True)
    delivery_type = fields.Selection(selection=DELIVERY_TYPE, string=u'发货类型', readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'业务伙伴', readonly=True)


    def _select(self):
        select_str = """
        SELECT min(asdm.id) as id,
        asdm.product_id as product_id,
        asdm.product_uom as product_uom,
        asdm.product_lot as product_lot,
        sum(asdm.product_qty) as product_qty,
        asdm.delivery_date as delivery_date,
        asdm.delivery_user as delivery_user,
        asdm.company_id as company_id,
        asdm.location_src_id as location_src_id,
        asdm.location_dest_id as location_dest_id,
        asdm.origin_order as origin_order,
        asdm.delivery_type as delivery_type,
        asdm.partner_id as partner_id
        """
        return select_str

    def _from(self):
        from_str = """
        aas_stock_delivery_move asdm
        """
        return from_str

    def _group_by(self):
        group_by_str = """
        GROUP BY asdm.product_id,asdm.product_lot,asdm.product_uom,asdm.delivery_date,asdm.delivery_user,asdm.location_src_id,asdm.location_dest_id,
        asdm.company_id,asdm.delivery_type,asdm.partner_id,asdm.origin_order
        """
        return group_by_str

    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as ( %s FROM %s %s )""" % (self._table, self._select(), self._from(), self._group_by()))




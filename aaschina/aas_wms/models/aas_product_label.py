# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError, ValidationError

import math
import logging
_logger = logging.getLogger(__name__)

LABEL_STATE = [('draft', u'草稿'), ('normal', u'正常'), ('frozen', u'冻结'), ('over', u'消亡')]

class AASProductLabel(models.Model):
    _name = 'aas.product.label'
    _description = u'产品标签'
    _order = 'id desc'

    name = fields.Char(string=u'名称', copy=False, index=True)
    barcode = fields.Char(string='Barcode', copy=False, index=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', index=True, ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', index=True, ondelete='restrict')
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=1.0)
    product_uom = fields.Many2one(comodel_name='product.uom', string=u'单位', ondelete='set null')
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', ondelete='restrict')
    state = fields.Selection(selection=LABEL_STATE, string=u'状态', default='normal', copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null', default=lambda self: self.env.user.company_id)

    date_code = fields.Char(string='DateCode')
    qualified = fields.Boolean(string=u'是否合格', default=True)
    # 扩展以后供应商贴标签使用
    stocked = fields.Boolean(string=u'是否库存', default=False, help=u'是否已经进入库存')
    customer_code = fields.Char(string=u'客户编码', help=u'产品在客户方的编码')
    origin_order = fields.Char(string=u'来源单据')
    pack_user = fields.Char(string=u'包装员工', copy=False)
    prioritized = fields.Boolean(string=u'优先处理', default=False)
    locked = fields.Boolean(string=u'锁定', default=False, copy=False)
    locked_order = fields.Char(string=u'锁定单据', help=u'标签是因为此单据而锁定', copy=False)
    partner_id = fields.Many2one(comodel_name='res.partner', string=u'业务伙伴', ondelete='set null')

    parent_id = fields.Many2one(comodel_name='aas.product.label', string=u'父标签', ondelete='restrict', copy=False)
    parent_left = fields.Integer(string='Left Parent', index=True)
    parent_right = fields.Integer(string='Right Parent', index=True)
    has_children = fields.Boolean(string=u'是否包裹', copy=False, compute='_compute_has_children', store=True)
    child_lines = fields.One2many(comodel_name='aas.product.label', inverse_name='parent_id', string=u'子标签', copy=False)
    origin_id = fields.Many2one(comodel_name='aas.product.label', string=u'源标签', ondelete='set null', copy=False, help=u'当前标签由拆解而得的源头标签')
    origin_lines = fields.One2many(comodel_name='aas.product.label', inverse_name='origin_id', string=u'拆解标签', copy=False)

    onshelf_time = fields.Datetime(string=u'上架时间', help=u'货物到库存库位上架的时间')
    onshelf_date = fields.Date(string=u'上架日期', help=u'货物上架日期，拣货时排序使用')
    offshelf_time = fields.Datetime(string=u'下架时间', help=u'货物从库存库位下架的时间')
    stock_date = fields.Date(string=u'库龄日期', help=u'库龄时间段，货物允许放在仓库的最后日期')
    warranty_date = fields.Date(string=u'质保日期', help=u'质保时间段，货物最后有效的日期，过期将自动冻结')

    product_name = fields.Char(string=u'产品名称')
    product_code = fields.Char(string=u'产品编码')
    product_lotname = fields.Char(string=u'批次名称')
    oqcpass = fields.Boolean(string=u'OQC检测通过', default=False, copy=False)
    isproduction = fields.Boolean(string=u'产线标签', copy=False, related='location_id.edgelocation', store=True)
    journal_lines = fields.One2many(comodel_name='aas.product.label.journal', inverse_name='label_id', string=u'查存卡', copy=False)

    @api.depends('child_lines')
    def _compute_has_children(self):
        for record in self:
            record.has_children = record.child_lines and len(record.child_lines) > 0

    @api.model
    def action_before_create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('aas.product.label')
        vals.update({'name': sequence, 'barcode': sequence})
        product_lot = self.env['stock.production.lot'].browse(vals.get('product_lot'))
        product_id = product_lot.product_id
        vals.update({
            'product_uom': product_id.uom_id.id, 'product_name': product_id.name,
            'product_code': product_id.default_code, 'product_lotname': product_lot.name
        })

    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        record = super(AASProductLabel, self).create(vals)
        record.action_after_create()
        return record

    @api.one
    def action_after_create(self):
        journalvals = {'label_id': self.id, 'location_dest_id': self.location_id.id}
        journalvals.update({'balance_qty': self.product_qty, 'journal_qty': self.product_qty})
        if self.company_id:
            journalvals['company_id'] = self.company_id.id
        if self.stocked and self.state in ['normal', 'frozen']:
            self.env['aas.product.label.journal'].create(journalvals)


    @api.one
    def action_unpack(self):
        """
        包裹标签拆包，最外层标签消亡，里层标签直接暴露出来
        :return:
        """
        if not self.child_lines or len(self.child_lines) <= 0:
            raise UserError(u'当前标签不是包裹，不可以拆包！')
        if self.parent_id:
            raise UserError(u'当前包裹不是最外层包裹，不可以直接拆包，需要从最外层开始层层拆包！')
        self.child_lines.write({'parent_id': False})
        self.write({'state': 'over', 'product_qty': 0.0, 'date_code': False, 'origin_order': False})


    @api.multi
    def action_split(self):
        self.ensure_one()
        wizard = self.env['aas.product.label.split.wizard'].create({
            'label_id': self.id, 'product_id': self.product_id.id,
            'product_lot': self.product_lot.id, 'product_qty': self.product_qty
        })
        view_form = self.env.ref('aas_wms.view_form_aas_product_label_split_wizard')
        return {
            'name': u"标签拆分",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.product.label.split.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }


    @api.one
    def action_dosplit(self, label_qty, label_count=None):
        """
        标签拆分，将一个大包装的标签拆分成若干个小包装标签
        :param label_qty:
        :param label_count:
        :return:
        """
        if self.state != 'normal':
            raise UserError(u'标签状态异常，不可以拆分！')
        if self.child_lines and len(self.child_lines) >= 0:
            raise UserError(u'包裹标签，不可以拆分！')
        if self.parent_id:
            raise UserError(u'标签被包装在其他包裹中，请先拆包再对标签进行拆分！')
        if float_compare(label_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            raise UserError(u'新标签的产品数量必须是一个正数！')
        if not label_count:
            label_count = int(math.ceil(self.product_qty / label_qty))
        elif label_count <= 0:
            raise UserError(u'拆分出来的标签数量必须是一个正整数！')
        elif float_compare(label_qty*label_count, self.product_qty, precision_rounding=0.000001) > 0:
            raise UserError(u'拆分设置异常，拆分总数已大于实际标签可拆分数量！')
        temp_qty, tlabel_qty = self.product_qty, label_qty
        for i in range(0, label_count):
            if float_compare(temp_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                break
            if float_compare(temp_qty, label_qty, precision_rounding=0.000001) < 0.0:
                tlabel_qty = temp_qty
            self.copy({'state': self.state, 'origin_id': self.id, 'product_qty': tlabel_qty})
            temp_qty -= tlabel_qty
        selfvals = {'product_qty': temp_qty}
        if float_compare(temp_qty, 0.0, precision_rounding=0.000001) <= 0.0:
            selfvals.update({'state': 'over', 'product_qty': 0.0})
        self.write(selfvals)

    @api.model
    def action_strippe(self, parent_label, child_label):
        """
        标签分离，可以将自己标签直接从包裹中分离出来，并脱离父子级关系
        :param parent_label:
        :param child_label:
        :return:
        """
        if not parent_label or not child_label:
            raise UserError(u'请仔细检查父子标签军不可以为空！')
        if not child_label.parent_id:
            raise UserError(u'当前标签没有父标签，无需进行分离操作！')
        if child_label and child_label.parent_id.id != parent_label.id:
            raise UserError(u'分离操作异常，当前标签并非此父标签的子标签，不能进行剥离操作！')
        child_label.write({'parent_id': False})
        if not parent_label.child_lines or len(parent_label.child_lines) <= 0:
            parent_label.write({'state': 'over', 'product_qty': 0.0, 'date_code': False, 'origin_order': False})
            if parent_label.parent_id:
                self.action_strippe(parent_label.parent_id, parent_label)
        parent_label.write({'product_qty': sum([tchild.product_qty for tchild in parent_label.child_lines])})


    @api.multi
    def action_frozen(self):
        """
        冻结标签
        :return:
        """
        self.write({'state': 'frozen'})


    @api.multi
    def action_unfreeze(self):
        """
        解冻标签
        :return:
        """
        self.write({'state': 'normal'})


    @api.multi
    def write(self, vals):
        if 'product_id' in vals:
            raise UserError(u'标签的产品不可以变更！')
        if 'product_lot' in vals:
            raise UserError(u'标签的批次不可以变更！')
        if 'product_qty' in vals:
            operate_order = self.env.context.get('operate_order', False)
            self.action_journal_qty(vals.get('product_qty'), operate_order)
        locationid = vals.get('location_id', False)
        if locationid:
            self.action_journal_location(locationid)
            templocation = self.env['stock.location'].browse(locationid)
            # 标签进入呆滞库位自动冻结
            if templocation.dulllocation:
                vals['state'] = 'frozen'
        result = super(AASProductLabel, self).write(vals)
        self.action_after_write(vals)
        return result


    @api.multi
    def action_journal_qty(self, product_qty, operate_order=None):
        for record in self:
            journalvals = {'label_id': record.id}
            temp_qty = record.product_qty - product_qty
            if float_compare(temp_qty, 0.0, precision_rounding=0.000001) > 0:
                journalvals['location_src_id'] = record.location_id.id
            else:
                journalvals['location_dest_id'] = record.location_id.id
            journalvals.update({'journal_qty': abs(temp_qty), 'balance_qty': product_qty})
            if record.company_id:
                journalvals['company_id'] = record.company_id.id
            if operate_order:
                journalvals['operate_order'] = operate_order
            self.env['aas.product.label.journal'].create(journalvals)

    @api.multi
    def action_journal_location(self, location_id):
        for record in self:
            if record.location_id.id == location_id:
                continue
            journalvals = {'label_id': record.id, 'journal_qty': record.product_qty, 'balance_qty': record.product_qty}
            journalvals.update({'location_src_id': record.location_id.id, 'location_dest_id': location_id})
            if record.company_id:
                journalvals['company_id'] = record.company_id.id
            self.env['aas.product.label.journal'].create(journalvals)


    @api.multi
    def action_after_write(self, vals):
        tempvals = {}
        recursion_keys = ['location_id', 'state', 'company_id', 'date_code', 'qualified', 'stocked', 'customer_code', 'origin_order']
        recursion_keys.extend(['prioritized', 'locked', 'locked_order', 'onshelf_time', 'onshelf_date', 'offshelf_time', 'warranty_date', 'stock_date'])
        for tkey, tval in vals.items():
            if tkey in recursion_keys:
                tempvals[tkey] = tval
        if tempvals and len(tempvals) > 0:
            childrenlabels = self.env['aas.product.label']
            for record in self:
                if not record.child_lines or len(record.child_lines) <= 0:
                    continue
                for childlabel in record.child_lines:
                    childrenlabels |= childlabel
            if childrenlabels and len(childrenlabels) > 0:
                childrenlabels.write(tempvals)
        if 'product_qty' in vals:
            for record in self:
                parentlabel = record.parent_id
                if not parentlabel:
                    continue
                parentlabel.write({'product_qty': sum([tchild.product_qty for tchild in parentlabel.child_lines])})

    @api.model
    def action_merge_labels(self, labels, location, singleton=True):
        """标签合并；singleton为True时新生成一个标签，来源标签自动消亡；False时生成的新标签是来源标签的父标签
        :param labels:
        :param location:
        :param singleton:
        :return:
        """
        if not labels or len(labels) <= 0:
            raise UserError(u'请先添加需要合并的标签！')
        if not location:
            raise UserError(u'请先设置好合并后的标签库位')
        movevals, firstlabel, datecodes, originorders = {}, labels[0], [], []
        labellines, labelmoving = self.env['aas.product.label'], self.env['aas.product.label']
        location_id, product_lot, stocked, company_id = location.id, firstlabel.product_lot.id, firstlabel.stocked, firstlabel.company_id.id
        labelvals = {'location_id': location_id, 'product_qty': 0.0, 'onshelf_time': firstlabel.onshelf_time, 'warranty_date': firstlabel.warranty_date, 'stock_date': firstlabel.stock_date}
        for tlabel in labels:
            if product_lot != tlabel.product_lot.id:
                raise UserError(u'标签%s和其他标签上的产品批次不相同,不能合并！'% tlabel.name)
            if stocked != tlabel.stocked:
                raise UserError(u'标签%s和其他标签入库装填不一致,不能合并！'% tlabel.name)
            if company_id != tlabel.company_id.id:
                raise UserError(u'标签%s和其他标签所属公司不同,不能合并！'% tlabel.name)
            labelvals['product_qty'] += tlabel.product_qty
            labellines |= tlabel
            if tlabel.location_id.id != location_id:
                labelmoving |= tlabel
                if tlabel.stocked:
                    mkey = 'location_'+str(tlabel.location_id.id)+'_'+str(location_id)
                    if mkey in movevals:
                        movevals[mkey]['product_uom_qty'] += tlabel.product_qty
                    else:
                        movevals[mkey] = {
                            'name': tlabel.name, 'product_id': tlabel.product_id.id, 'product_uom': tlabel.product_uom.id, 'create_date': fields.Datetime.now(),
                            'restrict_lot_id': product_lot, 'product_uom_qty': tlabel.product_qty, 'location_id': tlabel.location_id.id, 'location_dest_id': location_id, 'company_id': company_id
                        }
            if not labelvals['onshelf_time'] or (tlabel.onshelf_time and tlabel.onshelf_time < labelvals['onshelf_time']):
                labelvals.update({'onshelf_time': tlabel.onshelf_time, 'onshelf_date': tlabel.onshelf_date})
            if not labelvals['warranty_date'] or (tlabel.warranty_date and tlabel.warranty_date < labelvals['warranty_date']):
                labelvals['warranty_date'] = tlabel.warranty_date
            if not labelvals['stock_date'] or (tlabel.stock_date and tlabel.stock_date < labelvals['stock_date']):
                labelvals['stock_date'] = tlabel.stock_date
            if tlabel.date_code:
                datecodes.extend(tlabel.date_code.split(','))
            if tlabel.origin_order:
                originorders.extend(tlabel.origin_order.split(','))
        if len(datecodes) > 0:
            labelvals['date_code'] = ','.join(list(set(datecodes)))
        if len(originorders) > 0:
            labelvals['origin_order'] = ','.join(list(set(originorders)))
        parentlabel = firstlabel.copy(labelvals)
        if singleton:
            labellines.with_context({'operate_order': parentlabel.name}).write({'product_qty': 0.0, 'state': 'over'})
        else:
            labellines.write({'parent_id': parentlabel.id})
            if labelmoving and len(labelmoving) > 0:
                labelmoving.write({'location_id': location_id})
        if movevals and len(movevals) > 0:
            movelist = self.env['stock.move']
            for mkey, mval in movevals.items():
                movelist |= self.env['stock.move'].create(mval)
            movelist.action_done()
        return parentlabel


    @api.multi
    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(u'标签已在正常业务中使用，不可以删除！')
        return super(AASProductLabel, self).unlink()


    @api.model
    def action_print_label(self, printer_id, ids=[], domain=[]):
        values = {'success': True, 'message': '', 'records': []}
        printer = self.env['aas.label.printer'].browse(printer_id)
        if not printer.field_lines or len(printer.field_lines) <= 0:
            values.update({'success': False, 'message': u'请联系管理员标签打印未指定具体打印内容！'})
            return values
        values.update({'printer': printer.name, 'serverurl': printer.serverurl})
        field_list = [fline.field_name for fline in printer.field_lines]
        if ids and len(ids) > 0:
            labeldomain = [('id', 'in', ids)]
        else:
            labeldomain = domain
        if not labeldomain or len(labeldomain) <= 0:
            return {'success': False, 'message': u'您可能已经选择了所有标签或未选择任何标签，请选中需要打印的标签！'}
        records = self.search_read(domain=labeldomain, fields=field_list)
        if not records or len(records) <= 0:
            values.update({'success': False, 'message': u'未搜索到需要打印的标签！'})
            return values
        records = printer.action_correct_records(records)
        values['records'] = records
        return values

    @api.one
    def action_stock(self, srclocationid, origin=False):
        self.env['stock.move'].create({
            'name': self.name if not origin else origin,
            'product_id': self.product_id.id,  'product_uom': self.product_uom.id,
            'restrict_lot_id': self.product_lot.id, 'product_uom_qty': self.product_qty,
            'location_id': srclocationid, 'location_dest_id': self.location_id.id,
            'create_date': fields.Datetime.now(), 'company_id': self.env.user.company_id.id
        }).action_done()


    @api.model
    def action_production_labels(self, labelinfo):
        """不经过其他操作，直接生成标签
        :param labelinfo:
        :return:
        """
        values = {'success': True, 'message': '', 'desc': '', 'barcodes': []}
        product_code, product_lot = labelinfo.get('PN', False), labelinfo.get('LOT', False)
        label_qty, label_count = labelinfo.get('QTY', False), labelinfo.get('Number', False)
        if not product_code:
            values.update({'success': False, 'message': u'请仔细检查，您还未设置产品编码！'})
            return values
        if not product_lot:
            values.update({'success': False, 'message': u'请仔细检查，您还未设置产品批次！'})
            return values
        if not label_qty or float_compare(label_qty, 0.0, precision_rounding=0.0000001) <= 0.0:
            values.update({'success': False, 'message': u'请仔细检查，每个标签的数量必须是一个大于零的数！'})
            return values
        if not label_count or label_count <= 0:
            values.update({'success': False, 'message': u'请仔细检查，标签的个数必须大于零！'})
            return values
        temproduct = self.env['product.product'].search([('default_code', '=', product_code)], limit=1)
        if not temproduct:
            values.update({'success': False, 'message': u'请仔细检查，您的产品编码异常，系统中不存在此产品！'})
            return values
        values['desc'] = temproduct.name
        templot = self.env['stock.production.lot'].action_checkout_lot(temproduct.id, product_lot)
        pdtlocation = self.env.ref('stock.location_production')
        packlocation = self.env['stock.warehouse'].get_default_warehouse().wh_pack_stock_loc_id
        # 启用打包库位
        if not packlocation.active:
            packlocation.sudo().write({'active': True})
        for tindex in range(0, label_count):
            templabel = self.env['aas.product.label'].create({
                'product_id': temproduct.id, 'product_code': product_code, 'product_uom': temproduct.uom_id.id,
                'stocked': True, 'location_id': packlocation.id, 'product_lot': templot.id, 'product_qty': label_qty
            })
            values['barcodes'].append(templabel.name)
        self.env['stock.move'].create({
            'name': ','.join(values['barcodes']),
            'product_id': temproduct.id, 'product_uom': temproduct.uom_id.id,
            'restrict_lot_id': templot.id, 'product_uom_qty': label_qty * label_count,
            'location_id': pdtlocation.id, 'location_dest_id': packlocation.id, 'create_date': fields.Datetime.now()
        }).action_done()
        return values



# 标签流水帐  查存卡
class AASProductLabelJournal(models.Model):
    _name = "aas.product.label.journal"
    _description = u"标签查存卡"

    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='cascade')
    record_time = fields.Datetime(string=u'时间', required=True, default=fields.Datetime.now)
    location_src_id = fields.Many2one(comodel_name='stock.location', string=u'发出', ondelete='set null')
    location_dest_id = fields.Many2one(comodel_name='stock.location', string=u'收入', ondelete='set null')
    journal_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    balance_qty = fields.Float(string=u'结存', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    operate_order = fields.Char(string=u'操作单据', copy=False)
    operate_note = fields.Char(string=u'操作备注', copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', ondelete='set null')

    @api.model
    def action_before_create(self, vals):
        context = self.env.context
        if context.get('operate_order'):
            vals['operate_order'] = context.get('operate_order')
        if context.get('operate_note'):
            vals['operate_note'] = context.get('operate_note')

    @api.model
    def create(self, vals):
        self.action_before_create(vals)
        return super(AASProductLabelJournal, self).create(vals)

# 标签调整记录
class AASProductLabelAdjust(models.Model):
    _name = 'aas.product.label.adjust'
    _description = 'AAS Product Label Adjust'

    name = fields.Char(string=u'名称', copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    adjust_time = fields.Datetime(string=u'调整时间', default=fields.Datetime.now, copy=False)
    adjuster_id = fields.Many2one(comodel_name='res.users', string=u'调整人', ondelete='restrict', default=lambda self:self.env.user)
    adjust_note = fields.Text(string=u'调整说明')
    state = fields.Selection(selection=[('draft', u'草稿'), ('done', u'完成')], string=u'状态', default='draft', copy=False)
    label_lines = fields.One2many(comodel_name='aas.product.label.adjust.line', inverse_name='adjust_id', string=u'调整明细')

    @api.onchange('product_id')
    def change_product(self):
        self.label_lines = False

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('aas.product.label.adjust')
        return super(AASProductLabelAdjust, self).create(vals)

    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(u'调整已完成，不可以删除！')
        return super(AASProductLabelAdjust, self).unlink()

    @api.one
    def action_adjust(self):
        if not self.label_lines or len(self.label_lines) <= 0:
            raise UserError(u'请先添加调整明细')
        movedict, destlocation, company = {}, self.env.ref('stock.location_inventory'), self.env.user.company_id
        for mline in self.label_lines:
            tlabel = mline.label_id
            balance_qty = mline.before_qty - mline.after_qty
            if not tlabel.isproduction:
                if float_compare(balance_qty, 0.0, precision_rounding=0.0000001) > 0:
                    mkey = 'M-0-'+str(tlabel.location_id)+'-'+str(tlabel.product_lot.id)
                    if mkey in movedict:
                        movedict[mkey]['product_uom_qty'] += balance_qty
                    else:
                        movedict[mkey] = {
                            'name': self.name, 'product_id': self.product_id.id, 'product_uom': tlabel.product_uom.id, 'create_date': fields.Datetime.now(),
                            'restrict_lot_id': tlabel.product_lot.id, 'product_uom_qty': balance_qty, 'location_id': tlabel.location_id.id, 'location_dest_id': destlocation.id, 'company_id': company.id
                        }
                else:
                    mkey = 'M-'+str(tlabel.location_id)+'-0-'+str(tlabel.product_lot.id)
                    if mkey in movedict:
                        movedict[mkey]['product_uom_qty'] += abs(balance_qty)
                    else:
                        movedict[mkey] = {
                            'name': self.name, 'product_id': self.product_id.id, 'product_uom': tlabel.product_uom.id, 'create_date': fields.Datetime.now(),
                            'restrict_lot_id': tlabel.product_lot.id, 'product_uom_qty': abs(balance_qty), 'location_id': destlocation.id, 'location_dest_id': tlabel.location_id.id, 'company_id': company.id
                        }
            tlabel.with_context({'operate_order': self.name}).write({'product_qty': mline.after_qty})
        if movedict and len(movedict) > 0:
            movelist = self.env['stock.move']
            for mkey, mval in movedict.items():
                movelist |= self.env['stock.move'].create(mval)
            movelist.action_done()
        self.write({'state': 'done', 'adjust_time': fields.Datetime.now()})



# 标签调整明细
class AASProductLabelAdjustLine(models.Model):
    _name = 'aas.product.label.adjust.line'
    _description = 'AAS Product Label Adjust Line'

    adjust_id = fields.Many2one(comodel_name='aas.product.label.adjust', string=u'调整', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='restrict')
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', ondelete='restrict')
    before_qty = fields.Float(string=u'调整前数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    after_qty = fields.Float(string=u'调整后数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    @api.onchange('label_id')
    def change_label(self):
        if self.label_id:
            self.product_lot, self.before_qty = self.label_id.product_lot.id, self.label_id.product_qty
        else:
            self.product_lot, self.before_qty = False, 0.0

    @api.one
    @api.constrains('after_qty')
    def action_check_afterqty(self):
        if float_compare(self.after_qty, 0.0, precision_rounding=0.000001) < 0.0:
            raise ValidationError(u'调整后的数量不能小于零！')
        if float_compare(self.after_qty, self.before_qty, precision_rounding=0.000001) == 0.0:
            raise ValidationError(u'调整前后的数量不能相同！')



    @api.model
    def create(self, vals):
        tlabel = self.env['aas.product.label'].browse(vals.get('label_id'))
        vals.update({'product_lot': tlabel.product_lot.id, 'before_qty': tlabel.product_qty})
        return super(AASProductLabelAdjustLine, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('label_id', False):
            tlabel = self.env['aas.product.label'].browse(vals.get('label_id'))
            vals.update({'product_lot': tlabel.product_lot.id, 'before_qty': tlabel.product_qty})
        return super(AASProductLabelAdjustLine, self).write(vals)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def get_current_qty(self):
        self.ensure_one()
        temp_qty = 0.0
        labeldomain = [('product_id', '=', self.id), ('state', '=', 'normal'), ('locked', '=', False), ('qualified', '=', True)]
        stockdomain = labeldomain + [('location_id.mrblocation', '=', False), ('location_id.edgelocation', '=', False), ('location_id.usage', '=', 'internal')]
        stocklabels = self.env['aas.product.label'].search(stockdomain)
        if stocklabels and len(stocklabels) > 0:
            temp_qty = sum([plabel.product_qty for plabel in stocklabels])
        return temp_qty


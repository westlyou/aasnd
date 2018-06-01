# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-1-6 16:03
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError, ValidationError

import logging
import base64
from cStringIO import StringIO
from odoo.tools.misc import str2bool, xlwt

_logger = logging.getLogger(__name__)


# 成品产出
class AASProductionProduct(models.Model):
    _name = 'aas.production.product'
    _description = 'AAS Production Product'
    _rec_name = 'product_id'
    _order = 'id desc'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', index=True)
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次', index=True)
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', index=True)
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', index=True)

    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', index=True)
    workticket_id = fields.Many2one(comodel_name='aas.mes.workticket', string=u'工票', index=True)
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', index=True)
    product_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', index=True)
    product_qty = fields.Float(string=u'产出数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    badmode_qty = fields.Float(string=u'不良数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    consumed_qty = fields.Float(string=u'消耗数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    finaloutput = fields.Boolean(string=u'最终产出', default=False, copy=False, help=u'是否最终的成品产出')
    output_date = fields.Char(string=u'产出日期', copy=False)
    output_hour = fields.Integer(string=u'产出小时')
    output_time = fields.Datetime(string=u'产出时间', default=fields.Datetime.now, copy=False)
    onepass = fields.Boolean(string=u'一次通过', default=True, copy=False)
    qualified = fields.Boolean(string=u'是否合格', default=True, copy=False)
    canconsume = fields.Boolean(string=u'可消耗', copy=False, compute='_compute_canconsume', store=True)
    ccode = fields.Char(string=u'客方编码', copy=False)
    pcode = fields.Char(string=u'产品编码', copy=False)
    tracing = fields.Boolean(string=u'追溯', default=False, copy=False, help=u'标记为追溯产出，用于质量追溯')
    container_id = fields.Many2one(comodel_name='aas.container', string=u'产出容器')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'产出标签')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    product_code = fields.Char(string=u'产品编码', copy=False)
    customer_code = fields.Char(string=u'客方编码', copy=False)
    mesline_name = fields.Char(string=u'产线名称', copy=False)
    workstation_name = fields.Char(string=u'工位名称', copy=False)
    schedule_name = fields.Char(string=u'班次名称', copy=False)
    workorder_name = fields.Char(string=u'工单编号', copy=False)

    material_lines = fields.One2many(comodel_name='aas.production.material', inverse_name='production_id', string=u'原料清单')
    employee_lines = fields.One2many(comodel_name='aas.production.employee', inverse_name='production_id', string=u'员工清单')
    badmode_lines = fields.One2many(comodel_name='aas.production.badmode', inverse_name='production_id', string=u'不良清单')

    @api.depends('product_qty', 'consumed_qty')
    def _compute_canconsume(self):
        for record in self:
            if float_compare(record.product_qty, record.consumed_qty, precision_rounding=0.000001) <= 0.0:
                record.canconsume = False
            else:
                record.canconsume = True
    @api.model
    def create(self, vals):
        record = super(AASProductionProduct, self).create(vals)
        product = record.product_id
        productvals = {'product_code': product.default_code}
        if product.customer_product_code:
            productvals['customer_code'] = product.customer_product_code
        if record.mesline_id:
            productvals['mesline_name'] = record.mesline_id.name
        if record.workstation_id:
            productvals['workstation_name'] = record.workstation_id.name
        if record.schedule_id:
            productvals['schedule_name'] = record.schedule_id.name
        if record.workorder_id:
            productvals['workorder_name'] = record.workorder_id.name
        chinatime = fields.Datetime.to_china_string(fields.Datetime.now())
        try:
            currenthour = int(chinatime[11:13])
            if 0 <= currenthour <= 23:
                productvals['output_hour'] = currenthour
        except Exception:
            productvals['output_hour'] = False
        record.write(productvals)
        return record

    @api.model
    def action_production_output(self, workorder, product, output_qty, workticket=False, schedule=False,
                                 workcenter=False, workstation=False, badmode_lines=[], employee=False,
                                 equipment=False, serialnumber=False, container=False, finaloutput=False,
                                 tracing=False, output_date=False, output_time=False, product_lot=False, cutting=False):
        """工单产出
        :param workorder:
        :param product:
        :param output_qty:
        :param workticket:
        :param workcenter:
        :param workstation:
        :param badmode_lines:
        :param employee:
        :param equipment:
        :param serialnumber:
        :param container:
        :param finaloutput:
        :param tracing:
        :param output_date:
        :param output_time:
        :param product_lot:
        :param cutting:
        :return:
        """
        values = {'success': True, 'message': '', 'label_id': '0', 'production_id': '0'}
        if workorder.state == 'done':
            values.update({'success': False, 'message': u'工单%s已完工，不可以继续产出！'% workorder.name})
            return values
        _logger.info(u'工单%s开始产出时间:%s', workorder.name, fields.Datetime.now())
        mesline = workorder.mesline_id
        if not output_date:
            output_date = fields.Datetime.to_china_today() if not mesline.workdate else mesline.workdate
        # update 20180411 确保下线产出必须设置容器
        if not container and cutting:
            values.update({'success': False, 'message': u'下线产出必须先设置好容器!'})
            return values
        outputvals = {
            'workorder_id': workorder.id, 'product_id': product.id, 'finaloutput': finaloutput,
            'mesline_id': mesline.id, 'output_date': output_date, 'pcode': product.default_code, 'tracing': tracing
        }
        if product_lot:
            outputvals['product_lot'] = product_lot.id
        if not output_time:
            output_time = fields.Datetime.now()
            outputvals['output_time'] = output_time
        if schedule:
            outputvals['schedule_id'] = schedule.id
        elif mesline.schedule_id:
            outputvals['schedule_id'] = mesline.schedule_id.id
        if workstation:
            outputvals['workstation_id'] = workstation.id
        if workticket:
            outputvals['workticket_id'] = workticket.id
            if workticket.islastworkcenter() and workorder.output_manner == 'container':
                if not container:
                    values.update({'success': False, 'message': u'当前工单产出方式为容器，您还未添加产出容器！'})
                    return values
                elif not container.isempty:
                    values.update({'success': False, 'message': u'当前容器已被占用，请使用其他容器产出！'})
                    return values
        if equipment:
            outputvals['equipment_id'] = equipment.id
        if serialnumber:
            outputvals['serialnumber_id'] = serialnumber.id
            if serialnumber.reworked:
                outputvals['onepass'] = False

        if product.customer_product_code:
            outputvals['ccode'] = product.customer_product_code
        product_qty, badmode_qty = output_qty, 0.0
        # 加载不良信息
        if badmode_lines and len(badmode_lines) > 0:
            badmodelines = []
            for bline in badmode_lines:
                badmode_qty += bline['badmode_qty']
                badmodelines.append((0, 0, {
                    'badmode_id': bline['badmode_id'],
                    'badmode_qty': bline['badmode_qty'],
                    'mesline_id': outputvals.get('mesline_id', False),
                    'schedule_id': outputvals.get('schedule_id', False),
                    'workstation_id': outputvals.get('workstation_id', False),
                    'equipment_id': outputvals.get('equipment_id', False),
                    'workorder_id': outputvals.get('workorder_id', False),
                    'workticket_id': outputvals.get('workticket_id', False),
                    'product_id': outputvals.get('product_id', False),
                    'badmode_date': outputvals.get('output_date', False)
                }))
            outputvals.update({'badmode_lines': badmodelines, 'badmode_qty': badmode_qty})
            product_qty -= badmode_qty
        outputvals['product_qty'] = product_qty
        # 加载产出员工清单
        empvals = self.action_loading_output_employeelist(mesline, workstation, employee=employee, equipment=equipment)
        if empvals['employeelines'] and len(empvals['employeelines']) > 0:
            outputvals['employee_lines'] = empvals['employeelines']
        # 加载消耗清单
        consumevals = self.action_loading_consumelist(workorder, product, output_qty, workcenter=workcenter)
        if not consumevals.get('success', False):
            values.update(consumevals)
            return values
        materiallist, movevallist, virtuallist = [], [], []
        consumedict, feedids = consumevals['consumedict'], []
        # 加载原料消耗明细
        production_location_id = self.env.ref('stock.location_production').id
        if consumedict and len(consumedict) > 0:
            for materialid, stockvals, in consumedict.items():
                materiallots, uomid = stockvals['stocklist'], stockvals['uom_id']
                for mlot in materiallots:
                    materiallist.append((0, 0, {
                        'material_id': materialid, 'material_lot': mlot['lot_id'],
                        'material_qty': mlot['lot_qty'], 'mesline_id': mesline.id
                    }))
                    if mlot.get('feed_id', False):
                        feedids.append(mlot.get('feed_id'))
                    locationlist = mlot.get('locationlist', [])
                    if locationlist and len(locationlist) > 0:
                        for locationval in locationlist:
                            movevallist.append({
                                'name': workorder.name,
                                'product_id': materialid,  'product_uom': uomid,
                                'restrict_lot_id': mlot['lot_id'], 'product_uom_qty': locationval['product_qty'],
                                'location_id': locationval['location_id'], 'location_dest_id': production_location_id,
                                'create_date': fields.Datetime.now(), 'company_id': self.env.user.company_id.id
                            })
                    tempvlist = mlot.get('productionlist', [])
                    if tempvlist and len(tempvlist) > 0:
                        virtuallist += tempvlist
            outputvals['material_lines'] = materiallist
        currentoutput = self.env['aas.production.product'].create(outputvals)
        values['production_id'] = currentoutput.id
        # 消耗原材料，库存移动到生产虚库
        if movevallist and len(movevallist) > 0:
            movelist = self.env['stock.move']
            for moveval in movevallist:
                moveval['production_id'] = currentoutput.id
                movelist |= self.env['stock.move'].create(moveval)
            movelist.action_done()
        # 消耗虚拟件，更新相应产出记录上的已消耗数量
        if virtuallist and len(virtuallist) > 0:
            for virtualvals in virtuallist:
                temproduction = self.env['aas.production.product'].browse(virtualvals['production_id'])
                consumed_qty = temproduction.consumed_qty + virtualvals['product_qty']
                if float_compare(consumed_qty, temproduction.product_qty, precision_rounding=0.000001) > 0.0:
                    consumed_qty = temproduction.product_qty
                temproduction.write({'consumed_qty': consumed_qty})
        # 加载原料不良详情
        if currentoutput.badmode_lines and len(currentoutput.badmode_lines) > 0:
            badmateriallist = self.env['aas.mes.bom'].action_loading_materialist(product.id, 1.0)
            if badmateriallist and len(badmateriallist) > 0:
                for badline in currentoutput.badmode_lines:
                    badline.write({
                        'material_lines': [(0, 0, {
                            'material_id': tmaterial['product_id'],
                            'material_qty': badline.badmode_qty * tmaterial['product_qty']
                        }) for tmaterial in badmateriallist]
                    })
        # 刷新上料记录
        if feedids and len(feedids) > 0:
            feedinglist = self.env['aas.mes.feedmaterial'].browse(feedids)
            if feedinglist and len(feedinglist) > 0:
                feedinglist.action_freshandclear()
        # 更新产出库存
        if workticket and workticket.islastworkcenter():
            if workorder.output_manner == 'container' and container:
                self.action_output2container(currentoutput, container)
            if workorder.output_manner == 'label':
                self.action_output2label(currentoutput)
                templabel = currentoutput.label_id
                if templabel:
                    values['label_id'] = templabel.id
                    workticket.write({'label_id': templabel.id})
        consumelines = consumevals.get('consumelines', [])
        workordervals = {'output_time': fields.Datetime.now()}
        if consumelines and len(consumelines) > 0:
            workordervals['consume_lines'] = consumelines
        # 更新生产状态
        if workorder.state == 'confirm':
            workordervals.update({
                'state': 'producing',
                'produce_start': fields.Datetime.now(), 'produce_date': fields.Datetime.to_china_today()
            })
        if finaloutput:
            workordervals['output_qty'] = workorder.output_qty + currentoutput.product_qty
        if product.id == workorder.product_id.id and float_compare(currentoutput.badmode_qty, 0.0, precision_rounding=0.000001) > 0.0:
            workordervals['badmode_qty'] = workorder.badmode_qty + currentoutput.badmode_qty
        # 兼容下线产出
        if not workticket and container and workorder.output_manner == 'container':
            self.action_output2container(currentoutput, container)
        if workordervals and len(workordervals) > 0:
            workorder.write(workordervals)
        # 更新序列号信息
        if serialnumber:
            serialvals = {
                'production_id': currentoutput.id, 'workorder_id': workorder.id,
                'output_time': output_time, 'outputuser_id': self.env.user.id
            }
            if mesline.serialnumber_id:
                serialvals['lastone_id'] = mesline.serialnumber_id.id
                currenttime = fields.Datetime.from_string(serialvals['output_time'])
                lasttime = fields.Datetime.from_string(mesline.serialnumber_id.output_time)
                serialvals['output_internal'] = (currenttime - lasttime).seconds / 3600.0
            serialnumber.write(serialvals)
            mesline.write({'serialnumber_id': serialnumber.id})
        _logger.info(u'工单%s完成产出时间:%s', workorder.name, fields.Datetime.now())
        return values


    @api.model
    def action_loading_output_employeelist(self, mesline, workstation, employee=False, equipment=False):
        """加载产出员工清单
        :param mesline:
        :param workstation:
        :param employee:
        :param equipment:
        :return:
        """
        values = {'success': True, 'message': '', 'employeelines': []}
        if employee:
            empvals = {'employee_id': employee.id, 'employee_code': employee.code}
            if workstation:
                empvals['workstation_id'] = workstation.id
            values['employeelines'] = [(0, 0, empvals)]
            return values
        if not mesline or not workstation:
            return values
        employeedomain = [('mesline_id', '=', mesline.id), ('workstation_id', '=', workstation.id)]
        if equipment:
            employeedomain.append(('equipment_id', '=', equipment.id))
        employeelist = self.env['aas.mes.workstation.employee'].search(employeedomain)
        if employeelist and len(employeelist) > 0:
            employeeids, employeelines = [], []
            for temployee in employeelist:
                employeeid, employeecode = temployee.employee_id.id, temployee.employee_id.code
                if employeeid in employeeids:
                    continue
                employeeids.append(employeeid)
                employeelines.append((0, 0, {
                    'workstation_id': workstation.id, 'employee_id': employeeid, 'employee_code': employeecode
                }))
            values['employeelines'] = employeelines
        return values



    @api.model
    def action_loading_consumelist(self, workorder, product, output_qty, workcenter=False):
        """获取工单消耗清单
        :param workorder:
        :param product:
        :param output_qty:
        :param badmode_qty:
        :param workcenter:
        :return:
        """
        values = {'success': True, 'message': '', 'consumedict': {}, 'consumelines': []}
        consumedomain = [('workorder_id', '=', workorder.id), ('product_id', '=', product.id)]
        if workcenter:
            consumedomain += [('workcenter_id', '=', workcenter.id)]
        consumes = self.env['aas.mes.workorder.consume'].search(consumedomain)
        if not consumes or len(consumes) <= 0:
            return values
        tempdict, consumelines = {}, []
        for tconsume in consumes:
            material, wait_qty = tconsume.material_id, tconsume.consume_unit * output_qty
            if not material.virtual_material:
                stockvals = self.action_loading_consume_materiallist(material, wait_qty, workorder.mesline_id)
                if not stockvals.get('success', False):
                    values.update(stockvals)
                    return values
                tempdict[material.id] = {
                    'virtual': False, 'stocklist': stockvals['stocklist'], 'uom_id': material.uom_id.id
                }
            else:
                stockvals = self.action_loading_consume_virtuallist(material, wait_qty, workorder.mesline_id)
                if not stockvals.get('success', False):
                    values.update(stockvals)
                    return values
                tempdict[material.id] = {
                    'virtual': True, 'stocklist': stockvals['stocklist'], 'uom_id': material.uom_id.id
                }
            # 更新消耗清单信息
            temp_qty = output_qty * tconsume.consume_unit + tconsume.consume_qty
            consumelines.append((1, tconsume.id, {'consume_qty': temp_qty}))
        values.update({'consumedict': tempdict, 'consumelines': consumelines})
        return values


    @api.model
    def action_loading_consume_materiallist(self, material, wait_qty, mesline):
        """获取待消耗原料的可供消耗清单
        :param material:
        :param wait_qty:
        :param mesline:
        :return:
        """
        values = {'success': True, 'message': '', 'stocklist': []}
        feeddomain = [('mesline_id', '=', mesline.id), ('material_id', '=', material.id)]
        feedlist = self.env['aas.mes.feedmaterial'].search(feeddomain, order='feed_time')
        if not feedlist and len(feedlist) <= 0:
            values.update({'success': False, 'message': u'物料%s还未上料或已消耗完毕，请联系上料员上料'% material.default_code})
            return values
        tempqty, restqty = 0.0, wait_qty
        for feed in feedlist:
            if float_compare(restqty, 0.0, precision_rounding=0.000001) <= 0.0:
                break
            quants = feed.action_checking_quants()
            if not quants or len(quants) <= 0:
                continue
            if float_compare(feed.material_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                continue
            lotid, lotqty, locationdict = feed.material_lot.id, 0.0, {}
            for quant in quants:
                if float_compare(restqty, 0.0, precision_rounding=0.000001) <= 0.0:
                    break
                qqty = quant.qty
                if float_compare(qqty, restqty, precision_rounding=0.000001) >= 0.0:
                    current_qty = restqty
                else:
                    current_qty = qqty
                lkey = 'L'+str(quant.location_id.id)
                if lkey in locationdict:
                    locationdict[lkey]['product_qty'] += current_qty
                else:
                    locationdict[lkey] = {'location_id': quant.location_id.id, 'product_qty': current_qty}
                restqty -= current_qty
                lotqty += current_qty
            values['stocklist'].append({
                'feed_id': feed.id,
                'lot_id': lotid, 'lot_qty': lotqty, 'locationlist': locationdict.values()
            })
            tempqty += lotqty
        balance_qty = wait_qty - tempqty
        if float_compare(balance_qty, 0.0, precision_rounding=0.000001) > 0.0:
            values.update({'success': False, 'message': u'物料%s上料不足，还差%s'% (material.default_code, balance_qty)})
            return values
        return values



    @api.model
    def action_loading_consume_virtuallist(self, material, wait_qty, mesline):
        """获取虚拟物料可供消耗清单
        :param material:
        :param wait_qty:
        :param mesline:
        :return:
        """
        values = {'success': True, 'message': '', 'stocklist': []}

        tempdomain = [('mesline_id', '=', mesline.id), ('product_id', '=', material.id), ('canconsume', '=', True)]
        outputlist = self.env['aas.production.product'].search(tempdomain, order='output_time')
        if not outputlist or len(outputlist) <= 0:
            return values
        lotids, lotdict = [], {}
        restqty = wait_qty
        for tempoutput in outputlist:
            if float_compare(restqty, 0.0, precision_rounding=0.000001) <= 0.0:
                break
            consume_qty = tempoutput.product_qty - tempoutput.consumed_qty
            if float_compare(restqty, consume_qty, precision_rounding=0.000001) >= 0.0:
                current_qty = consume_qty
            else:
                current_qty = restqty
            lotid = tempoutput.product_lot.id
            lkey = 'L'+str(lotid)
            if lkey not in lotdict:
                lotids.append(lotid)
                lotdict[lkey] = {
                    'lot_id': lotid, 'lot_qty': current_qty,
                    'productionlist': [{'production_id': tempoutput.id, 'product_qty': current_qty}]
                }
            else:
                lotdict[lkey]['lot_qty'] += current_qty
                lotdict[lkey]['productionlist'].append({'production_id': tempoutput.id, 'product_qty': current_qty})
            restqty -= current_qty
        values['stocklist'] = [lotdict['L'+str(templotid)] for templotid in lotids]
        return values


    @api.model
    def action_output2container(self, production, container):
        """产出到容器
        :param production:
        :param container:
        :return:
        """
        values = {'success': True, 'message': ''}
        if not container.isempty:
            _logger.info(u'产出到容器异常，容器%s已经被占用,操作时间：%s', container.name, fields.Datetime.now())
            values.update({'success': False})
            return values
        lotcode = production.output_date.replace('-', '')
        tequipment = production.equipment_id
        if tequipment and tequipment.sequenceno:
            lotcode += tequipment.sequenceno
        product = production.product_id
        productlot = self.env['stock.production.lot'].action_checkout_lot(product.id, lotcode)
        mesline = production.mesline_id
        if container.location_id.id != mesline.location_production_id.id:
            container.action_domove(mesline.location_production_id.id, movenote=u'产出到容器自动调拨')
        containerline = self.env['aas.container.product'].create({
            'container_id': container.id,
            'product_id': product.id, 'product_lot': productlot.id, 'temp_qty': production.product_qty
        })
        containerline.action_stock(production.product_qty)
        production.write({'product_lot': productlot.id, 'container_id': container.id})
        return values



    @api.model
    def action_output2label(self, production):
        """产出到标签
        :param production:
        :return:
        """
        values = {'success': True, 'message': '', 'label_id': '0'}
        lotcode = production.output_date.replace('-', '')
        tequipment = production.equipment_id
        if tequipment and tequipment.sequenceno:
            lotcode += tequipment.sequenceno
        product = production.product_id
        productlot = self.env['stock.production.lot'].action_checkout_lot(product.id, lotcode)
        label = self.env['aas.product.label'].create({
            'product_id': product.id, 'product_lot': productlot.id,
            'product_qty': production.product_qty, 'origin_order': production.workorder_id.name,
            'location_id': production.mesline_id.location_production_id.id
        })
        production_location_id = self.env.ref('stock.location_production').id
        label.action_stock(production_location_id, origin=production.workorder_id.name)
        production.write({'label_id': label.id, 'product_lot': productlot.id})
        values['label_id'] = label.id
        return values


    @api.model
    def action_build_outputlist(self, starttime, finishtime, meslineid=False,
                                workstationid=False, productid=False, equipmentid=False):
        values = {'success': True, 'message': '', 'records': []}
        params = [starttime, finishtime]
        sql_query = """
            SELECT approduct.product_id, approduct.mesline_id, approduct.workstation_id,
            approduct.product_code, approduct.mesline_name, approduct.workstation_name,
            approduct.product_qty, approduct.output_date, approduct.onepass, approduct.qualified
            FROM aas_production_product approduct
            WHERE approduct.output_time >= %s AND approduct.output_time <= %s
        """
        if meslineid:
            params.append(meslineid)
            sql_query += ' AND approduct.mesline_id = %s'
        if workstationid:
            params.append(workstationid)
            sql_query += ' AND approduct.workstation_id = %s'
        if productid:
            params.append(productid)
            sql_query += ' AND approduct.product_id = %s'
        if equipmentid:
            params.append(equipmentid)
            sql_query += ' AND approduct.equipment_id = %s'
        self.env.cr.execute(sql_query, tuple(params))
        records = self.env.cr.dictfetchall()
        if not records or len(records) <= 0:
            return values
        outputdict = {}
        for record in records:
            rkey = 'P-'+str(record['product_id'])+'-'+str(record['mesline_id'])
            rkey += '-'+str(record['workstation_id'])+'-'+record['output_date']
            if rkey in outputdict:
                outputdict[rkey]['product_qty'] += record['product_qty']
                if record['onepass']:
                    outputdict[rkey]['once_qty'] += record['product_qty']
                else:
                    outputdict[rkey]['twice_total_qty'] += record['product_qty']
                    twice_total_qty = outputdict[rkey]['twice_total_qty']
                    if record['qualified']:
                        outputdict[rkey]['twice_qualified_qty'] += record['product_qty']
                    twice_qualified_qty = outputdict[rkey]['twice_qualified_qty']
                    if float_compare(twice_total_qty, 0.0, precision_rounding=0.0000001) <= 0.0:
                        outputdict[rkey]['twice_rate'] = 100.0
                    else:
                        outputdict[rkey]['twice_rate'] = (twice_qualified_qty / twice_total_qty) * 100
                product_qty, once_qty = outputdict[rkey]['product_qty'], outputdict[rkey]['once_qty']
                if float_compare(product_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                    outputdict[rkey]['once_rate'] = 100.0
                else:
                    outputdict[rkey]['once_rate'] = (once_qty / product_qty) * 100
            else:
                tempvals = {
                    'product_id': record['product_id'], 'mesline_id': record['mesline_id'],
                    'workstation_id': record['workstation_id'], 'output_date': record['output_date'],
                    'product_qty': record['product_qty'], 'product_code': record['product_code'],
                    'workstation_name': record['workstation_name'], 'mesline_name': record['mesline_name']
                }
                if record['onepass']:
                    tempvals.update({
                        'once_qty': record['product_qty'], 'twice_total_qty': 0.0,
                        'twice_qualified_qty': 0.0, 'once_rate': 100.0, 'twice_rate': 100.0
                    })
                else:
                    tempvals.update({'once_qty': 0.0, 'twice_total_qty': record['product_qty'], 'once_rate': 100.0})
                    if record['qualified']:
                        tempvals.update({'twice_qualified_qty': record['product_qty'], 'twice_rate': 100.0})
                    else:
                        tempvals.update({'twice_qualified_qty': 0.0, 'twice_rate': 100.0})
                outputdict[rkey] = tempvals
        values['records'] = outputdict.values()
        return values


    @api.model
    def action_loading_materialist_oneinall(self, production, productkeys=[], materialkeys=[]):
        """
        获取最终原料信息
        :param production:
        :param productkeys:
        :param materialkeys:
        :return:
        """
        if not production.material_lines or len(production.material_lines) <= 0:
            return
        for pmaterial in production.material_lines:
            productid, productlot = pmaterial.material_id.id, pmaterial.material_lot.id
            mkey = str(production.mesline_id.id)+'-'+str(productid)+'-'+str(productlot)
            if pmaterial.material_id.ismaterial:
                if mkey not in materialkeys:
                    materialkeys.append(mkey)
                continue
            tempdomain = [('product_id', '=', productid), ('product_lot', '=', productlot)]
            productionlist = self.env['aas.production.product'].search(tempdomain)
            if not productionlist or len(productionlist) <= 0:
                if mkey not in materialkeys:
                    materialkeys.append(mkey)
                continue
            for tproduction in productionlist:
                productid, productlot = tproduction.product_id.id, tproduction.product_lot.id
                pkey = str(tproduction.mesline_id.id)+'-'+str(productid)+'-'+str(productlot)
                if pkey in productkeys:
                    continue
                else:
                    productkeys.append(pkey)
                    self.action_loading_materialist_oneinall(tproduction, productkeys, materialkeys)




# 产出原料消耗
class AASPRoductionMaterial(models.Model):
    _name = 'aas.production.material'
    _description = 'AAS Production Material'

    production_id = fields.Many2one(comodel_name='aas.production.product', string=u'产出成品')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料')
    material_lot = fields.Many2one(comodel_name='stock.production.lot', string=u'批次')
    material_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

# 产出时操作员工
class AASProductionEmployee(models.Model):
    _name = 'aas.production.employee'
    _description = 'AAS Production Employee'

    production_id = fields.Many2one(comodel_name='aas.production.product', string=u'产出成品')
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工')
    employee_code = fields.Char(string=u'编码', copy=False)
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位')
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)


# 生产不良信息
class AASProductionBadmode(models.Model):
    _name = 'aas.production.badmode'
    _description = 'AAS Production Badmode'


    production_id = fields.Many2one(comodel_name='aas.production.product', string=u'产出成品')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', index=True)
    schedule_id = fields.Many2one(comodel_name='aas.mes.schedule', string=u'班次', index=True)
    workcenter_id = fields.Many2one(comodel_name='aas.mes.routing.line', string=u'工序', index=True)
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', index=True)
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', index=True)

    workorder_id = fields.Many2one(comodel_name='aas.mes.workorder', string=u'工单', index=True)
    workticket_id = fields.Many2one(comodel_name='aas.mes.workticket', string=u'工票', index=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', index=True)
    badmode_id = fields.Many2one(comodel_name='aas.mes.badmode', string=u'不良模式', index=True)
    badmode_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    badmode_date = fields.Char(string=u'不良日期', copy=False)
    badmode_time = fields.Datetime(string=u'不良时间', default=fields.Datetime.now, copy=False)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)

    material_lines = fields.One2many(comodel_name='aas.production.badmode.material', inverse_name='production_badmode_id', string=u'原料清单')


# 生产不良的原料信息
class AASProductionBadmodeMaterial(models.Model):
    _name = 'aas.production.badmode.material'
    _description = 'AAS Production Badmode Material'

    production_badmode_id = fields.Many2one(comodel_name='aas.production.badmode', string=u'生产不良')
    material_id = fields.Many2one(comodel_name='product.product', string=u'原料')
    material_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    company_id = fields.Many2one('res.company', string=u'公司', default=lambda self: self.env.user.company_id)







# 成品标签记录
class AASMESProductionLabel(models.Model):
    _name = 'aas.mes.production.label'
    _description = 'AAS MES Production Label'
    _rec_name = 'label_id'
    _order = 'id desc'

    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', index=True)
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', index=True)
    lot_id = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', index=True)
    location_id = fields.Many2one(comodel_name='stock.location', string=u'库位', index=True)
    action_time = fields.Datetime(string=u'时间', default=fields.Datetime.now, copy=False)
    action_date = fields.Char(string=u'日期', copy=False, index=True)
    customer_code = fields.Char(string=u'客户编码', copy=False)
    product_code = fields.Char(string=u'产品编码', copy=False)
    isserialnumber = fields.Boolean(string=u'是否序列号', default=False, copy=False)
    operator_id = fields.Many2one(comodel_name='res.users', string=u'用户', index=True)
    employee_id = fields.Many2one(comodel_name='aas.hr.employee', string=u'员工', index=True)
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', index=True)
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)
    company_id = fields.Many2one(comodel_name='res.company', string=u'公司', default=lambda self: self.env.user.company_id)


    @api.multi
    def action_show_serialnumbers(self):
        self.ensure_one()
        view_form = self.env.ref('aas_mes.view_form_aas_mes_serialnumber')
        view_tree = self.env.ref('aas_mes.view_tree_aas_mes_serialnumber')
        return {
            'name': u"成品清单",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'aas.mes.serialnumber',
            'views': [(view_tree.id, 'tree'), (view_form.id, 'form')],
            'target': 'self',
            'context': self.env.context,
            'domain': "[('label_id','=',"+str(self.label_id.id)+")]"
        }


    @api.multi
    def action_update_serialnumber(self):
        self.ensure_one()
        wizard = self.env['aas.mes.production.label.update.serialnumber.wizard'].create({
            'plabel_id': self.id, 'label_id': self.label_id.id,
            'product_id': self.label_id.product_id.id, 'lot_id': self.label_id.product_lot.id,
            'product_qty': self.label_id.product_qty
        })
        view_form = self.env.ref('aas_mes.view_form_aas_mes_production_label_update_serialnumber_wizard')
        return {
            'name': u"更新标签序列号",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.production.label.update.serialnumber.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }

    @api.multi
    def action_destroy(self):
        self.ensure_one()
        if self.location_id.id != self.label_id.location_id.id:
            raise UserError(u'标签库位已发生变化，不可以解绑！')
        wizard = self.env['aas.mes.production.label.destroy.wizard'].create({
            'plabel_id': self.id, 'product_qty': self.label_id.product_qty,
            'product_id': self.label_id.product_id.id, 'lot_id': self.label_id.product_lot.id
        })
        view_form = self.env.ref('aas_mes.view_form_aas_mes_production_label_destroy_wizard')
        return {
            'name': u"解除标签绑定",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.production.label.destroy.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }



 # 追溯消耗明细
class StockMove(models.Model):
    _inherit = 'stock.move'

    production_id = fields.Many2one(comodel_name='aas.production.product', string=u'成品产出')





########################################## 向导 ##############################################

# 生产产出以及优率查询
class AASMESProductionOutputQueryWizard(models.TransientModel):
    _name = 'aas.mes.production.output.query.wizard'
    _description = 'AAS MES Production Output Query Wizard'

    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='cascade')
    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='cascade')
    time_start = fields.Datetime(string=u'开始时间', copy=False)
    time_finish = fields.Datetime(string=u'结束时间', copy=False)
    query_lines = fields.One2many(comodel_name='aas.mes.production.output.query.line.wizard', inverse_name='wizard_id', string=u'查询明细')

    file_name = fields.Char(string=u'文件名称')
    file_data = fields.Binary(string=u'文件', readonly='1')
    file_exported = fields.Boolean(string=u'是否导出', default=False)

    @api.model
    def default_get(self, fields_list):
        defaults = super(AASMESProductionOutputQueryWizard,self).default_get(fields_list)
        chinatime = fields.Datetime.to_china_time(fields.Datetime.now())
        startime = chinatime.replace(hour=0, minute=0, second=0)
        finishtime = chinatime.replace(hour=23, minute=59, second=59)
        defaults.update({
            'time_start': fields.Datetime.to_utc_string(startime, 'Asia/Shanghai'),
            'time_finish': fields.Datetime.to_utc_string(finishtime, 'Asia/Shanghai')
        })
        return defaults


    @api.multi
    def action_query(self):
        """查询产出汇总数据
        :return:
        """
        self.ensure_one()
        starttime, finishtime = self.time_start, self.time_finish
        meslineid = False if not self.mesline_id else self.mesline_id.id
        workstationid = False if not self.workstation_id else self.workstation_id.id
        productid = False if not self.product_id else self.product_id.id
        equipmentid = False if not self.equipment_id else self.equipment_id.id
        tempvals = self.env['aas.production.product'].action_build_outputlist(starttime, finishtime, meslineid,
                                                                              workstationid, productid, equipmentid)
        records = tempvals.get('records', [])
        if records and len(records) > 0:
            querylines = []
            for record in records:
                querylines.append((0, 0, {
                    'product_id': record['product_id'], 'product_qty': record['product_qty'],
                    'mesline_id': record['mesline_id'], 'workstation_id': record['workstation_id'],
                    'output_date': record['output_date'], 'once_rate': record['once_rate'],
                    'twice_rate': record['twice_rate'], 'once_qty': record['once_qty'],
                    'twice_total_qty': record['twice_total_qty'], 'twice_qualified_qty': record['twice_qualified_qty']
                }))
            self.write({'query_lines': querylines})
        view_form = self.env.ref('aas_mes.view_form_aas_mes_production_output_query_result')
        return {
            'name': u"查询结果",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.production.output.query.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context
        }


    @api.multi
    def action_dataexport(self):
        self.ensure_one()
        if not self.query_lines or len(self.query_lines) <= 0:
            raise UserError(u'暂时没有数据可以导出！')
        fieldlines = ['output_date', 'mesline_id', 'product_id', 'workstation_id', 'product_qty', 'once_qty',
                      'once_rate', 'twice_total_qty', 'twice_qualified_qty', 'twice_rate']
        headerlines = [u'日期', u'产线', u'产品', u'工位', u'总数', u'一次合格数量', u'一次优率', u'二次总数', u'二次合格数量',
                       u'二次优率']
        records, rows = self.query_lines.read(fields=fieldlines), []
        file_name = u"产出优率%s"% fields.Datetime.to_china_today().replace('-', '')
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet(file_name)
        base_style = xlwt.easyxf('align: wrap yes')
        for record in records:
            tvalue, row = '', []
            for fkey in fieldlines:
                tval = record.get(fkey)
                if tval:
                    if type(tval) == tuple:
                        tvalue = tval[1]
                    else:
                        tvalue = tval
                else:
                    tvalue = None
                row.append(tvalue)
            rows.append(row)
        for i, fheader in enumerate(headerlines):
            worksheet.write(0, i, fheader)
            # around 220 pixels
            worksheet.col(i).width = 8000
        for row_index, row in enumerate(rows):
            for cell_index, cell_value in enumerate(row):
                worksheet.write(row_index + 1, cell_index, cell_value, base_style)
        fp = StringIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        out=base64.encodestring(data)
        file_name = file_name+'.xls'
        self.write({'file_data': out, 'file_name': file_name, 'file_exported': True})
        view_form = self.env.ref('aas_mes.view_form_aas_mes_production_output_query_result')
        return {
            'name': u"查询结果",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.production.output.query.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context
        }











class AASMESProductionOutputQueryLineWizard(models.TransientModel):
    _name = 'aas.mes.production.output.query.line.wizard'
    _description = 'AAS MES Production Output Query Line Wizard'
    _order = 'output_date desc,mesline_id,workstation_id,product_id'

    wizard_id = fields.Many2one(comodel_name='aas.mes.production.output.query.wizard', string='Wizard', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    product_qty = fields.Float(string=u'总数', default=0.0)
    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='cascade')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='cascade')
    output_date = fields.Char(string=u'日期', copy=False)
    once_qty = fields.Float(string=u'一次合格数量', default=0.0)
    twice_total_qty = fields.Float(string=u'二次总数', default=0.0)
    twice_qualified_qty = fields.Float(string=u'二次合格数量', default=0.0)
    once_rate = fields.Float(string=u'一次优率', default=0.0)
    twice_rate = fields.Float(string=u'二次优率', default=0.0)



class AASMESProductionLabelUpdateSerialnumberWizard(models.TransientModel):
    _name = 'aas.mes.production.label.update.serialnumber.wizard'
    _description = 'AAS MES Production Label Update Serialnumber Wizard'

    plabel_id = fields.Many2one(comodel_name='aas.mes.production.label', string=u'标签', ondelete='cascade')
    label_id = fields.Many2one(comodel_name='aas.product.label', string=u'标签', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    lot_id = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', index=True)
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    add_lines = fields.One2many('aas.mes.production.label.update.addserial.wizard', inverse_name='wizard_id', string=u'新增明细')
    del_lines = fields.One2many('aas.mes.production.label.update.delserial.wizard', inverse_name='wizard_id', string=u'删除明细')

    @api.one
    def action_done(self):
        tlabel, plabel = self.label_id, self.plabel_id
        addcount = 0 if not self.add_lines else len(self.add_lines)
        delcount = 0 if not self.del_lines else len(self.del_lines)
        if addcount <= 0 and delcount <= 0:
            raise UserError(u'请先设置需要新增或则清理的序列号！')
        if addcount > 0:
            aserialnumberlist = self.env['aas.mes.serialnumber']
            for tserial in self.add_lines:
                aserialnumberlist |= tserial.serialnumber_id
            aserialnumberlist.write({'label_id': tlabel.id, 'product_lot': tlabel.product_lot.id})
        if delcount > 0:
            dserialnumberlist, doperationlist = self.env['aas.mes.serialnumber'], self.env['aas.mes.operation']
            for tserial in self.del_lines:
                dserialnumberlist |= tserial.serialnumber_id
                doperationlist |= tserial.serialnumber_id.operation_id
            dserialnumberlist.write({'label_id': False, 'product_lot': False})
            doperationlist.write({'gp12_check': False, 'gp12_record_id': False, 'gp12_date': False, 'gp12_time': False})
        if addcount == delcount:
            return
        labelocation = tlabel.location_id
        pdtlocation = self.env.ref('stock.location_production')
        movevals = {
            'name': tlabel.name, 'product_id': tlabel.product_id.id,
            'company_id': self.env.user.company_id.id, 'product_uom': tlabel.product_id.uom_id.id,
            'create_date': fields.Datetime.now(), 'restrict_lot_id': tlabel.product_lot.id,
            'product_uom_qty': abs(addcount - delcount)
        }
        if addcount > delcount:
            movevals.update({'location_id': pdtlocation.id, 'location_dest_id': labelocation.id})
        else:
            movevals.update({'location_id': labelocation.id, 'location_dest_id': pdtlocation.id})
        self.env['stock.move'].create(movevals).action_done()
        temp_qty = tlabel.product_qty + addcount - delcount
        plabel.write({'product_qty': temp_qty})
        tlabel.write({'product_qty': temp_qty})



class AASMESProductionLabelUpdateAddserialWizard(models.TransientModel):
    _name = 'aas.mes.production.label.update.addserial.wizard'
    _description = 'AAS MES Production Label Update Addserial Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.mes.production.label.update.serialnumber.wizard', string='Wizard', ondelete='cascade')
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    sequence_code = fields.Char(string=u'序列编码', copy=False)

    @api.onchange('serialnumber_id')
    def action_change_serialnumber(self):
        if not self.serialnumber_id:
            self.product_id, self.sequence_code = False, False
        else:
            self.product_id = self.serialnumber_id.product_id.id
            self.sequence_code = self.serialnumber_id.sequence_code

    @api.model
    def create(self, vals):
        record = super(AASMESProductionLabelUpdateAddserialWizard, self).create(vals)
        record.write({
            'product_id': record.serialnumber_id.product_id.id,
            'sequence_code': record.serialnumber_id.sequence_code
        })
        return record


    @api.one
    @api.constrains('serialnumber_id')
    def action_check_serialnumber(self):
        plabel = self.wizard_id.plabel_id
        serialnumber = self.serialnumber_id
        if serialnumber.label_id:
            raise ValidationError(u'序列号%s已绑定在标签%中，不可以随意更换标签'% (serialnumber.name, serialnumber.label_id.name))
        if plabel.label_id.product_id.id != serialnumber.product_id.id:
            raise ValidationError(u'序列号%s与标签%s的产品不一致，不可以添加到此标签中！'% (serialnumber.name, plabel.label_id.name))
        toperation = serialnumber.operation_id
        if not toperation.gp12_check:
            raise ValidationError(u'序列号%s还未通过GP12检测，不可以添加到产出标签！'% serialnumber.name)



class AASMESProductionLabelUpdateDelserialWizard(models.TransientModel):
    _name = 'aas.mes.production.label.update.delserial.wizard'
    _description = 'AAS MES Production Label Update Delserial Wizard'

    wizard_id = fields.Many2one(comodel_name='aas.mes.production.label.update.serialnumber.wizard', string='Wizard', ondelete='cascade')
    serialnumber_id = fields.Many2one(comodel_name='aas.mes.serialnumber', string=u'序列号', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='restrict')
    sequence_code = fields.Char(string=u'序列编码', copy=False)


    @api.onchange('serialnumber_id')
    def action_change_serialnumber(self):
        if not self.serialnumber_id:
            self.product_id, self.sequence_code = False, False
        else:
            self.product_id = self.serialnumber_id.product_id.id
            self.sequence_code = self.serialnumber_id.sequence_code

    @api.model
    def create(self, vals):
        record = super(AASMESProductionLabelUpdateDelserialWizard, self).create(vals)
        record.write({
            'product_id': record.serialnumber_id.product_id.id,
            'sequence_code': record.serialnumber_id.sequence_code
        })
        return record

class AASMESProductionLabelDestroyWizard(models.TransientModel):
    _name = 'aas.mes.production.label.destroy.wizard'
    _description = 'AAS MES Production Label Destroy Wizard'

    plabel_id = fields.Many2one(comodel_name='aas.mes.production.label', string=u'标签', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string=u'产品', ondelete='cascade')
    lot_id = fields.Many2one(comodel_name='stock.production.lot', string=u'批次', index=True)
    product_qty = fields.Float(string=u'数量', digits=dp.get_precision('Product Unit of Measure'), default=0.0)

    @api.one
    def action_done(self):
        tlabel = self.plabel_id.label_id
        operationlist = self.env['aas.mes.operation']
        serialnumberlist = self.env['aas.mes.serialnumber'].search([('label_id', '=', tlabel.id)])
        if serialnumberlist and len(serialnumberlist) > 0:
            for tserialnumber in serialnumberlist:
                operationlist |= tserialnumber.operation_id
            serialnumberlist.write({'label_id': False})
        if operationlist and len(operationlist) > 0:
            operationlist.write({'gp12_check': False, 'gp12_record_id': False, 'gp12_date': False, 'gp12_time': False})
        if float_compare(tlabel.product_qty, 0.0, precision_rounding=0.000001) > 0.0:
            labelocation, pdtlocation = tlabel.location_id, self.env.ref('stock.location_production')
            self.env['stock.move'].create({
                'name': tlabel.name, 'product_id': tlabel.product_id.id,
                'company_id': self.env.user.company_id.id, 'product_uom': tlabel.product_id.uom_id.id,
                'create_date': fields.Datetime.now(), 'restrict_lot_id': tlabel.product_lot.id,
                'product_uom_qty': tlabel.product_qty, 'location_id': labelocation.id, 'location_dest_id': pdtlocation.id
            }).action_done()
        tlabel.write({'product_qty': 0.0})
        self.plabel_id.unlink()









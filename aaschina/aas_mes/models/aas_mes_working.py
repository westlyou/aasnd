# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-8-25 11:05
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

class AASEquipmentEquipment(models.Model):
    _inherit = 'aas.equipment.equipment'

    mesline_id = fields.Many2one(comodel_name='aas.mes.line', string=u'产线', ondelete='restrict')
    workstation_id = fields.Many2one(comodel_name='aas.mes.workstation', string=u'工位', ondelete='restrict')

    @api.one
    def doset_mesline_workstation(self, mesline_id, workstation_id):
        equipmentrecords = self.env['aas.mes.workstation.equipment'].search([('equipment_id', '=', self.id)])
        if equipmentrecords and len(equipmentrecords) > 0:
            equipmentrecords.unlink()
        self.env['aas.mes.workstation.equipment'].create({
            'workstation_id': workstation_id, 'mesline_id': mesline_id, 'equipment_id': self.id
        })
        self.write({'mesline_id': mesline_id, 'workstation_id': workstation_id})

    @api.multi
    def action_mesline_workstation(self):
        """
        更新产线工位
        :return:
        """
        self.ensure_one()
        wizard = self.env['aas.mes.equipment.workstation.wizard'].create({
            'equipment_id': self.id
        })
        view_form = self.env.ref('aas_mes.view_form_aas_mes_equipment_workstation_wizard')
        return {
            'name': u"产线工位",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'aas.mes.equipment.workstation.wizard',
            'views': [(view_form.id, 'form')],
            'view_id': view_form.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': self.env.context
        }


    @api.model
    def get_redis_settings(self, name):
        """Redis接口
        :param name:
        :return:
        """
        return self.env['aas.base.redis'].get_redis_settings(name)

    @api.model
    def action_workstation_scanning(self, equipment_code, employee_barcode):
        """工控工位扫码上岗
        :param equipment_code:
        :param employee_barcode:
        :return:
        """
        return self.env['aas.mes.work.attendance'].action_workstation_scanning(equipment_code, employee_barcode)

    @api.model
    def get_workstation_materiallist(self, equipment_code):
        """工位获取上料清单
        :param equipment_code:
        :return:
        """
        return self.env['aas.mes.feedmaterial'].get_workstation_materiallist(equipment_code)

    @api.model
    def action_feed_onstationclient(self, equipment_code, barcode):
        """工控工位上料
        :param equipment_code:
        :param barcode:
        :return:
        """
        return self.env['aas.mes.feedmaterial'].action_feed_onstationclient(equipment_code, barcode)

    @api.model
    def get_virtual_materiallist(self, equipment_code, workorderid=None):
        """工位获取虚拟件清单
        :param equipment_code:
        :param workorderid: 子工单条码id
        :return:
        """
        return self.env['aas.mes.workorder'].get_virtual_materiallist(equipment_code, workorderid=workorderid)

    @api.model
    def get_workstation_workticket(self, equipment_code, barcode):
        """工位获取工票信息
        :param equipment_code:
        :param barcode:
        :return:
        """
        return self.env['aas.mes.workticket'].get_workstation_workticket(equipment_code, barcode)

    @api.model
    def action_workticket_start_onstationclient(self, workticket_id, equipment_id):
        """工位上工票开工
        :param workticket_id:
        :param equipment_id:
        :return:
        """
        return self.env['aas.mes.workticket'].action_workticket_start_onstationclient(workticket_id, equipment_id)

    @api.model
    def action_workticket_finish_onstationclient(self, workticket_id, equipment_id, commit_qty, badmode_lines=[], container_id=None):
        """工位上工票报工
        :param workticket_id:
        :param equipment_id:
        :param commit_qty:
        :param badmode_lines:
        :param container_id:
        :return:
        """
        return self.env['aas.mes.workticket'].action_workticket_finish_onstationclient(workticket_id, equipment_id, commit_qty, badmode_lines, container_id)

    @api.model
    def action_container_scanning(self, barcode):
        """工位上扫描容器
        :param barcode:
        :return:
        """
        return self.env['aas.container'].action_scanning(barcode)

    @api.model
    def get_employeelist(self, equipment_code):
        """工控工位设备上获取员工清单
        :param equipment_code:
        :return:
        """
        return self.env['aas.mes.workstation'].get_employeelist(equipment_code)

    @api.model
    def action_functiontest(self, equipment_code, serialnumber, operation_pass, operate_result):
        """添加功能测试记录
        :param equipment_code:
        :param serialnumber:
        :param operation_pass:
        :param operate_result:
        :return:
        """
        return self.env['aas.mes.operation.record'].action_functiontest(equipment_code, serialnumber, operation_pass, operate_result)

    @api.model
    def loading_consumelist_onclient(self, workorder_id, workcenter_id):
        """工控工位获取消耗明细
        :param workorder_id:
        :param workcenter_id:
        :return:
        """
        return self.env['aas.mes.workorder.consume'].loading_consumelist_onclient(workorder_id, workcenter_id)

    @api.model
    def action_vtproduct_output(self, workstation_id, workorder_id, product_id, output_qty, badmode_lines=[]):
        """工控工位虚拟件产出
        :param workstation_id:
        :param workorder_id:
        :param product_id:
        :param output_qty:
        :param badmode_lines:
        :return:
        """
        return self.env['aas.mes.workorder'].action_vtproduct_output(workstation_id, workorder_id,
                                                                     product_id, output_qty, badmode_lines=badmode_lines)

    @api.model
    def action_loading_badmodelist(self, equipment_code):
        """工位上工票报工时获取不良模式清单
        :param equipment_code:
        :return:
        """
        return self.env['aas.mes.workstation'].action_loading_badmodelist(equipment_code)

    @api.model
    def action_loading_workstationlist(self):
        """获取产线工位清单
        :return:
        """
        return self.env['aas.mes.line'].action_loading_workstationlist()

    @api.model
    def action_setequipment_workstation(self, equipment_code, mesline_id, workstation_id):
        """更新设备产线和工位
        :param equipment_code:
        :param mesline_id:
        :param workstation_id:
        :return:
        """
        values = {'success': True, 'message': ''}
        tequipment = self.env['aas.equipment.equipment'].search([('code', '=', equipment_code)], limit=1)
        if not tequipment:
            values.update({'success': False, 'message': u'系统未获取到相应设备，请仔细检查设备编码是否正确！'})
            return values
        tequipment.doset_mesline_workstation(mesline_id, workstation_id)
        return values

    @api.model
    def get_printer_list(self):
        """
        获取标签打印机清单
        :return:
        """
        values = {'success': True, 'message': '', 'printers': []}
        printerlist = self.env['aas.label.printer'].search([])
        if not printerlist or len(printerlist) <= 0:
            return values
        values['printers'] = [{
            'printer_id': printer.id, 'printer_name': printer.name
        } for printer in printerlist]
        return values


    @api.model
    def action_print_labels(self, printerid, res_model, res_ids=[]):
        """
        打印标签
        :param printerid:
        :param res_model:
        :param res_ids:
        :return:
        """
        values = {'success': True, 'message': '', 'printer': '', 'serverurl': '', 'records': []}
        if not res_model:
            values.update({'success': False, 'message': u'请设置有效的打印对象！'})
            return values
        if not res_ids or len(res_ids) <= 0:
            values.update({'success': False, 'message': u'请设置有效的打印对象！'})
            return values
        return self.env[res_model].action_print_label(printerid, res_ids)

    @api.model
    def loading_producttest_onclient(self, productid, workcenterid):
        """客户端获取检测参数信息
        :param productid:
        :param workcenterid:
        :return:
        """
        return self.env['aas.mes.producttest'].loading_producttest(productid, workcenterid)

    @api.model
    def action_producttest_onclient(self, equipmentid, producttestid, parameters,
                                    testtype='firstone', instrument=False, fixture=False):
        """客户端添加首末件抽检操作
        :param equipmentid:
        :param producttestid:
        :param parameters:
        :param testtype:
        :param instrument:
        :param fixture:
        :return:
        """
        return self.env['aas.mes.producttest'].action_producttest(equipmentid, producttestid, parameters,
                                                                  testtype=testtype, instrument=instrument, fixture=fixture)




#######################向导#################################


# 设备产线和工位设置
class AASMESEquipmentWorkstationWizard(models.TransientModel):
    _name = 'aas.mes.equipment.workstation.wizard'
    _description = 'AAS MES Equipment Workstation Wizard'

    equipment_id = fields.Many2one(comodel_name='aas.equipment.equipment', string=u'设备', ondelete='cascade')
    mesline_workstation = fields.Many2one(comodel_name='aas.mes.line.workstation', string=u'产线工位', ondelete='cascade')

    @api.one
    def action_done(self):
        if not self.mesline_workstation:
            raise UserError(u'请先设置好产线工位！')
        self.equipment_id.doset_mesline_workstation(self.mesline_workstation.mesline_id.id,
                                                    self.mesline_workstation.workstation_id.id)
# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2018-5-31 20:53
"""

import xlwt
import logging
from cStringIO import StringIO


from odoo import http, fields
from odoo.http import request
from odoo.tools.float_utils import float_compare, float_repr
from odoo.exceptions import AccessDenied, UserError, ValidationError

logger = logging.getLogger(__name__)

class AASMESYieldReportController(http.Controller):

    def action_loading_badmodelist(self, mesline, workdate):
        badmodeids, badmodelist = [], []
        orderdomain = [('mesline_id', '=', mesline.id), ('plan_date', '=', workdate), ('state', '!=', 'draft')]
        workorderlist = request.env['aas.mes.workorder'].search(orderdomain)
        if not workorderlist or len(workorderlist) <= 0:
            return badmodelist
        workorderids = workorderlist.ids
        if mesline.line_type == 'flowing':
            reworklist = request.env['aas.mes.rework'].search([('workorder_id', 'in', workorderids)])
            if not reworklist or len(reworklist) <= 0:
                return badmodelist
            for rework in reworklist:
                badmode = rework.badmode_id
                if badmode.id in badmodeids:
                    continue
                badmodeids.append(badmode.id)
                badmodelist.append({'badmode_id': badmode.id, 'badmode_name': badmode.name})
        else:
            sql_query = """
            SELECT id, name FROM aas_mes_badmode WHERE id in (
               SELECT DISTINCT badmode_id FROM aas_production_badmode WHERE workorder_id in %s
            )
            """
            request.env.cr.execute(sql_query, (tuple(workorderids), ))
            badmodes = request.env.cr.dictfetchall()
            if badmodes and len(badmodes) > 0:
                for badmode in badmodes:
                    badmodelist.append({'badmode_id': badmode['id'], 'badmode_name': badmode['name']})
        return badmodelist


    def action_loading_workorder_badmodelist(self, workorder):
        values = {'badmodes': {}, 'once_qty': 0, 'twice_qty': 0, 'more_qty': 0, 'total_qty': 0}
        mesline = workorder.mesline_id
        if mesline.line_type == 'flowing':
            reworklist = request.env['aas.mes.rework'].search([('workorder_id', '=', workorder.id)])
            if not reworklist or len(reworklist) <= 0:
                return values
            serialdict = {}
            for rework in reworklist:
                bkey, serialnumber = rework.badmode_id.id, rework.serialnumber_id
                if bkey in values['badmodes']:
                  values['badmodes'][bkey] += 1
                else:
                  values['badmodes'][bkey] = 1
                skey = serialnumber.id
                if skey not in serialdict:
                    serialdict[skey] = 1
                else:
                    serialdict[skey] += 1
            for tkey, tcount in serialdict.items():
                if tcount == 1:
                    values['once_qty'] += 1
                elif tcount == 2:
                    values['twice_qty'] += 1
                else:
                    values['more_qty'] += 1
                values['total_qty'] += 1
        else:
            if not workorder.badmode_lines or len(workorder.badmode_lines) <= 0:
                return values
            for bline in workorder.badmode_lines:
                bkey = bline.badmode_id.id
                if bkey in values['badmodes']:
                  values['badmodes'][bkey] += bline.badmode_qty
                else:
                  values['badmodes'][bkey] = bline.badmode_qty
            values['total_qty'] = workorder.badmode_qty
        return values



    @http.route('/aasmes/yieldreport/<int:meslineid>', type='http', auth="user")
    def aasmes_yieldreport_list(self, meslineid):
        loginuser = request.env.user
        mesline = request.env['aas.mes.line'].browse(meslineid)
        values = {
            'success': True, 'message': '', 'checker': loginuser.name,
            'workorderlist': [], 'mesline_id': meslineid, 'mesline_name': mesline.name,
            'flowingline': True if mesline.line_type == 'flowing' else False,
            'linetype': mesline.line_type
        }
        return request.render('aas_mes.aas_yieldreport_list', values)


    @http.route('/aasmes/yieldreport/badmodelist', type='json', auth="user")
    def aasmes_yieldreport_badmodelist(self, meslineid, workdate):
        values = {'success': True, 'message': '', 'badmodelist': []}
        mesline = request.env['aas.mes.line'].browse(meslineid)
        if not mesline:
            values.update({'success': False, 'message': u'产线异常，请检查是否访问的是有效的产线！'})
            return values
        values['badmodelist'] = self.action_loading_badmodelist(mesline, workdate)
        return values



    @http.route('/aasmes/yieldreport/workorderlist', type='json', auth="user")
    def aasmes_yieldreport_workorderlist(self, meslineid, page=1, productcode=None, workorder=None, workdate=None):
        values = {
            'success': True, 'message': '', 'workorderlist': [],
            'countcontent': '0/0', 'total': '0', 'linetype': 'flowing'
        }
        offset = (page-1) * 100
        firstindex, lastindex = offset + 1, offset + 100
        tempdomain = [('mesline_id', '=', meslineid), ('state', '!=', 'draft')]
        if productcode:
            pproduct = request.env['product.product'].search([('default_code', '=', productcode)], limit=1)
            if not pproduct:
                values.update({'success': False, 'message': u'产品编码有误，请仔细核对！'})
                return values
            tempdomain.append(('product_id', '=', pproduct.id))
        if workorder:
            tempdomain.append(('name', 'ilike', '%'+workorder+'%'))
        if workdate:
            tempdomain.append(('plan_date', '=', workdate))
        totalcount = request.env['aas.mes.workorder'].search_count(tempdomain)
        values['total'] = totalcount
        if totalcount < lastindex:
            lastindex = totalcount
        if totalcount == 0:
            firstindex = 0
        values['countcontent'] = str(firstindex)+'-'+str(lastindex)+'/'+str(totalcount)
        workorderlines = request.env['aas.mes.workorder'].search(tempdomain, offset=offset, order='id desc', limit=100)
        if not workorderlines or len(workorderlines) <= 0:
            return values
        workorderlist, mesline = [], False
        for workorder in workorderlines:
            employee_name, equipment_name, producer, equipment = '', '', workorder.producer_id, workorder.equipment_id
            if producer:
                employee_name = producer.name + '[' + producer.code + ']'
            if equipment:
                equipment_name = equipment.name + '[' + equipment.code + ']'
            ordervals = {
                'plan_date': '' if not workorder.plan_date else workorder.plan_date,
                'plan_schedule': '' if not workorder.plan_schedule else workorder.plan_schedule.name,
                'workorder_id': workorder.id, 'workorder_name': workorder.name,
                'mainorder_name': '' if not workorder.mainorder_id else workorder.mainorder_id.name,
                'product_code': workorder.product_code,
                'produce_start': fields.Datetime.to_china_string(workorder.produce_start),
                'produce_finish': fields.Datetime.to_china_string(workorder.produce_finish),
                'input_qty': workorder.input_qty, 'output_qty': workorder.output_qty,
                'reach_rate': workorder.output_qty / workorder.input_qty * 100.0,
                'badmode_qty': workorder.badmode_qty, 'yield_actual': 100.0,
                'badmodes': {}, 'once_qty': 0, 'twice_qty': 0, 'more_qty': 0,
                'employee_name': employee_name, 'equipment_name': equipment_name
            }
            tempbadmodevals = self.action_loading_workorder_badmodelist(workorder)
            ordervals.update({
                'badmodes': tempbadmodevals['badmodes'], 'once_qty': tempbadmodevals['once_qty'],
                'twice_qty': tempbadmodevals['twice_qty'], 'more_qty': tempbadmodevals['more_qty'],
                'badmode_qty': tempbadmodevals['total_qty']
            })
            if float_compare(workorder.output_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                yield_actual = 0.0
            else:
                yield_actual = workorder.output_qty / (ordervals['badmode_qty'] + workorder.output_qty) * 100.0
            ordervals['yield_actual'] = yield_actual
            workorderlist.append(ordervals)
            mesline = workorder.mesline_id
        values['workorderlist'] = workorderlist
        values['linetype'] = mesline.line_type
        return values



    @http.route('/aasmes/yieldreport/exportchecking', type='json', auth="user")
    def aasmes_yieldreport_exportchecking(self, meslineid, workdate=None, productcode=None, workorder=None):
        values = {'success': True, 'message': ''}
        mesline = request.env['aas.mes.line'].browse(meslineid)
        tempdomain = [('mesline_id', '=', meslineid), ('state', '!=', 'draft')]
        if not mesline:
            values.update({'success': False, 'message': u'产线异常，请检查是否访问的是有效的产线！'})
            return values
        if productcode:
            pproduct = request.env['product.product'].search([('default_code', '=', productcode)], limit=1)
            if not pproduct:
                values.update({'success': False, 'message': u'产品编码有误，请仔细核对！'})
                return values
            tempdomain.append(('product_id', '=', pproduct.id))
        if workorder:
            tempdomain.append(('name', 'ilike', '%'+workorder+'%'))
        if workdate:
            tempdomain += [('plan_date', '=', workdate)]
        totalcount = request.env['aas.mes.workorder'].search_count(tempdomain)
        if totalcount <= 0:
            values.update({'success': False, 'message': u'未获取需要导出的数据！'})
            return values
        return values

    @http.route('/aasmes/yieldreport/export', type='http', auth="user")
    def aasmes_yieldreport_export(self, meslineid, workorderidstr=None, workdate=None, productcode=None, workorder=None):
        mesline = request.env['aas.mes.line'].browse(int(meslineid))
        badmodelist, badmodeids = self.action_loading_badmodelist(mesline, workdate), []
        if workorderidstr:
            workorderids = [int(workorderid) for workorderid in workorderidstr.split('-')]
            workorderlist = request.env['aas.mes.workorder'].browse(workorderids)
        else:
            tempdomain = [('mesline_id', '=', mesline.id), ('state', '!=', 'draft')]
            if productcode:
                pproduct = request.env['product.product'].search([('default_code', '=', productcode)], limit=1)
                if pproduct:
                    tempdomain.append(('product_id', '=', pproduct.id))
            if workorder:
                tempdomain.append(('name', 'ilike', '%'+workorder+'%'))
            if workdate:
                tempdomain += [('plan_date', '=', workdate)]
            workorderlist = request.env['aas.mes.workorder'].search(tempdomain)
        workbook = xlwt.Workbook(style_compression=2)
        worksheet = workbook.add_sheet(u'良率报表')
        base_style = xlwt.easyxf('align: wrap yes')
        wkcolumnindex = 0
        worksheet.write(0, wkcolumnindex, u'日期', base_style)
        wkcolumnindex += 1
        worksheet.write(0, wkcolumnindex, u'班次', base_style)
        wkcolumnindex += 1
        if mesline.id == 5:
            worksheet.write(0, wkcolumnindex, u'员工', base_style)
            wkcolumnindex += 1
            worksheet.write(0, wkcolumnindex, u'设备', base_style)
            wkcolumnindex += 1
        worksheet.write(0, wkcolumnindex, u'主工单', base_style)
        wkcolumnindex += 1
        worksheet.write(0, wkcolumnindex, u'子工单', base_style)
        wkcolumnindex += 1
        worksheet.write(0, wkcolumnindex, u'生产品种', base_style)
        wkcolumnindex += 1
        worksheet.write(0, wkcolumnindex, u'开始时间', base_style)
        wkcolumnindex += 1
        worksheet.write(0, wkcolumnindex, u'结束时间', base_style)
        wkcolumnindex += 1
        worksheet.write(0, wkcolumnindex, u'计划产出', base_style)
        wkcolumnindex += 1
        worksheet.write(0, wkcolumnindex, u'实际产出', base_style)
        wkcolumnindex += 1
        worksheet.write(0, wkcolumnindex, u'达成率', base_style)
        wkcolumnindex += 1
        worksheet.write(0, wkcolumnindex, u'不良数量', base_style)
        wkcolumnindex += 1
        worksheet.write(0, wkcolumnindex, u'工单良率', base_style)
        wkcolumnindex += 1
        if mesline.line_type == 'flowing':
            worksheet.write(0, wkcolumnindex, u'一次不良', base_style)
            wkcolumnindex += 1
            worksheet.write(0, wkcolumnindex, u'二次不良', base_style)
            wkcolumnindex += 1
            worksheet.write(0, wkcolumnindex, u'三次不良', base_style)
        badcolumnindex = 1
        if badmodelist and len(badmodelist) > 0:
            for badmode in badmodelist:
                worksheet.write(0, wkcolumnindex+badcolumnindex, badmode['badmode_name'], base_style)
                badcolumnindex += 1
                badmodeids.append(badmode['badmode_id'])
        rowindex = 1
        if workorderlist and len(workorderlist) > 0:
            for workorder in workorderlist:
                mainorder_name = '' if not workorder.mainorder_id else workorder.mainorder_id.name,
                plan_date = '' if not workorder.plan_date else workorder.plan_date
                plan_schedule = '' if not workorder.plan_schedule else workorder.plan_schedule.name
                produce_start = '' if not workorder.produce_start else fields.Datetime.to_china_string(workorder.produce_start)
                produce_finish = '' if not workorder.produce_finish else fields.Datetime.to_china_string(workorder.produce_finish)
                reach_rate = workorder.output_qty / workorder.input_qty * 100.0
                employee_name, equipment_name, producer, equipment = '', '', workorder.producer_id, workorder.equipment_id
                if producer:
                    employee_name = producer.name + '[' + producer.code + ']'
                if equipment:
                    equipment_name = equipment.name + '[' + equipment.code + ']'
                wkcolumnindex = 0
                worksheet.write(rowindex, wkcolumnindex, plan_date, base_style)
                wkcolumnindex += 1
                worksheet.write(rowindex, wkcolumnindex, plan_schedule, base_style)
                wkcolumnindex += 1
                if mesline.id == 5:
                    worksheet.write(rowindex, wkcolumnindex, employee_name, base_style)
                    wkcolumnindex += 1
                    worksheet.write(rowindex, wkcolumnindex, equipment_name, base_style)
                    wkcolumnindex += 1
                worksheet.write(rowindex, wkcolumnindex, mainorder_name, base_style)
                wkcolumnindex += 1
                worksheet.write(rowindex, wkcolumnindex, workorder.name, base_style)
                wkcolumnindex += 1
                worksheet.write(rowindex, wkcolumnindex, workorder.product_code, base_style)
                wkcolumnindex += 1
                worksheet.write(rowindex, wkcolumnindex, produce_start, base_style)
                wkcolumnindex += 1
                worksheet.write(rowindex, wkcolumnindex, produce_finish, base_style)
                wkcolumnindex += 1
                worksheet.write(rowindex, wkcolumnindex, workorder.input_qty, base_style)
                wkcolumnindex += 1
                worksheet.write(rowindex, wkcolumnindex, workorder.output_qty, base_style)
                wkcolumnindex += 1
                worksheet.write(rowindex, wkcolumnindex, float_repr(reach_rate, 2), base_style)
                wkcolumnindex += 1
                tempbadmodevals = self.action_loading_workorder_badmodelist(workorder)
                badmode_qty = tempbadmodevals['total_qty']
                worksheet.write(rowindex, wkcolumnindex, badmode_qty, base_style)
                wkcolumnindex += 1
                if float_compare(workorder.output_qty, 0.0, precision_rounding=0.000001) <= 0.0:
                    yield_actual = 0.0
                else:
                    yield_actual = workorder.output_qty / (badmode_qty + workorder.output_qty) * 100.0
                worksheet.write(rowindex, wkcolumnindex, float_repr(yield_actual, 2), base_style)
                wkcolumnindex += 1
                if mesline.line_type == 'flowing':
                    worksheet.write(rowindex, wkcolumnindex, tempbadmodevals['once_qty'], base_style)
                    wkcolumnindex += 1
                    worksheet.write(rowindex, wkcolumnindex, tempbadmodevals['twice_qty'], base_style)
                    wkcolumnindex += 1
                    worksheet.write(rowindex, wkcolumnindex, tempbadmodevals['more_qty'], base_style)
                badcolumnindex = 1
                badmodes = tempbadmodevals['badmodes']
                if not badmodeids or len(badmodeids) <= 0:
                    rowindex += 1
                    continue
                for badmodeid in badmodeids:
                    temp_qty = 0.0
                    if badmodeid in badmodes:
                        temp_qty = badmodes[badmodeid]
                    worksheet.write(rowindex, wkcolumnindex+badcolumnindex, temp_qty, base_style)
                    badcolumnindex += 1
                rowindex += 1
        stream = StringIO()
        workbook.save(stream)
        outvalues = stream.getvalue()
        filename = mesline.name+fields.Datetime.to_china_today().replace('-', '')
        xlshttpheaders = [
            ('Content-Type', 'application/vnd.ms-excel'), ('Content-Length', len(outvalues)),
            (u'Content-Disposition', 'attachment; filename=%s.xls;'% filename)
        ]
        return request.make_response(outvalues, headers=xlshttpheaders)
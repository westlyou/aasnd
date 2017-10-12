# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging
import pytz
from datetime import datetime

_logger = logging.getLogger(__name__)


from odoo.addons.base.ir.ir_sequence import _alter_sequence

class IRSequence(models.Model):
    _inherit = "ir.sequence"

    loop_type = fields.Selection(selection=[('year', u'年'), ('month', u'月'), ('day', u'日')], string=u'循环类型')
    loop_time = fields.Datetime(string=u'循环日期', default=fields.Datetime.now)

    @api.one
    def alert_sequence(self, number_increment=None, number_next=None):
        numbervals = {}
        if not number_increment:
            number_increment = self.number_increment
        else:
            numbervals['number_increment'] = number_increment
        if not number_next:
            number_next = self.number_next
        else:
            numbervals['number_next'] = number_next
        if numbervals and len(numbervals) > 0:
            self.sudo().write(numbervals)
        _alter_sequence(self.env.cr, "ir_sequence_%03d" % self.id, number_increment=number_increment, number_next=number_next)


    def convert2timezonetime(self, origintime, tzname='Asia/Shanghai'):
        temptime = pytz.timezone('UTC').localize(origintime, is_dst=False)
        return temptime.astimezone(pytz.timezone(tzname))


    @api.model
    def next_by_code(self, sequence_code):
        temp_sequence = self.env['ir.sequence'].search([('code', '=', sequence_code)], limit=1)
        if not temp_sequence or not temp_sequence.loop_type:
            return super(IRSequence, self).next_by_code(sequence_code)
        tz_name = self.env.user.tz or self.env.context.get('tz') or 'Asia/Shanghai'
        temptime = fields.Datetime.from_string(temp_sequence.loop_time)
        loopdate = self.convert2timezonetime(temptime, tzname=tz_name).strftime('%Y-%m-%d')
        currenttime = fields.Datetime.from_string(fields.Datetime.now())
        currentdate = self.convert2timezonetime(currenttime, tzname=tz_name).strftime('%Y-%m-%d')
        temp_type, temp_flag = temp_sequence.loop_type, False
        if (temp_type == 'year') and (currentdate[0:4] != loopdate[0:4]):
            temp_flag = True
        elif (temp_type == 'month') and (currentdate[0:7] != loopdate[0:7]):
            temp_flag = True
        elif (temp_type == 'day') and (currentdate != loopdate):
            temp_flag = True
        if temp_flag:
            temp_sequence.sudo().alert_sequence(number_increment=1, number_next=1)
            temp_sequence.sudo().write({'loop_time': fields.Datetime.now()})
        return super(IRSequence, self).next_by_code(sequence_code)



class RESPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, vals):
        if ('tz' not in vals) or (not vals.get('tz')):
            vals['tz'] = 'Asia/Shanghai'
        return super(RESPartner, self).create(vals)


CONFIG_PARAM_WEB_WINDOW_TITLE = "web.base.title"

class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    web_window_title = fields.Char(u'页面标题')

    @api.model
    def get_default_web_window_title(self, fields):
        ir_config = self.env['ir.config_parameter']
        web_window_title = ir_config.get_param(CONFIG_PARAM_WEB_WINDOW_TITLE, "")
        return dict(web_window_title=web_window_title)

    @api.multi
    def set_default_web_window_title(self):
        self.ensure_one()
        ir_config = self.env['ir.config_parameter']
        web_window_title = self.web_window_title or ""
        ir_config.set_param(CONFIG_PARAM_WEB_WINDOW_TITLE, web_window_title)
        return True


class View(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def render_template(self, template, values=None, engine='ir.qweb'):
        if not values:
            values = {}
        if template in ['web.login', 'web.webclient_bootstrap']:
            values["title"] = self.env['ir.config_parameter'].get_param("web.base.title", "")
        return super(View, self).render_template(template, values=values, engine=engine)



class AASBaseCron(models.Model):
    _name = 'aas.base.cron'
    _description = u'安费诺自动化任务'
    _order = 'thend_time desc,start_time desc'

    name = fields.Char(string=u'名称')
    cron_method = fields.Char(string=u'方法')
    start_time = fields.Datetime(string=u'开始时间')
    thend_time = fields.Datetime(string=u'结束时间')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('aas.base.cron')
        vals['start_time'] = fields.Datetime.now()
        return super(AASBaseCron, self).create(vals)

    @api.model
    def excute_month_cron(self):
        """
        每月执行一次
        :return:
        """
        tempcron = self.env['aas.base.cron'].create({'cron_method': 'action_month_cron'})
        self.action_month_cron()
        tempcron.write({'thend_time': fields.Datetime.now()})

    @api.model
    def action_month_cron(self):
        pass

    @api.model
    def excute_day_cron(self):
        """
        每天执行一次
        :return:
        """
        tempcron = self.env['aas.base.cron'].create({'cron_method': 'action_day_cron'})
        self.action_day_cron()
        self.action_clear_cron_records()
        tempcron.write({'thend_time': fields.Datetime.now()})

    @api.model
    def action_day_cron(self):
        pass

    @api.model
    def excute_hour_cron(self):
        """
        每小时执行一次
        :return:
        """
        tempcron = self.env['aas.base.cron'].create({'cron_method': 'action_hour_cron'})
        self.action_hour_cron()
        tempcron.write({'thend_time': fields.Datetime.now()})

    @api.model
    def action_hour_cron(self):
        pass

    @api.model
    def action_clear_cron_records(self, days=180):
        # 清理days天之前的记录,默认半年
        pass

    @api.model
    def excute_minute_cron(self):
        """
        每分钟执行一次
        :return:
        """
        self.action_minute_cron()


    @api.model
    def action_minute_cron(self):
        pass


    @api.model
    def excute_thirty_minutes_cron(self):
        """
        每30分钟执行一次
        :return:
        """
        tempcron = self.env['aas.base.cron'].create({'cron_method': 'action_thirty_minutes_cron'})
        self.action_thirty_minutes_cron()
        tempcron.write({'thend_time': fields.Datetime.now()})

    @api.model
    def action_thirty_minutes_cron(self):
        pass

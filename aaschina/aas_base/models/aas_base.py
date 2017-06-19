# -*- coding: utf-8 -*-


import odoo
from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)

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
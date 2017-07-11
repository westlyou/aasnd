# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-8 23:03
"""


import logging
import werkzeug

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied
from odoo.addons.web.controllers.main import Home

logger = logging.getLogger(__name__)

def abort_and_redirect(url):
    r = request.httprequest
    response = werkzeug.utils.redirect(url, 302)
    response = r.app.get_response(r, response, explicit_session=False)
    werkzeug.exceptions.abort(response)


def ensure_db(redirect='/web/database/selector'):
    db = request.params.get('db')
    if db and db not in http.db_filter([db]):
        db = None
    if db and not request.session.db:
        r = request.httprequest
        url_redirect = r.base_url
        if r.query_string:
            url_redirect += '?' + r.query_string
        response = werkzeug.utils.redirect(url_redirect, 302)
        request.session.db = db
        abort_and_redirect(url_redirect)
    if not db and request.session.db and http.db_filter([request.session.db]):
        db = request.session.db
    if not db:
        db = http.db_monodb(request.httprequest)
    if not db:
        werkzeug.exceptions.abort(werkzeug.utils.redirect(redirect, 303))
    if db != request.session.db:
        request.session.logout()
        abort_and_redirect(request.httprequest.url)
    request.session.db = db


class AASBaseWechatController(Home):


    @http.route('/web/login', type='http', auth="public", methods=['GET', 'POST'])
    def web_login(self, redirect=None, *args, **kw):
        if redirect and (redirect.find('aaswechat')>-1):
            redirect = '/aaswechat/login?' + request.httprequest.query_string
            return http.redirect_with_hash(redirect)
        return super(AASBaseWechatController, self).web_login(redirect=redirect, *args, **kw)

    @http.route('/aaswechat/login', type='http', auth="public", methods=['GET', 'POST'])
    def aaswechat_login(self, redirect=None, *args, **kw):
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)
        if not request.uid:
            request.uid = self.sudo().env.user.id
        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except AccessDenied:
            values['databases'] = None
        logger.info('databases is ok')
        if request.httprequest.method == 'POST':
            old_uid = request.uid
            uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
            if uid is not False:
                request.params['login_success'] = True
                if not redirect:
                    redirect = '/web'
                return http.redirect_with_hash(redirect)
            request.uid = old_uid
            values['error'] = u"账号或密码错误！"
        return request.render('aas_base.aas_wechat_login', values)


    @http.route('/aaswechat/labelprinters', type='json', auth="user")
    def aas_wechat_labelprinters(self):
        values = {'success': True, 'message': '', 'printers': []}
        printers = request.env['aas.label.printer'].search([])
        if printers and len(printers) > 0:
            values['printers'] = [{'value': str(printer.id), 'text': printer.name} for printer in printers]
        return values

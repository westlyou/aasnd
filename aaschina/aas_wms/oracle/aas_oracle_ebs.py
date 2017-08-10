# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-5 11:25
"""

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class AASBaseCron(models.Model):
    _inherit = 'aas.base.cron'


    @api.model
    def action_day_cron(self):
        super(AASBaseCron, self).action_day_cron()
        self.action_synchronize_baseinformation()

    @api.model
    def action_synchronize_baseinformation(self):
        _logger.info(u'synchronize base information start: '+fields.Datetime.now())
        self.action_insert_uomcategory()
        self.action_update_uomcategory()
        self.action_insert_product_uom()
        self.action_update_product_uom()
        self.action_insert_vendors()
        self.action_update_vendors()
        self.action_insert_customer()
        self.action_update_customer()
        self.action_insert_product_template()
        self.action_update_product_template()
        self.action_insert_product_product()
        self.action_update_product_product()
        _logger.info(u'synchronize base information done: '+fields.Datetime.now())

    @api.model
    def action_insert_uomcategory(self):
        sql_query = """
        INSERT INTO product_uom_categ (name, create_date, write_date)
        SELECT t2.description, t2.creation_date, t2.last_update_date
        FROM product_uom_categ t1 RIGHT JOIN aas_ebs_uom_categ t2 ON t1.name = t2.description and t1.create_date = t2.creation_date
        WHERE t1.name IS NULL
        """
        self.env.cr.execute(sql_query)

    @api.model
    def action_update_uomcategory(self):
        sql_query = """
        UPDATE product_uom_categ t1 SET name = t2.description, write_date = t2.last_update_date
        FROM aas_ebs_uom_categ t2
        WHERE t1.name = t2.description AND t1.create_date = t2.creation_date AND t1.write_date <> t2.last_update_date
        """
        self.env.cr.execute(sql_query)


    @api.model
    def action_insert_product_uom(self):
        sql_query = """
        INSERT INTO product_uom (name, rounding, active, uom_type, factor, category_id, create_date, write_date)
        SELECT t2.uom_code, 0.01, TRUE, 'reference', 1, t3.id, t2.creation_date, t2.last_update_date
        FROM product_uom t1 RIGHT JOIN aas_ebs_uom t2 ON t1.name = t2.uom_code and t1.create_date = t2.creation_date
             INNER JOIN product_uom_categ t3 ON t2.uom_class = t3.name
        WHERE t1.name IS NULL
        """
        self.env.cr.execute(sql_query)

    @api.model
    def action_update_product_uom(self):
        sql_query = """
        UPDATE product_uom t1 SET name = t2.description, category_id = t3.id, write_date = t2.last_update_date
        FROM aas_ebs_uom t2 INNER JOIN product_uom_categ t3 ON t2.uom_class = t3.name
        WHERE t1.name = t2.uom_code AND t1.create_date = t2.creation_date AND t1.write_date <> t2.last_update_date
        """
        self.env.cr.execute(sql_query)


    @api.model
    def action_insert_vendors(self):
        sql_query = """
        INSERT INTO res_partner (id, ref, name, display_name, company_id, is_company, supplier, customer, employee, active, tz, lang, type, commercial_partner_id, notify_email, picking_warn, create_date, write_date)
        SELECT t2.id, t2.ref, t2.name, t2.name, 1, TRUE, TRUE, FALSE, FALSE, TRUE, 'Asia/Shanghai', 'zh_CN', 'contact', t2.id, 'none', 'no-message', t2.creation_date, t2.last_update_date
        FROM res_partner t1 RIGHT JOIN aas_ebs_vendors t2 ON t1.id = t2.id and t1.create_date = t2.creation_date
        WHERE t1.name IS NULL
        """
        self.env.cr.execute(sql_query)

    @api.model
    def action_update_vendors(self):
        sql_query = """
        UPDATE res_partner t1 SET ref = t2.ref, name = t2.name, display_name = t2.name, write_date = t2.last_update_date
        FROM aas_ebs_vendors t2
        WHERE t1.id = t2.id AND t1.create_date = t2.creation_date AND t1.write_date <> t2.last_update_date
        """
        self.env.cr.execute(sql_query)


    @api.model
    def action_insert_customer(self):
        sql_query = """
        INSERT INTO res_partner (id, ref, name, display_name, company_id, is_company, supplier, customer, employee, active, tz, lang, type, commercial_partner_id, notify_email, picking_warn, create_date, write_date)
        SELECT t2.id, t2.ref, t2.name, t2.cname, 1, TRUE, FALSE, TRUE, FALSE, TRUE, 'Asia/Shanghai', 'zh_CN', 'contact', t2.id, 'none', 'no-message', t2.creation_date, t2.last_update_date
        FROM res_partner t1 RIGHT JOIN aas_ebs_customers t2 ON t1.id = t2.id and t1.create_date = t2.creation_date
        WHERE t1.name IS NULL
        """
        self.env.cr.execute(sql_query)


    @api.model
    def action_update_customer(self):
        sql_query = """
        UPDATE res_partner t1 SET ref = t2.ref, name = t2.name, display_name = t2.name, write_date = t2.last_update_date
        FROM aas_ebs_customers t2
        WHERE t1.id = t2.id AND t1.create_date = t2.creation_date AND t1.write_date <> t2.last_update_date
        """
        self.env.cr.execute(sql_query)


    @api.model
    def action_insert_product_template(self):
        sql_query = """
        INSERT INTO product_template (id, default_code, name, company_id, categ_id, type, uom_id, uom_po_id, active, tracking, create_date, write_date)
        SELECT t2.id, t2.default_code, t2.name, 1, 1, 'product', t3.id, t3.id, TRUE, 'lot', t2.creation_date, t2.last_update_date
        FROM product_template t1 RIGHT JOIN aas_ebs_product t2 ON t1.id = t2.id and t1.create_date = t2.creation_date
             INNER JOIN product_uom t3 ON t2.product_uom = t3.name
        WHERE t1.name IS NULL
        """
        self.env.cr.execute(sql_query)


    @api.model
    def action_update_product_template(self):
        sql_query = """
        UPDATE product_template t1 SET default_code=t2.default_code, name = t2.name, uom_id = t3.id, uom_po_id = t3.id, write_date = t2.last_update_date
        FROM aas_ebs_product t2 INNER JOIN product_uom t3 ON t2.product_uom = t3.name
        WHERE t1.id = t2.id AND t1.create_date = t2.creation_date AND t1.write_date <> t2.last_update_date
        """
        self.env.cr.execute(sql_query)


    @api.model
    def action_insert_product_product(self):
        sql_query = """
        INSERT INTO product_product (id, default_code, product_tmpl_id, active, create_date, write_date)
        SELECT t2.id, t2.default_code, t2.id, TRUE, t2.creation_date, t2.last_update_date
        FROM product_product t1 RIGHT JOIN aas_ebs_product t2 ON t1.id = t2.id and t1.create_date = t2.creation_date
        WHERE t1.id IS NULL
        """
        self.env.cr.execute(sql_query)


    @api.model
    def action_update_product_product(self):
        sql_query = """
        UPDATE product_product t1 SET default_code = t2.default_code, write_date = t2.last_update_date
        FROM aas_ebs_product t2
        WHERE t1.id = t2.id AND t1.create_date = t2.creation_date AND t1.write_date <> t2.last_update_date
        """
        self.env.cr.execute(sql_query)

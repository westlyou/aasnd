# -*- coding: utf-8 -*-

{
    'name': u'安费诺基础信息',
    'version': '1.0',
    'category': 'Zhiq Amphenol',
    'sequence': 1,
    'summary': u'安费诺基础信息',
    'description': """
        安费诺基础信息
    """,
    'author': 'Luforn',
    'website': 'http://www.zhiq.info',
    'depends': ['web', 'base_setup'],
    'data': [
        'data/aas_base_schedule.xml',
        'data/aas_base_sequence.xml',
        'security/aas_base_security.xml',
        'security/ir.model.access.csv',
        'views/aas_base_templates.xml',
        'views/aas_base_view.xml',
        'views/aas_label_view.xml',
        'views/aas_wechat_templates.xml'
    ],
    'qweb':[
        'static/src/xml/aas_base.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}

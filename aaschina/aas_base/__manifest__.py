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
        'views/aas_base_templates.xml',
        'views/aas_base_view.xml'
    ],
    'qweb':[
        'static/src/xml/aas_base.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}

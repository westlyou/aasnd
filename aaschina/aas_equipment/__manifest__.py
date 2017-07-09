# -*- coding: utf-8 -*-

{
    'name': u'安费诺设备',
    'version': '1.0',
    'category': 'Zhiq Amphenol',
    'sequence': 4,
    'summary': u'安费诺设备',
    'description': """
        安费诺设备管理
    """,
    'author': 'Luforn',
    'website': 'http://www.zhiq.info',
    'depends': ['aas_redis'],
    'data': [
        'data/aas_equipment_data.xml',
        'views/aas_equipment_view.xml',
        'views/aas_equipment_data_view.xml'
    ],
    'qweb':[],
    'installable': True,
    'application': True,
    'auto_install': False
}

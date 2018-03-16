# -*- coding: utf-8 -*-

{
    'name': u'宁德安费诺设备数据',
    'version': '1.0',
    'category': 'Zhiq Amphenol',
    'sequence': 4,
    'summary': u'宁德安费诺设备数据',
    'description': """
        宁德安费诺设备管理
    """,
    'author': 'Luforn',
    'website': 'http://www.zhiq.info',
    'depends': ['aas_equipment'],
    'data': [
        'security/ir.model.access.csv',
        'views/aas_equipment_equipment_view.xml'
    ],
    'qweb':[],
    'installable': True,
    'application': True,
    'auto_install': False
}

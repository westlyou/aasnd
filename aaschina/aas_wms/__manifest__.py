# -*- coding: utf-8 -*-

{
    'name': u'安费诺仓库管理',
    'version': '1.0',
    'category': 'Zhiq Amphenol',
    'sequence': 2,
    'summary': u'安费诺仓库管理',
    'description': """
        安费诺仓库管理
    """,
    'author': 'Luforn',
    'website': 'http://www.zhiq.info',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/aas_product_label_view.xml',
        'views/aas_receive_deliver_view.xml'
    ],
    'qweb':[],
    'installable': True,
    'application': True,
    'auto_install': False
}

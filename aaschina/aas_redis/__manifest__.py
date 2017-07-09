# -*- coding: utf-8 -*-

{
    'name': u'安费诺Redis',
    'version': '1.0',
    'category': 'Zhiq Amphenol',
    'sequence': 1,
    'summary': u'安费诺Redis',
    'description': """
        安费诺Redis管理，缓存、消息队列
    """,
    'author': 'Luforn',
    'website': 'http://www.zhiq.info',
    'depends': ['aas_base'],
    'data': [
        'views/aas_redis_view.xml'
    ],
    'qweb':[],
    'installable': True,
    'application': True,
    'auto_install': False
}

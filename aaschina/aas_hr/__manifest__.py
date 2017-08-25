# -*- coding: utf-8 -*-

{
    'name': u'安费诺人事',
    'version': '1.0',
    'category': 'Zhiq Amphenol',
    'sequence': 6,
    'summary': u'安费诺人事',
    'description': """
        安费诺人力资源
    """,
    'author': 'Luforn',
    'website': 'http://www.zhiq.info',
    'depends': ['aas_base'],
    'data': [
        'security/aas_hr_security.xml',
        'security/ir.model.access.csv',
        'views/aas_hr_view.xml',
        'views/aas_hr_employee_view.xml'
    ],
    'qweb':[],
    'installable': True,
    'application': True,
    'auto_install': False
}

# -*- coding: utf-8 -*-

{
    'name': u'安费诺生产',
    'version': '1.0',
    'category': 'Zhiq Amphenol',
    'sequence': 5,
    'summary': u'安费诺生产',
    'description': """
        安费诺生产管理
    """,
    'author': 'Luforn',
    'website': 'http://www.zhiq.info',
    'depends': ['aas_wms', 'aas_equipment'],
    'data': [
        'security/aas_mes_security.xml',
        'security/ir.model.access.csv',
        'views/aas_mes_view.xml',
        'views/aas_stock_delivery_view.xml',
        'views/aas_stock_receipt_view.xml',
        'views/aas_stock_report_view.xml',
        'views/aas_mes_manufacture_view.xml',
        'wizard/aas_mes_manufacture_wizard_view.xml'
    ],
    'qweb':[],
    'installable': True,
    'application': True,
    'auto_install': False,
    'external_dependencies': {'python': ['wechatpy']}
}

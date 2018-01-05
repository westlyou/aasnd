# -*-  coding: utf-8 -*-

{
    'name': u'安费诺质量',
    'version': '1.0',
    'category': 'Zhiq Amphenol',
    'sequence': 3,
    'summary': u'安费诺质量',
    'description': """
        安费诺质量管理
     """,
    'author': 'Luforn',
    'website': 'http://www.zhiq.info',
    'depends': ['aas_wms'],
    'data': [
        'security/aas_quality_security.xml',
        'security/ir.model.access.csv',
        'data/aas_quality_sequence.xml',
        'views/aas_quality_view.xml',
        'views/aas_quality_order_view.xml',
        'wizard/aas_quality_order_wizard_view.xml',
        'views/aas_wms_models_view.xml',
        'wizard/aas_wms_models_wizard_view.xml',
        'views/aas_product_label_view.xml',
        'views/aas_quality_frozen_view.xml',

        'wechat/views/aas_wechat_quality_template.xml',
        'wechat/views/aas_wechat_quality_order_template.xml'
    ],
    'qweb':[],
    'installable': True,
    'application': True,
    'auto_install': False
}

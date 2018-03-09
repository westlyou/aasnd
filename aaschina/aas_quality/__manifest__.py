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
    'depends': ['aas_wms', 'aas_mes'],
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
        'views/aas_quality_concession_view.xml',
        'views/aas_quality_oqcorder_view.xml',
        'views/aas_quality_oqcorder_templates.xml',
        'views/aas_quality_workdata_view.xml',
        'views/aas_quality_serialnumber_view.xml',

        'wechat/views/aas_wechat_quality_template.xml',
        'wechat/views/aas_wechat_quality_order_template.xml',
        'wechat/views/aas_wechat_quality_oqcchecking_template.xml',

        'views/aas_mes_producttest_view.xml',
        'views/aas_mes_rework_view.xml',
        'views/aas_mes_tracing_view.xml'
    ],
    'qweb':[],
    'installable': True,
    'application': True,
    'auto_install': False
}

# -*- coding: utf-8 -*-

{
    'name': u'安费诺库存',
    'version': '1.0',
    'category': 'Zhiq Amphenol',
    'sequence': 2,
    'summary': u'安费诺库存',
    'description': """
        安费诺库存管理
    """,
    'author': 'Luforn',
    'website': 'http://www.zhiq.info',
    'depends': ['stock', 'aas_base'],
    'data': [
        'data/aas_wms_data.xml',
        'data/aas_wms_sequence.xml',
        'security/aas_wms_security.xml',
        'security/ir.model.access.csv',
        'views/aas_stock_models_view.xml',
        'views/aas_product_label_view.xml',
        'wizard/aas_product_label_wizard_view.xml',
        'views/aas_receive_deliver_view.xml',
        'views/aas_stock_receipt_view.xml',
        'views/aas_stock_receipt_inside_view.xml',
        'views/aas_stock_receipt_outside_view.xml',
        'wizard/aas_stock_receipt_wizard_view.xml',
        'views/aas_stock_delivery_view.xml',
        'views/aas_stock_delivery_outside_view.xml',
        'views/aas_stock_delivery_inside_view.xml',
        'wizard/aas_stock_delivery_wizard_view.xml',
        'views/aas_stock_inventory_view.xml',
        'wizard/aas_stock_inventory_wizard_view.xml',
        'views/aas_stock_move_view.xml',
        'views/aas_container_view.xml',
        'views/aas_wms_delivery_templates.xml',
        'views/aas_stock_adjust_view.xml',
        'views/aas_stock_material_view.xml',
        'views/aas_wms_inventory_templates.xml',

        'oracle/aas_stock_purchase_view.xml',
        'oracle/aas_stock_sales_view.xml',

        'wechat/views/aas_wechat_wms_template.xml',
        'wechat/views/aas_wechat_wms_receipt_template.xml',
        'wechat/views/aas_wechat_wms_purchase_template.xml',
        'wechat/views/aas_wechat_wms_label_template.xml',
        'wechat/views/aas_wechat_wms_delivery_template.xml',
        'wechat/views/aas_wechat_wms_quant_template.xml',
        'wechat/views/aas_wechat_wms_inventory_template.xml'
    ],
    'qweb':[],
    'installable': True,
    'application': True,
    'auto_install': False,
    'external_dependencies': {'python': ['wechatpy']}
}

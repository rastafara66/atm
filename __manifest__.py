# -*- coding: utf-8 -*-
{
    'name': "ATM - auto export orders",
    'summary': """
        Automatically creates a scheduled task to export orders to a json file
	""",
    'description': """
        Automatically creates a scheduled task to export orders to a json file
    """,

    'author': "chukhin",
    # 'website': "https://github.com/rastafara66",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Specific Industry Applications',
    'version': '16.0.0.38',
	'license': 'LGPL-3',
	'images': ['images/thumb.png'],
	'price': 00.00,
	'currency': 'EUR',
    # any module necessary for this one to work correctly
    'depends': ['base',
                'account',
                'sale',
	],

    # always loaded
    'data': [
        'views/views.xml',
        'views/templates.xml',
		'views/res_config_settings_views.xml',
        'data/cron.xml',
        #'data/sale_demo.xml',
        'security/ir.model.access.csv',		
    ],
    # only loaded in demonstration mode
    'demo': [
        'data/product_demo.xml',
        # 'data/account.xml',
        # 'data/sale_demo.xml',
    ],
    #     'odoo.cron': [
    #     '1 1 * * * atm.OrderList.export_order_list_to_json()',
    # ],
}

# -*- coding: utf-8 -*-
{
    'name': "ATM - auto exim orders",
    'summary': """Automatically creates a scheduled task to export/import orders to a json file""",
    'description': """Automatically creates a scheduled task to export/import orders to a json file""",
    'author': "chukhin",
    'website': "https://github.com/rastafara66",
    'category': 'Tools',
    'version': '17.0.1.23',
	'license': 'LGPL-3',
	'images': [
		'images/thumb.png',
		'images/atm_settings.png',
		'images/exp_sheduler.png',
		'images/imp_sheduler.png',
	],
	'price': 00.00,
	'currency': 'EUR',
    'depends': ['base',
                'account',
                'sale',
	],
    'data': [
		'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
		'views/res_config_settings_views.xml',
        'data/cron.xml',	
    ],
    'demo': [
        'data/product_demo.xml',
    ],
    #     'odoo.cron': [
    #     '1 1 * * * atm.OrderList.export_order_list_to_json()',
    # ],
}

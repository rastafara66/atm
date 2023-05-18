# -*- coding: utf-8 -*-
{
    'name': "Automated Transaction Mechanics",

    'summary': """
        ATM odoo module""",

    'description': """
        ATM - Automated Transaction Mechanics
    """,

    'author': "chukhin",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Specific Industry Applications',
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['base',
                'sale',],

    # always loaded
    'data': [
        'views/views.xml',
        'views/templates.xml',
        'data/cron.xml',
        #'data/sale_demo.xml',
        'security/ir.model.access.csv',
    ],
    # only loaded in demonstration mode
    'demo': [
        'data/product_demo.xml',
        'data/sale_demo.xml',
    ],
    #     'odoo.cron': [
    #     '1 1 * * * atm.OrderList.export_order_list_to_json()',
    # ],
}

# -*- coding: utf-8 -*-
{
    'name': "atm",

    'summary': """
        odoo module""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
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
        #'data/cron.xml',
        #'security/ir.model.access.csv',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    #     'odoo.cron': [
    #     '1 1 * * * atm.OrderList.export_order_list_to_json()',
    # ],
}

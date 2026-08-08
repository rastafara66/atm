# -*- coding: utf-8 -*-
{
    'name': 'Data Exchange - JSON sync for orders, invoices and payments',
    'summary': 'Scheduled JSON exchange of contacts, products, orders, '
               'invoices and payments with an external accounting system',
    'description': """
Data Exchange - JSON sync with an external accounting system
============================================================

Keeps Odoo and an external accounting or ERP system in step through plain JSON
files in a shared directory - no open port, no middleware.

Exchanged entities
------------------

* Contacts and products (master data)
* Sales orders and purchase orders
* Customer invoices and vendor bills
* Customer and vendor credit notes
* Customer and vendor payments

How it works
------------

* Two scheduled actions, one per direction, both disabled by default.
* Each entity lands in its own file, so the external side reads only what it needs.
* Records are matched by an external reference, never by database id, which makes repeated imports idempotent.
* Imported documents are created as drafts; confirming them is an explicit setting.
* Posted documents are never rewritten by a later import.
* Every run is written to an exchange log with created, updated, skipped and failed counters.
""",
    'author': 'chukhin',
    'website': 'https://github.com/rastafara66/atm',
    'category': 'Productivity',
    'version': '17.0.2.0.0',
    'license': 'LGPL-3',
    # The first image is the card picture in the App Store listing.
    'images': [
        'static/description/banner.png',
        'static/description/screenshot_settings.png',
        'static/description/screenshot_log.png',
        'static/description/screenshot_json.png',
    ],
    'price': 0.00,
    'currency': 'EUR',
    'depends': [
        'base',
        'sale_management',
        'purchase',
        'account',
    ],
    'data': [
        'security/atm_security.xml',
        'security/ir.model.access.csv',
        'views/atm_exchange_log_views.xml',
        'views/res_config_settings_views.xml',
        'views/atm_menus.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': False,
}

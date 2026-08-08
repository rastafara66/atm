# -*- coding: utf-8 -*-
"""Registry of business entities ATM can exchange with an external system.

Every entity is described declaratively so that the exchange engine stays
generic: adding a document type means adding one :class:`EntitySpec`, not a new
export/import routine.

Records are matched between systems by ``external_ref`` -- a stable string key
issued by the external system -- never by database id. Ids are local to a
database and would silently point at unrelated records on the other side.
"""


class EntitySpec:
    """Declarative description of one exchangeable entity.

    :param code: technical key used in settings, file names and logs.
    :param model: Odoo model to read from / write to.
    :param label: human readable name (English, shown in the UI).
    :param filename: JSON file this entity is stored in.
    :param domain: extra domain applied on export, on top of the date filter.
    :param date_field: field used by the "export documents since" filter.
        ``None`` means the entity is not time-filtered (master data).
    :param fields: mapping ``json key -> Odoo field name`` for scalar values.
    :param m2o_fields: mapping ``json key -> (Odoo field, related entity code)``.
        Exported as the target's ``external_ref``, resolved back on import.
    :param line_field: one2many field holding document lines, if any.
    :param line_fields: scalar line fields, same shape as ``fields``.
    :param line_m2o_fields: relational line fields, same shape as ``m2o_fields``.
    :param defaults: values forced on every record created by the import.
    :param group: UI grouping used on the settings screen.
    """

    def __init__(self, code, model, label, filename, domain=None,
                 date_field=None, fields=None, m2o_fields=None,
                 line_field=None, line_fields=None, line_m2o_fields=None,
                 defaults=None, group='documents'):
        self.code = code
        self.model = model
        self.label = label
        self.filename = filename
        self.domain = domain or []
        self.date_field = date_field
        self.fields = fields or {}
        self.m2o_fields = m2o_fields or {}
        self.line_field = line_field
        self.line_fields = line_fields or {}
        self.line_m2o_fields = line_m2o_fields or {}
        self.defaults = defaults or {}
        self.group = group

    @property
    def setting_param(self):
        """Config parameter that enables/disables this entity."""
        return 'atm.entity_%s' % self.code

    def __repr__(self):
        return '<EntitySpec %s -> %s>' % (self.code, self.model)


#: Master data. Exported first and imported first: documents refer to it.
MASTER_DATA = [
    EntitySpec(
        code='partner',
        model='res.partner',
        label='Contacts',
        filename='partners.json',
        group='master',
        fields={
            'name': 'name',
            'is_company': 'is_company',
            'vat': 'vat',
            'street': 'street',
            'city': 'city',
            'zip': 'zip',
            'phone': 'phone',
            'email': 'email',
            'customer_code': 'ref',
        },
        m2o_fields={
            'country': ('country_id', None),
        },
    ),
    EntitySpec(
        code='product',
        model='product.product',
        label='Products',
        filename='products.json',
        group='master',
        fields={
            'name': 'name',
            'default_code': 'default_code',
            'barcode': 'barcode',
            'type': 'type',
            'list_price': 'list_price',
            'standard_price': 'standard_price',
        },
        m2o_fields={
            'uom': ('uom_id', None),
            # Odoo requires the default and the purchase unit to belong to the
            # same category, so the purchase one has to travel along.
            'uom_po': ('uom_po_id', None),
            'category': ('categ_id', None),
        },
    ),
]

#: Sales and purchase documents, in dependency order.
DOCUMENTS = [
    EntitySpec(
        code='sale_order',
        model='sale.order',
        label='Sales Orders',
        filename='sale_orders.json',
        date_field='date_order',
        domain=[('state', 'in', ['sale', 'done'])],
        fields={
            'name': 'name',
            'date_order': 'date_order',
            'state': 'state',
            'amount_untaxed': 'amount_untaxed',
            'amount_tax': 'amount_tax',
            'amount_total': 'amount_total',
            'client_order_ref': 'client_order_ref',
        },
        m2o_fields={
            'partner': ('partner_id', 'partner'),
            'currency': ('currency_id', None),
        },
        line_field='order_line',
        line_fields={
            'name': 'name',
            'quantity': 'product_uom_qty',
            'price_unit': 'price_unit',
            'discount': 'discount',
            'price_subtotal': 'price_subtotal',
        },
        line_m2o_fields={
            'product': ('product_id', 'product'),
            'uom': ('product_uom_id', None),
        },
    ),
    EntitySpec(
        code='purchase_order',
        model='purchase.order',
        label='Purchase Orders',
        filename='purchase_orders.json',
        date_field='date_order',
        domain=[('state', 'in', ['purchase', 'done'])],
        fields={
            'name': 'name',
            'date_order': 'date_order',
            'state': 'state',
            'amount_untaxed': 'amount_untaxed',
            'amount_tax': 'amount_tax',
            'amount_total': 'amount_total',
            'partner_ref': 'partner_ref',
        },
        m2o_fields={
            'partner': ('partner_id', 'partner'),
            'currency': ('currency_id', None),
        },
        line_field='order_line',
        line_fields={
            'name': 'name',
            'quantity': 'product_qty',
            'price_unit': 'price_unit',
            'price_subtotal': 'price_subtotal',
        },
        line_m2o_fields={
            'product': ('product_id', 'product'),
            'uom': ('product_uom_id', None),
        },
    ),
]


def _move_spec(code, label, filename, move_type):
    """Build the spec of one journal entry flavour (invoice/bill/refund)."""
    return EntitySpec(
        code=code,
        model='account.move',
        label=label,
        filename=filename,
        date_field='invoice_date',
        domain=[('move_type', '=', move_type), ('state', '=', 'posted')],
        defaults={'move_type': move_type},
        fields={
            'name': 'name',
            'invoice_date': 'invoice_date',
            'invoice_date_due': 'invoice_date_due',
            'ref': 'ref',
            'state': 'state',
            'amount_untaxed': 'amount_untaxed',
            'amount_tax': 'amount_tax',
            'amount_total': 'amount_total',
        },
        m2o_fields={
            'partner': ('partner_id', 'partner'),
            'currency': ('currency_id', None),
        },
        line_field='invoice_line_ids',
        line_fields={
            'name': 'name',
            'quantity': 'quantity',
            'price_unit': 'price_unit',
            'discount': 'discount',
            'price_subtotal': 'price_subtotal',
        },
        line_m2o_fields={
            'product': ('product_id', 'product'),
            'uom': ('product_uom_id', None),
            'account': ('account_id', None),
        },
    )


DOCUMENTS += [
    _move_spec('customer_invoice', 'Customer Invoices',
               'customer_invoices.json', 'out_invoice'),
    _move_spec('vendor_bill', 'Vendor Bills', 'vendor_bills.json',
               'in_invoice'),
    _move_spec('customer_refund', 'Customer Credit Notes',
               'customer_refunds.json', 'out_refund'),
    _move_spec('vendor_refund', 'Vendor Credit Notes', 'vendor_refunds.json',
               'in_refund'),
]


def _payment_spec(code, label, filename, payment_type, partner_type):
    """Build the spec of one payment direction."""
    return EntitySpec(
        code=code,
        model='account.payment',
        label=label,
        filename=filename,
        date_field='date',
        domain=[('payment_type', '=', payment_type), ('state', '!=', 'draft')],
        defaults={'payment_type': payment_type, 'partner_type': partner_type},
        fields={
            'name': 'name',
            'date': 'date',
            'amount': 'amount',
            'memo': 'memo',
            'state': 'state',
        },
        m2o_fields={
            'partner': ('partner_id', 'partner'),
            'currency': ('currency_id', None),
            'journal': ('journal_id', None),
        },
    )


DOCUMENTS += [
    _payment_spec('customer_payment', 'Customer Payments',
                  'customer_payments.json', 'inbound', 'customer'),
    _payment_spec('vendor_payment', 'Vendor Payments', 'vendor_payments.json',
                  'outbound', 'supplier'),
]

#: Full ordered registry. Order matters: master data must come first so that
#: documents imported afterwards can resolve their references.
ENTITIES = MASTER_DATA + DOCUMENTS

ENTITIES_BY_CODE = {spec.code: spec for spec in ENTITIES}

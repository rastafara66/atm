# Data Exchange — JSON sync for orders, invoices and payments

Scheduled JSON exchange between Odoo and an external accounting or ERP system.
Odoo writes the documents into a shared directory and reads back whatever the
other side puts there. No open port, no middleware, no API keys.

## Exchanged entities

| Entity             | Odoo model                       | File                     |
| ------------------ | -------------------------------- | ------------------------ |
| Contacts           | `res.partner`                    | `partners.json`          |
| Products           | `product.product`                | `products.json`          |
| Sales Orders       | `sale.order`                     | `sale_orders.json`       |
| Purchase Orders    | `purchase.order`                 | `purchase_orders.json`   |
| Customer Invoices  | `account.move` / `out_invoice`   | `customer_invoices.json` |
| Vendor Bills       | `account.move` / `in_invoice`    | `vendor_bills.json`      |
| Customer Credit Notes | `account.move` / `out_refund` | `customer_refunds.json`  |
| Vendor Credit Notes   | `account.move` / `in_refund`  | `vendor_refunds.json`    |
| Customer Payments  | `account.payment` / inbound      | `customer_payments.json` |
| Vendor Payments    | `account.payment` / outbound     | `vendor_payments.json`   |

Each entity can be switched on or off separately in the settings.

## File format

```json
{
  "atm_format": "1.0",
  "entity": "customer_invoice",
  "model": "account.move",
  "generated_at": "2026-08-08 09:00:00",
  "source": { "system": "odoo", "database": "mycompany", "company": "My Company" },
  "records": [
    {
      "external_ref": "odoo/account.move/38",
      "name": "INV/2026/00008",
      "invoice_date": "2026-08-08",
      "partner": { "external_ref": "odoo/res.partner/13", "name": "LightsUp" },
      "currency": { "name": "USD", "xmlid": "base.USD" },
      "amount_untaxed": 750.0,
      "amount_tax": 150.0,
      "amount_total": 900.0,
      "tax_summary": [
        {
          "name": "20%",
          "rate": 20.0,
          "base": 750.0,
          "amount": 150.0,
          "total": 900.0,
          "taxes": [
            { "name": "20%", "rate": 20.0, "amount_type": "percent",
              "type_tax_use": "sale", "xmlid": "l10n_ua.tax_20" }
          ]
        }
      ],
      "lines": [
        {
          "name": "Office Lamp",
          "quantity": 15.0,
          "price_unit": 50.0,
          "price_subtotal": 750.0,
          "price_total": 900.0,
          "product": { "external_ref": "odoo/product.product/6", "name": "Office Lamp" },
          "taxes": [
            { "name": "20%", "rate": 20.0, "amount_type": "percent",
              "type_tax_use": "sale", "xmlid": "l10n_ua.tax_20" }
          ]
        }
      ]
    }
  ]
}
```

References between records are never database ids. Business records carry an
`external_ref`; reference data (currencies, units of measure, accounts, taxes)
is described by name, code and XML id, and resolved against the local database
on import. That is what allows the same file to be loaded into a different
database.

## Taxes

`amount_tax` is a single figure, which is enough to reconcile a total but not to
raise a tax invoice. Orders, invoices, bills and credit notes therefore also
carry `tax_summary`: one entry per rate, with the taxable base (`base`), the tax
(`amount`) and the gross (`total`).

* Lines are grouped by their **whole set of taxes**. A line carrying two taxes
  forms its own entry rather than being split between them; that entry lists
  both in `taxes` and has no `rate`.
* Lines with no tax at all form an entry with an empty `name` and an empty
  `taxes` list — the untaxed base, which a tax invoice has to state too.
* The entries are an aggregation of `price_subtotal` and `price_total`, the
  amounts Odoo already computed. Nothing is recomputed, so the figures are in
  the document currency and `base` and `amount` add up to `amount_untaxed` and
  `amount_tax` exactly.

On import, the taxes of a line are matched in this order: XML id, then name
within the same `type_tax_use`, then the rate itself — so a tax renamed on the
other side is still recognised. If any tax on a line cannot be matched, the
field is left alone for Odoo to fill from the product and the partner: applying
only the ones that did resolve would quietly change the document's totals.
`tax_summary` itself is informational and is ignored on import; Odoo derives the
totals from the lines.

## Behaviour on import

* Records are matched on `external_ref`. Importing the same file twice creates
  nothing the second time.
* Documents are always created as **drafts**. Turn on *Confirm Imported
  Documents* to have orders confirmed and invoices and payments posted through
  their own business methods.
* A posted invoice or payment is never rewritten by a later import; it is
  counted as skipped.
* Document numbers coming from the other system are stored in the reference
  field, not forced onto the Odoo sequence.
* Each record is imported inside its own savepoint, so one rejected record
  cannot take the rest of the file down with it.

## Setup

1. *Settings → Data Exchange*: set the exchange directory. The Odoo server process must
   be able to read and write there.
2. Choose which entities take part, and optionally the date from which
   documents are exchanged.
3. Enable the scheduled actions *Data Exchange: export to external system*
   and *Data Exchange: import from external system* (both are off after
   installation), or
   press *Export Now* / *Import Now*.
4. Check the results under *Data Exchange → Exchange Log*.

## Upgrading from an earlier version

The `atm.orderlist` model is still there and its two methods now delegate
to the exchange engine, so scheduled actions created by earlier versions keep
working. They only handle sales orders — switch to the new crons to exchange
everything else.

## License

LGPL-3

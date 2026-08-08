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
      "lines": [
        {
          "name": "Office Lamp",
          "quantity": 15.0,
          "price_unit": 50.0,
          "product": { "external_ref": "odoo/product.product/6", "name": "Office Lamp" }
        }
      ]
    }
  ]
}
```

References between records are never database ids. Business records carry an
`external_ref`; reference data (currencies, units of measure, accounts) is
described by name, code and XML id, and resolved against the local database on
import. That is what allows the same file to be loaded into a different
database.

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

1. *Settings → ATM*: set the exchange directory. The Odoo server process must
   be able to read and write there.
2. Choose which entities take part, and optionally the date from which
   documents are exchanged.
3. Enable the scheduled actions *ATM: export to external system* and
   *ATM: import from external system* (both are off after installation), or
   press *Export Now* / *Import Now*.
4. Check the results under *ATM → Exchange Log*.

## Upgrading from an earlier version

The `atm.orderlist` model is still there and its two methods now delegate
to the exchange engine, so scheduled actions created by earlier versions keep
working. They only handle sales orders — switch to the new crons to exchange
everything else.

## License

LGPL-3

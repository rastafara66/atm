# Changelog

All notable changes to this module are recorded here.
The technical name stays `atm`; earlier releases were published under the
name "ATM - Automated Transaction Mechanics". Versions follow the Odoo
convention: `<odoo series>.<major>.<minor>.<patch>`.

## 2.0.4 — 2026-08-16
### Changed
- Store description now points to **Контрагенти з ЄДР**, a free module by the same
  author: fill a partner record from its Ukrainian registry code. It is the natural
  next step right after an import from 1C/BAS, when the counterparties exist but
  every field is empty.

## 2.0.3 — 2026-08-08

- The listing showed a hand-written JSON sample where the screenshot of a real
  exported file belongs. Swapped: the real file is shown, the invented one is
  gone.

## 2.0.2 — 2026-08-08

- The Ukrainian text on the listing page arrived as mojibake: the Apps Store
  serves the description without a charset, so every non-ASCII character is now
  written as an HTML entity, the way the other published module does it.
- Removed the screenshot of a JSON file from the description: the same file is
  already shown as text right above it. It stays in the store gallery.

## 2.0.1 — 2026-08-08

Everything below was written while 2.0.0 still carried the same version number,
which is why the store kept showing the old listing: the Apps Store refreshes a
module's page from the manifest version, and it had not changed.

- Ukrainian interface and a Ukrainian section on the listing page.
- New icon and store banner, without the ATM lettering.
- Screenshots on the listing page, and a changelog section on it.
- Exchange log counts every record the file held and shows *Skipped*.
- Payments store their source number in `memo` (18.0+) / `ref` (16.0–17.0).
- Settings screen opens again, and a disabled entity stays disabled.

## 2.0.0 — 2026-08-08

Rewritten from an exporter of sales orders into a general document exchange
engine. Available for Odoo 16.0, 17.0, 18.0 and 19.0.

### Added

- **Ten exchangeable entities** instead of one: contacts, products, sales
  orders, purchase orders, customer invoices, vendor bills, customer and vendor
  credit notes, customer and vendor payments. Each lands in its own file and can
  be switched on or off separately.
- **External references.** Records are matched between systems by a stable key
  held in `atm_external_ref`, so a file exported from one database can be
  imported into another, and importing the same file twice creates nothing the
  second time.
- **Exchange log** (`Data Exchange → Exchange Log`) recording every run: direction,
  entity, file, and created / updated / skipped / failed counters.
- **Settings screen** with the exchange directory, a date from which documents
  are exchanged, a system code used to build references, per-entity switches,
  and *Export Now* / *Import Now* buttons.
- **Confirm Imported Documents** setting. Off by default: imported documents are
  created as drafts, and confirming or posting them goes through Odoo's own
  business methods rather than a write to `state`.
- **New icon and store banner**, showing two documents exchanged in both
  directions. The previous icon carried the ATM lettering. Both are drawn
  from code by `tools/make_icons.py` and can be regenerated.
- **Ukrainian interface** (`i18n/uk.po`). The wording follows Ukrainian
  accounting usage rather than a literal rendering: contacts are
  «Контрагенти», products «Номенклатура» -- what the audience coming from
  1C or BAS reads without stumbling. The listing page carries a Ukrainian
  section too.
- Two scheduled actions, one per direction, both disabled after installation.
- A *Data Exchange Manager* group guarding the configuration and the manual run.

### Changed

- Document numbers coming from the other system are stored in the reference
  field instead of being forced onto the Odoo sequence, which used to collide
  with numbers the local sequence had already issued.
- A posted invoice or payment is never rewritten by a later import; it is
  counted as skipped.
- Each record is imported inside its own savepoint, so a record the database
  rejects no longer aborts the whole run.
- A reference to a business record that cannot be resolved fails that record
  instead of silently producing a document line without a product.
- The exchange skips fields the running Odoo version does not define, which
  keeps one set of entity definitions valid across four series.

### Fixed

- Exports wrote database ids for partners and products. Those ids are local to
  a database and pointed at unrelated records once the file was read anywhere
  else.
- The manifest referenced `static/src/components/export_dir_field.js`, while the
  file on disk was named `ExportDirField.js`, so the module could not install.
- A controller called into `atm.settings` and rendered `view_atm_settings_form`,
  neither of which exists.
- Invoice and order lines were dropped from the export: from Odoo 17 on, an
  ordinary line carries `display_type = 'product'`, which the old filter read as
  "this is a layout line".
- Products travelled without their purchase unit of measure, which Odoo requires
  to share a category with the default one; products were rejected on import,
  and the orders using them failed in turn.
- Values Odoo derives itself were decided by the `readonly` flag alone. Up to
  Odoo 16 plain fields were readonly by document state, so vendor bills arrived
  without an invoice date and could not be validated.
- The settings page answered "Something went wrong": *Exchange Documents Since*
  was a Date bound to a config parameter, and `res.config.settings` accepts only
  boolean, integer, float, char, selection, many2one and datetime there.
- An entity switched off came back on at the next run. Odoo deletes a config
  parameter when a boolean is saved as False, which is indistinguishable from
  "never configured"; the switches now store `True` / `False` explicitly.
- Payments kept their source number in a field that does not exist:
  `account.payment` has `memo` from Odoo 18 on and `ref` before that.
- The record counter and the run state both read `Failed` in English but
  need different words elsewhere, so the counter is now `Failures` and the
  two translate apart.
- The exchange log read as if nothing had happened when documents were
  skipped: *Records* counted only created and updated rows, and the
  *Skipped* column was hidden by default. Importing a file back into the
  database it came from showed zeros everywhere. *Records* is now what the
  file held, and created + updated + skipped + failed accounts for all of it.

### Compatibility

`atm.orderlist` and its two methods are kept and now delegate to the exchange
engine, so scheduled actions created by version 1.x keep working after the upgrade.
They still cover sales orders only.

### Verified

Exported a demo database and imported it into an empty one of the same series,
then imported a second time:

| Odoo | Result |
| ---- | ------ |
| 19.0 | all entities matched the exported files, except the demo combo product, which Odoo itself refuses to create without a combo choice |
| 18.0 | same |
| 17.0 | full match, no failures |
| 16.0 | full match (the target database needs a chart of accounts) |

The second import created no records in any series. Odoo ships no payments in
its demo data, so customer and vendor payments were tested against records
created for the purpose. The settings page was exercised separately on each
series: open, save, read back, and confirm a disabled entity stays disabled.

## 1.x — 2023–2024

Exported confirmed sales orders to a single `order_list.json` and read them
back. Published for Odoo 14.0, 15.0 and 16.0.

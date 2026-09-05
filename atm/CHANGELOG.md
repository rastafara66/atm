# Changelog

All notable changes to this module are recorded here.
The technical name stays `atm`; earlier releases were published under the
name "ATM - Automated Transaction Mechanics". Versions follow the Odoo
convention: `<odoo series>.<major>.<minor>.<patch>`.

## 2.3.1 — 2026-09-05

### Changed

- Author website now points at the line's own apps page,
  `https://aktiv.in.ua/dodatky/`. It used to point at the GitHub repository.

- The module now ships its own `CHANGELOG.md`. Until this build only the
  repository had one, so whoever downloaded the package for this series got no
  history inside the module at all.

## 2.3.0 — 2026-09-05

### Added

- **Version check.** Odoo never asks the App Store whether a third-party module
  has been updated: its "Upgrade" button compares what is installed against
  what is already on disk. So a customer who downloaded a build with a bug kept
  that bug until they happened to revisit the store page. That is not a
  hypothesis — in a sibling module a crash was fixed and published within the
  hour while every existing install stayed broken.

  Once a day a scheduled action asks which version is current, and a newer one
  is announced on the exchange log record and in the settings, with a link to
  the store. Nothing is ever downloaded or installed automatically: a module
  placed in an addons directory by hand has to be replaced the same way.

  The request is a bare GET. It carries no install id, no database name and not
  even the version you are running — only which series to answer for. It is on
  by default for that reason, unlike error reports, where there is something to
  consent to. It can be switched off, or pointed at your own endpoint, in
  Settings › Data Exchange › Updates.

- The check covers the **1C / BAS Connector** as well, and a test now fails the
  build if a module of this family is ever left off that list — the cheap half
  of the design is that an add-on needs no check of its own, and its price is
  that a forgotten name fails silently.

### Fixed

- The version endpoint answered for the 19.0 branch whatever was asked, so an
  install of an earlier series would eventually have been told that "19.0.x is
  newer than 16.0.x" — true as arithmetic, false as advice, and pointing at a
  module it cannot run. The series now travels with the question, and an answer
  from another series is discarded rather than shown.

## 2.2.2 — 2026-08-19

### Fixed

- The 2.2.1 entry reached the changelog file but not the listing page, so the
  store refreshed a page that read exactly as before. The store renders the
  page from the manifest version, and 2.2.1 had already been scanned by then —
  hence this version, which carries the same fix and the page to go with it.

## 2.2.1 — 2026-08-19

### Fixed

- The unique constraint behind error report deduplication was never created on
  Odoo 19: `_sql_constraints` is no longer applied there, only warned about.
  It was declared that way deliberately, because the method that used to apply
  it still exists in 19.0 and the older spelling therefore looked safe on all
  four series. It is not: checking `pg_constraint` after an install showed no
  constraint at all. 19.0 now uses `models.Constraint`; 16.0 to 18.0 keep
  `_sql_constraints`, where it does work, verified the same way.

  Deduplication itself was unaffected -- a report is looked up before being
  queued -- so this closed a race, not a visible fault.

## 2.2.0 — 2026-08-19

### Added

- **Automatic error reports**, off unless switched on in the settings. The
  exchange runs unattended, so a failure is usually noticed by nobody until
  someone wonders why the files stopped arriving. An unexpected failure now
  queues itself and is sent by a scheduled action, never at the moment it
  happens.
- The text of the error is **never sent**. Only the exception class, the lines
  of code it passed through with paths cut back to the module root, the
  versions, an HTTP status if there was one, a random per-database id, and
  whatever the user types into the comment box. This module handles contacts,
  invoices and payments, so an error message here plausibly contains a customer
  name or a sum, and filtering such a text with patterns is a losing game — a
  name has no pattern. Nothing identifying can leak through a field that only
  ever holds `KeyError`.
- **Error Reports** list and form under the *Data Exchange* menu. The *What
  gets sent* tab shows the request body itself, not a description of it, so
  "what do you send about me?" has a literal answer. Reports can be commented,
  sent by hand or deleted.
- Failures that are not defects are never reported: the module talking to the
  user, and incoming data this database cannot resolve. The latter is a new
  `AtmDataError`, raised where a document refers to something never imported —
  these arrive by the fileful, are already counted as *failed* in the exchange
  log, and would bury a real defect.
- The same failure is queued once and counted rather than queued again, with a
  ceiling per day, so a bug inside a loop cannot flood anything.
- First tests in this module: twelve of them, covering consent (including that
  "never asked" counts as no), what is and is not a defect, deduplication, and
  path shortening. The load-bearing one raises an error stuffed with a customer
  name, a document number, an address and a sum, and requires that none of it
  reaches the outgoing JSON.

## 2.1.1 — 2026-08-19

### Changed

- Screenshots of the real screens, in both languages: the settings screen, the
  entity switches, the exchange log, an invoice carrying two VAT rates, and the
  exported file showing the `tax_summary` block and the taxes on each line. The
  store gallery is the English set, led by the invoice; the listing page shows
  both languages. The three older screenshots are replaced.

## 2.1.0 — 2026-08-18

### Added

- **VAT broken down by rate.** Documents used to carry a single `amount_tax`
  figure, which is enough to reconcile a total but not to raise a tax invoice:
  that needs the base and the tax of every rate stated separately. Sales orders,
  purchase orders, invoices, bills and credit notes now also carry a
  `tax_summary` block with `base`, `amount`, `total` and `rate` per rate, and an
  untaxed group for lines that carry no tax at all. The figures are an
  aggregation of the amounts Odoo already computed, never a recomputation, so
  they stay in the document currency and add up to `amount_untaxed` and
  `amount_tax` exactly.
- **Taxes on document lines.** Each line lists its taxes, and an incoming line
  gets them applied back. A tax is matched by external id, then by name within
  the same direction, then by its rate -- so a tax renamed on the other side is
  still recognised. Lines are grouped by their whole set of taxes, so a line
  carrying two of them forms a group of its own instead of being split between
  them.
- Lines also carry `price_total`, the amount including tax.

### Changed

- An entity definition may now name several alternatives for one field, tried in
  order. The taxes of a line are `tax_id` on a sales line and `taxes_id` on a
  purchase line up to 18.0, and `tax_ids` for both in 19.0; one definition now
  covers all four series.
- A tax the importing database does not know leaves the field untouched for Odoo
  to fill from its own defaults, rather than applying the subset that did
  resolve: a partially applied tax set would quietly change the document totals.
- Store description now points to **Контрагенти з ЄДР**, a free module by the same
  author: fill a partner record from its Ukrainian registry code. It is the natural
  next step right after an import from 1C/BAS, when the counterparties exist but
  every field is empty. This reached the 19.0 series as 2.0.4 and arrives here
  together with the VAT breakdown.

### Fixed

- The module could not be installed at all on this series: the exchange log view
  was written with `<list>`, the element Odoo uses from 18.0 on, where this
  series knows only `<tree>`. Loading the view aborted the installation.

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

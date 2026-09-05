# Changelog — Data Exchange (`atm`)

JSON file exchange between Odoo and another accounting system. Newest on top.
Обмін файлами між Odoo та іншою обліковою системою. Найновіше — зверху.

## 19.0.2.3.1 — 2026-09-05

### Changed

- Author website now points at the line's own apps page,
  `https://aktiv.in.ua/dodatky/`. It used to point at the App Store itself —
  the page the visitor had just come from — or at a GitHub repository.

## 19.0.2.3.0 — 2026-09-05

### Added

- **Version check.** Odoo never asks the App Store whether a third-party module
  has been updated: its "Upgrade" button compares what is installed against
  what is already on disk. So a customer who downloaded a build with a bug kept
  that bug until they happened to revisit the store page — not a hypothesis, it
  is what happened in a sibling module when a crash was fixed and published
  within the hour while every existing install stayed broken.

  Once a day a scheduled action asks which version is current, and a newer one
  is announced on the exchange log record and in the settings, with a link to
  the store. Nothing is ever downloaded or installed automatically.

  The request is a bare GET: no install id, no database name, not even the
  version you are running — only which series to answer for. It is on by
  default for that reason, unlike error reports, where there is something to
  consent to. Settings › Data Exchange › Updates switches it off, or points it
  at your own endpoint.

- The check covers the **1C / BAS Connector** as well, and a test now fails the
  build if a module of this family is ever left off that list — an add-on needs
  no check of its own, and the price of that is that a forgotten name fails
  silently.

### Fixed

- The version endpoint used to answer for the 19.0 branch whatever was asked,
  so an install of an earlier series would eventually have been told that
  "19.0.x is newer than 16.0.x" — true as arithmetic, false as advice, and
  pointing at a module it cannot run. The series now travels with the question,
  and an answer from another series is discarded rather than shown.

## 19.0.2.2.4 — 2026-09-04

### Fixed

- 🔴 **The support address is back on the store page.** Moving the
  descriptions onto the shared generator dropped it from EVERY page in one
  command: pages still built, nothing failed, and a buyer simply had nowhere
  to write. The support block is now emitted by the generator itself, from
  the manifest's `support` key, and the build fails if it is missing.

## 19.0.2.2.3 — 2026-09-04

### Changed

- **Store description rebuilt on the shared layout** used across the whole line
  (Odoo's own `oe_container` / `oe_row` / `oe_span6` classes) instead of hand-rolled
  inline styles — in the catalogue the modules looked like products by different
  authors. Generated from `3A/tools/store/specs/atm.py`, so the layout cannot drift.
- Changelog on the page grouped into meaningful entries; the version comes straight
  from `__manifest__.py`, so page and manifest cannot disagree (invariant 93).

### Added

- **This CHANGELOG.md.** The module never had one, although the line requires a
  per-module changelog — the store page carried the history, the repository did not.


## 19.0.2.2.0 — 2026-08

- Ten entities with per-entity switches, external-id matching (re-import never duplicates), drafts on import, VAT split per rate, exchange log.
  Десять сутностей із перемикачами, зіставлення за зовнішнім ключем, чернетки при імпорті, розкладка ПДВ за ставками, журнал обміну.

## 19.0.2.0.0 — 2026-07

- Ukrainian interface and documentation.
  Український інтерфейс і документація.

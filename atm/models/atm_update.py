# -*- coding: utf-8 -*-
"""Tell the user when a newer version of Data Exchange exists.

Odoo does not do this for third-party modules. Its "Upgrade" button compares
what is installed against what is already **on disk** -- it never asks the App
Store whether something newer was published. So a customer who downloaded a
build with a bug keeps that bug forever unless they happen to revisit the store
page. In Bank Sync exactly that happened: a crash was fixed and published within
the hour, and every existing install stayed broken.

For a paid add-on it is money left on the table: nobody asks for a refund, they
simply never update.

Hence a small check of our own, deliberately the least intrusive thing that
works:

* it is a **GET with no body and no identifier** -- no install id, no versions,
  no database name. The server learns only that somebody asked what the latest
  version is, which is what any visitor to the store page reveals anyway. There
  is nothing here to weigh up, which is why this is on by default while error
  reports (see ``atm_error_report.py``) are off until asked for;
* it runs **once a day** from a scheduled action, never during a page load;
* it can never break anything: any failure is swallowed and a database with no
  answer simply shows no banner. The manual check is the exception -- a person
  who pressed a button is owed a reason, or "you are up to date" and "the
  request never left the building" look identical.

The banner links to the store. It cannot install anything -- a module dropped
into an addons directory by hand has to be replaced the same way -- so promising
a one-click upgrade would be a lie.

Implementation lifted from ``bank_sync_base/models/bank_sync_update.py``, where
it is already debugged against live installs. Two copies drifting apart would
buy nothing.

Where the banner lives. Bank Sync puts it on the connection form and "Aktiv" on
the submission register, because those are screens their users open by hand.
Data Exchange has no such screen: it runs from cron and is looked at when
something needs attention. So the banner sits on the exchange log record -- the
place you land when you go looking -- and the settings page repeats it with a
manual check, because that is where this module is actually configured.
"""
import json
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

PARAM_UPDATE_CHECK = 'atm.update_check'
PARAM_LATEST = 'atm.latest_versions'
PARAM_URL = 'atm.update_url'
PARAM_CHECKED = 'atm.latest_checked'

# The same endpoint the other products use. It reads versions from the
# manifests on branch 19.0 -- that is, from what the store actually serves --
# so there is no hand-kept copy of a version number to forget about. A second
# service for a second product would just be a second thing to remember.
DEFAULT_URL = 'https://yellow.in.ua/bank-sync/latest'

# 🔴 Серія в адресі, а не 19.0 намертво. Сторінка додатка існує ОКРЕМО для
# кожної серії (перевірено: /16.0/atm/ ... /19.0/atm/ — усі чотири віддають
# 200), і послати інсталяцію 16.0 на сторінку 19.0 означає запропонувати їй
# збірку, якої вона встановити не може. Це та сама помилка, від якої захищає
# порівняння версій у межах серії, — тільки на кроці пізніше, вже в посиланні.
STORE_URL = 'https://apps.odoo.com/apps/modules/%s/%s/'

CHECK_TIMEOUT = 10

# Ours only. A version string for somebody else's module has no business
# driving our banner.
#
# 🔴 Every module of this family belongs here. An add-on needs no update check
# of its own -- it is enough that the base module names it -- but that is
# exactly why a forgotten name is dangerous: nothing fails, no test goes red,
# and its buyers are simply never told a fix exists. That is not hypothetical:
# `bank_sync_privat` sat unlisted for four days. `test_every_module_is_listed`
# now fails the build instead of trusting anyone's memory.
KNOWN_MODULES = ('atm', 'atm_1c')


def series_of(version):
    """``"19.0.2.3.0"`` -> ``"19.0"``. Empty when there is nothing to read.

    🔴 Data Exchange ships four series at once (16.0, 17.0, 18.0, 19.0), each
    from its own branch, each its own listing in the store. Compared as plain
    numbers, ``19.0.2.2.0`` is "newer" than ``16.0.2.2.0`` -- so an endpoint
    that only knew the 19.0 branch would tell every 16.0 install that an update
    exists, and point it at a module it cannot install. Worse than silence: it
    would burn the one message we get to send.

    So the series travels with the question and is checked again in the answer.
    """
    parts = (version or '').split('.')
    return '.'.join(parts[:2]) if len(parts) >= 2 else ''


def parse_version(text):
    """``"19.0.1.2.10"`` -> ``(19, 0, 1, 2, 10)``.

    🔴 Compared as numbers, not as text: as strings ``"19.0.1.2.10"`` sorts
    *below* ``"19.0.1.2.9"``, so the tenth fix of a series would stop being
    offered -- precisely when a series has had ten fixes and updating matters
    most.
    """
    parts = []
    for chunk in (text or '').split('.'):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)


class AtmUpdate(models.AbstractModel):
    _name = 'atm.update'
    _description = 'Data Exchange Update Check'

    @api.model
    def _enabled(self):
        # Unset means on: this call carries nothing about the user, and a check
        # nobody knows to switch on would never run.
        return self.env['ir.config_parameter'].sudo().get_param(
            PARAM_UPDATE_CHECK, 'on') != 'off'

    @api.model
    def _series(self):
        """Which branch this install came from, e.g. ``"19.0"``.

        Read from the installed module rather than from ``odoo.release``: they
        agree in every sane install, and when they do not, the number that
        matters is the one on the module the customer actually downloaded.
        """
        module = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'atm')], limit=1)
        return series_of(module.installed_version)

    @api.model
    def _run_check(self):
        """Do the check and say what happened. Returns ``(ok, reason)``.

        Split out from ``_cron_check`` for the sake of whoever pressed the
        button: swallowing every failure is right for the daily job -- a missed
        check is not an incident -- but it leaves a manual check with nothing
        to say.
        """
        if not self._enabled():
            return False, _('Version checking is switched off.')
        params = self.env['ir.config_parameter'].sudo()
        url = params.get_param(PARAM_URL, DEFAULT_URL)
        if not url:
            return False, _('No address is configured for the version check.')

        import requests
        # The only thing the request carries. It says which shelf to read, not
        # who is asking: every install of a series sends the identical two
        # characters, so it identifies nobody. An endpoint that does not know
        # the parameter simply ignores it and answers for the newest series --
        # which the answer check below then discards rather than believes.
        series = self._series()
        try:
            response = requests.get(url, timeout=CHECK_TIMEOUT,
                                    params={'series': series} if series else None)
            response.raise_for_status()
            published = response.json()
        except Exception as error:  # noqa: BLE001 - a missed check is not an incident
            return False, _('Could not reach %(url)s: %(error)s',
                            url=url, error=error)
        if not isinstance(published, dict):
            return False, _('%s answered with something that is not a version '
                            'list.', url)

        # Ours, and from our own series. An answer for another branch is
        # dropped here rather than shown: a number the customer cannot install
        # is worse than no number, and this is where an endpoint that ignored
        # the `series` parameter gets caught.
        clean = {name: str(published[name])[:32]
                 for name in KNOWN_MODULES
                 if isinstance(published.get(name), str)
                 and (not series or series_of(published[name]) == series)}
        if not clean:
            return False, _('%(url)s knows of no %(series)s version of these '
                            'modules.', url=url, series=series or '?')
        params.set_param(PARAM_LATEST, json.dumps(clean))
        params.set_param(PARAM_CHECKED,
                         fields.Datetime.to_string(fields.Datetime.now()))
        return True, ''

    @api.model
    def _cron_check(self):
        """The daily job: never raises, never reports, just refreshes the cache."""
        ok, reason = self._run_check()
        if not ok and reason:
            _logger.info('Data Exchange update check skipped: %s', reason)
        return ok

    @api.model
    def _published(self):
        raw = self.env['ir.config_parameter'].sudo().get_param(PARAM_LATEST)
        try:
            return json.loads(raw) if raw else {}
        except ValueError:
            return {}

    @api.model
    def _outdated(self):
        """Installed modules of ours with a newer published version.

        Returns ``[(module name, installed, published)]``.
        """
        published = self._published()
        if not published:
            return []
        modules = self.env['ir.module.module'].sudo().search(
            [('name', 'in', KNOWN_MODULES), ('state', '=', 'installed')])
        out = []
        for module in modules:
            latest = published.get(module.name)
            if not latest:
                continue
            # Checked a second time, on cached data this time: a stored answer
            # outlives the request that fetched it, and an upgrade to another
            # Odoo series would otherwise start advertising the old branch.
            if series_of(latest) != series_of(module.installed_version):
                continue
            if parse_version(latest) > parse_version(module.installed_version):
                out.append((module.name, module.installed_version, latest))
        return out

    @api.model
    def update_banner(self):
        """Banner text and link, or ``(False, False)``."""
        outdated = self._outdated()
        if not outdated:
            return False, False
        name, installed, latest = outdated[0]
        return _(
            'A newer version of %(module)s is available: %(latest)s '
            '(you have %(installed)s).',
            module=name, latest=latest, installed=installed
        ), STORE_URL % (series_of(installed) or '19.0', name)


class AtmExchangeLogUpdate(models.Model):
    """The banner goes on the log record -- where you land when you look.

    Putting it only in the settings would show it to the one person who is
    already hunting for updates, which is the very reason Odoo's own "Upgrade"
    button does not help.
    """
    _inherit = 'atm.exchange.log'

    update_message = fields.Char(compute='_compute_update_message')
    update_url = fields.Char(compute='_compute_update_message')

    def _compute_update_message(self):
        # Asked once for the whole recordset: the answer does not depend on the
        # record, and a log list can be long.
        message, url = self.env['atm.update'].update_banner()
        for log in self:
            log.update_message = message
            log.update_url = url

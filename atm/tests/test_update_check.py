# -*- coding: utf-8 -*-
"""Telling the user that a newer version exists.

Odoo never asks the App Store whether a third-party module has been updated, so
a customer keeps a known bug until they happen to revisit the store page. That
is not hypothetical: in Bank Sync a crash was fixed and published within the
hour while every existing install stayed broken.
"""
import json
import os
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from ..models import atm_update as updating


def our_addons_beside(addons_dir):
    """Modules of ours, in ``addons_dir``, built on top of Data Exchange.

    Both halves of the rule matter. The author keeps somebody else's add-on
    from failing our build; the dependency on ``atm`` keeps an unrelated module
    of ours (Bank Sync, 3A-dealer) out of a list that only covers this family.
    """
    found = set()
    for name in sorted(os.listdir(addons_dir)):
        manifest = os.path.join(addons_dir, name, '__manifest__.py')
        if name == 'atm' or not os.path.isfile(manifest):
            continue
        try:
            with open(manifest, encoding='utf-8') as handle:
                spec = eval(handle.read(), {'__builtins__': {}})  # noqa: S307
        except Exception:  # noqa: BLE001 - not a manifest we can read
            continue
        if (isinstance(spec, dict) and spec.get('author') == 'chukhin'
                and 'atm' in (spec.get('depends') or [])):
            found.add(name)
    return found


class _Answer:
    """A stand-in for a requests response, so no test touches the network."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@tagged('post_install', '-at_install')
class TestUpdateCheck(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Update = cls.env['atm.update']
        cls.params = cls.env['ir.config_parameter'].sudo()

    def _publish(self, versions):
        self.params.set_param(updating.PARAM_LATEST, json.dumps(versions))

    def _installed_version(self):
        module = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'atm')], limit=1)
        return module.installed_version

    def _newer(self):
        """A version above the installed one, but on the same series."""
        return '%s.99.0.0' % updating.series_of(self._installed_version())

    # -- comparing versions -------------------------------------------------
    def test_versions_compare_as_numbers_not_text(self):
        """As strings "19.0.1.2.10" sorts below "19.0.1.2.9"."""
        self.assertGreater(updating.parse_version('19.0.1.2.10'),
                           updating.parse_version('19.0.1.2.9'))

    def test_a_junk_version_does_not_raise(self):
        """A malformed answer must not break the daily job."""
        self.assertEqual(updating.parse_version('19.0.x.1'), (19, 0, 0, 1))
        self.assertEqual(updating.parse_version(''), (0,))
        self.assertEqual(updating.parse_version(None), (0,))

    def test_series_is_the_first_two_numbers(self):
        self.assertEqual(updating.series_of('19.0.2.3.0'), '19.0')
        self.assertEqual(updating.series_of('16.0.2.2.0'), '16.0')
        self.assertEqual(updating.series_of('nonsense'), '')
        self.assertEqual(updating.series_of(''), '')
        self.assertEqual(updating.series_of(None), '')

    # -- what the user is told ---------------------------------------------
    def test_newer_version_is_reported_as_outdated(self):
        self._publish({'atm': self._newer()})
        self.assertIn('atm', [row[0] for row in self.Update._outdated()])

    def test_same_version_is_not_reported(self):
        self._publish({'atm': self._installed_version()})
        self.assertEqual(self.Update._outdated(), [])

    def test_older_published_version_is_not_reported(self):
        """A stale answer must never talk anybody into downgrading."""
        self._publish({'atm': '%s.0.0.0' % updating.series_of(
            self._installed_version())})
        self.assertEqual(self.Update._outdated(), [])

    def test_a_version_from_another_series_is_never_offered(self):
        """🔴 The one that would have been a lie.

        Data Exchange ships 16.0 through 19.0 at once. As numbers 19.0.2.2.0
        beats 16.0.2.2.0, so an endpoint that answered for the wrong branch --
        or a cached answer that outlived an Odoo upgrade -- would tell a 16.0
        install to install a module it cannot run. Silence is the only honest
        answer here.
        """
        self._publish({'atm': '99.0.1.0.0'})
        self.assertEqual(self.Update._outdated(), [])
        self.assertEqual(self.Update.update_banner(), (False, False))

    def test_nothing_published_means_no_banner(self):
        self.params.set_param(updating.PARAM_LATEST, False)
        self.assertEqual(self.Update._outdated(), [])

    def test_only_our_modules_are_believed(self):
        """A version for somebody else's module drives nothing here."""
        self._publish({'account': '99.0', 'atm': self._newer()})
        self.assertEqual([row[0] for row in self.Update._outdated()], ['atm'])

    def test_the_banner_carries_a_link_to_the_store(self):
        """A notice with nowhere to go is only half the message."""
        self._publish({'atm': self._newer()})
        message, url = self.Update.update_banner()
        self.assertTrue(message)
        self.assertEqual(url, updating.STORE_URL % 'atm')

    def test_no_banner_when_up_to_date(self):
        self._publish({'atm': self._installed_version()})
        self.assertEqual(self.Update.update_banner(), (False, False))

    # -- the check itself ---------------------------------------------------
    def test_check_is_skipped_when_switched_off(self):
        self.params.set_param(updating.PARAM_UPDATE_CHECK, 'off')
        with patch('requests.get') as get:
            self.assertFalse(self.Update._cron_check())
        get.assert_not_called()

    def test_unset_means_on(self):
        """This request carries nothing, so an unanswered database still checks.

        The opposite of the error reports, deliberately: there the default is
        off, because there is something to consent to.
        """
        self.params.set_param(updating.PARAM_UPDATE_CHECK, False)
        self.assertTrue(self.Update._enabled())

    def test_an_unreachable_server_is_not_an_incident(self):
        self.params.set_param(updating.PARAM_UPDATE_CHECK, 'on')
        with patch('requests.get', side_effect=OSError('no route to host')):
            self.assertFalse(self.Update._cron_check())

    def test_a_nonsense_answer_is_ignored(self):
        self.params.set_param(updating.PARAM_UPDATE_CHECK, 'on')
        self.params.set_param(updating.PARAM_LATEST, False)
        with patch('requests.get', return_value=_Answer(['not', 'a', 'map'])):
            self.assertFalse(self.Update._cron_check())
        self.assertEqual(self.Update._published(), {})

    def test_a_good_answer_is_stored(self):
        self.params.set_param(updating.PARAM_UPDATE_CHECK, 'on')
        newer = self._newer()
        with patch('requests.get',
                   return_value=_Answer({'atm': newer, 'evil': {'x': 1}})):
            self.assertTrue(self.Update._cron_check())
        self.assertEqual(self.Update._published(), {'atm': newer})

    def test_the_request_asks_for_our_own_series(self):
        """Otherwise the endpoint answers for the newest branch it knows."""
        self.params.set_param(updating.PARAM_UPDATE_CHECK, 'on')
        with patch('requests.get',
                   return_value=_Answer({'atm': self._newer()})) as get:
            self.Update._run_check()
        self.assertEqual(
            get.call_args.kwargs.get('params'),
            {'series': updating.series_of(self._installed_version())})

    def test_an_answer_for_another_series_is_not_even_stored(self):
        """An endpoint that ignores `series` must not poison the cache.

        Dropping it here as well as at display time matters: the settings page
        reads the stored number straight out, and would otherwise show a
        version this database cannot install.
        """
        self.params.set_param(updating.PARAM_UPDATE_CHECK, 'on')
        self.params.set_param(updating.PARAM_LATEST, False)
        with patch('requests.get',
                   return_value=_Answer({'atm': '99.0.1.0.0'})):
            ok, reason = self.Update._run_check()
        self.assertFalse(ok)
        # Named, not hardcoded: this file is backported to 16.0/17.0/18.0.
        self.assertIn(updating.series_of(self._installed_version()), reason)
        self.assertEqual(self.Update._published(), {})

    def test_a_failed_check_says_why(self):
        """The daily job may stay silent; a person who pressed a button may not.

        Without a reason, "you are up to date" and "the request never left the
        building" are the same blank page.
        """
        self.params.set_param(updating.PARAM_UPDATE_CHECK, 'on')
        with patch('requests.get', side_effect=OSError('no route to host')):
            ok, reason = self.Update._run_check()
        self.assertFalse(ok)
        self.assertIn('no route to host', reason)


@tagged('post_install', '-at_install')
class TestUpdateBannerIsVisible(TransactionCase):
    """A banner nobody can see is the same as no banner at all.

    Tests run as superuser and read fields directly, so neither a missing field
    on the form nor a missing access right shows up here. This one at least
    proves the field exists on the model the view puts it on -- renaming the
    model or dropping the inherit would otherwise pass every other test.
    """

    def test_the_log_record_carries_the_banner_fields(self):
        log = self.env['atm.exchange.log']
        for name in ('update_message', 'update_url'):
            self.assertIn(name, log._fields,
                          'the exchange log form shows %s' % name)

    def test_the_settings_page_reports_a_version(self):
        values = self.env['res.config.settings']._atm_version_values()
        self.assertTrue(values['atm_version_installed'])
        self.assertTrue(values['atm_update_summary'])

    def test_an_unchecked_database_does_not_claim_to_be_current(self):
        """🔴 The failure that looks exactly like success.

        With no answer stored, "you are up to date" would be a guess presented
        as a fact -- and a customer who believes they are current is the one
        thing this whole feature exists to prevent.
        """
        self.env['ir.config_parameter'].sudo().set_param(
            updating.PARAM_LATEST, False)
        summary = self.env['res.config.settings']._atm_version_values()[
            'atm_update_summary']
        self.assertIn('not known', summary)

    def test_the_settings_page_actually_renders(self):
        """A field on the model but not on the form is invisible to the rest.

        Every other test here reads fields directly, so a typo in the view --
        or a field the arch names and the model does not -- would pass them all
        and fail only in the browser.

        The assembled view, not our own arch: an xpath that lands nowhere still
        leaves our file exactly as written. `get_view` is the 17+ spelling and
        `fields_view_get` the older one -- this module ships on four series
        from one source, so the test asks rather than assumes.
        """
        settings = self.env['res.config.settings']
        if hasattr(settings, 'get_view'):
            arch = settings.get_view(view_type='form')['arch']
        else:  # Odoo 16 and earlier
            arch = settings.fields_view_get(view_type='form')['arch']
        self.assertIn('atm_update_summary', arch)
        self.assertIn('action_atm_check_update', arch)


@tagged('post_install', '-at_install')
class TestModuleListIsComplete(TransactionCase):
    """The list of our modules must grow when a module is added.

    An add-on carries no update check of its own: it is enough that the base
    module names it in ``KNOWN_MODULES``. That is the cheap half of the design,
    and its price is that a forgotten name fails silently -- nothing breaks, no
    test goes red, and the buyers of that add-on are simply never told a fix
    exists. It already happened once in this line: `bank_sync_privat` shipped
    three weeks after the check was written and sat unlisted.

    So the invariant is not "atm_1c is listed" -- that would only cover the one
    module we happen to have today. It is "every add-on of ours beside us is
    listed", which fails on the next one too.
    """

    def test_every_module_is_listed(self):
        from odoo.addons import atm

        addons = os.path.dirname(os.path.dirname(atm.__file__))
        missing = our_addons_beside(addons) - set(updating.KNOWN_MODULES)
        self.assertFalse(
            missing,
            'модулі є, а в KNOWN_MODULES їх нема: %s. Їхні покупці ніколи не '
            'дізнаються про виправлення — банер мовчатиме, і ніщо не впаде.'
            % ', '.join(sorted(missing)))

    def test_the_scan_is_not_vacuous(self):
        """The invariant above passes trivially if the scan finds nothing.

        🔴 That is the third of the error classes tests do not see: a check
        that works, finds nothing and reports success. A customer install has
        no sibling add-on at all, so "found nothing" cannot be an assertion
        there -- which is exactly why the scanner itself is checked here,
        against a directory built for the purpose.
        """
        import tempfile

        def write(root, name, spec):
            os.makedirs(os.path.join(root, name))
            with open(os.path.join(root, name, '__manifest__.py'), 'w',
                      encoding='utf-8') as handle:
                handle.write(repr(spec))

        with tempfile.TemporaryDirectory() as root:
            write(root, 'atm', {'author': 'chukhin', 'depends': []})
            write(root, 'atm_new', {'author': 'chukhin', 'depends': ['atm']})
            write(root, 'atm_theirs', {'author': 'someone', 'depends': ['atm']})
            write(root, 'bank_sync_base', {'author': 'chukhin',
                                           'depends': ['account']})
            os.makedirs(os.path.join(root, 'not_a_module'))

            self.assertEqual(our_addons_beside(root), {'atm_new'})

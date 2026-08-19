# -*- coding: utf-8 -*-
"""What the crash reporter promises, and what holds those promises.

The load-bearing test is :meth:`test_payload_carries_no_business_data`. If
anyone ever decides to put the exception text into a report, that test is what
fails. Do not remove it.
"""

import json

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..models.atm_error_report import PARAM_CONSENT, PARAM_INSTALL_ID
from ..models.atm_exceptions import AtmDataError


@tagged('post_install', '-at_install')
class TestAtmErrorReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Report = cls.env['atm.error.report']
        cls.params = cls.env['ir.config_parameter'].sudo()

    def _enable(self):
        # Written on the test's own cursor. The reporter reads consent before
        # it opens its second connection, so no commit is needed -- and Odoo
        # forbids committing inside a test anyway.
        self.params.set_param(PARAM_CONSENT, 'on')

    def _capture(self, error, operation):
        """Raise ``error`` and let the reporter queue it, as production does."""
        try:
            raise error
        except Exception:
            return self.Report._capture(operation)

    def _read_back(self, operation):
        """Read what was queued, through a cursor that can see it.

        The reporter writes in its own connection so the report survives the
        rollback of the failing transaction. Odoo cursors are REPEATABLE READ,
        so this test's transaction cannot see that write -- a fresh cursor can.
        """
        with self.registry.cursor() as cr:
            cr.execute(
                "SELECT id FROM atm_error_report WHERE operation = %s",
                (operation,))
            return [row[0] for row in cr.fetchall()]

    def _delete(self, operation):
        """Rows written on a separate cursor are really committed.

        They are not rolled back between tests in the same class, so each test
        cleans up after itself -- otherwise one test's occurrence counter leaks
        into the next.
        """
        with self.registry.cursor() as cr:
            cr.execute("DELETE FROM atm_error_report WHERE operation = %s",
                       (operation,))

    # ------------------------------------------------------------------
    # The promise that matters
    # ------------------------------------------------------------------
    def test_payload_carries_no_business_data(self):
        """Nothing identifying may reach the wire, however loud the exception.

        The message below is deliberately stuffed with everything this module
        touches. None of it may appear in the outgoing JSON.
        """
        secrets = [
            'Promin LLC', 'INV/2026/00010', '19263.00', 'Sichovykh Striltsiv 12',
            'sergiy@example.com', '123456789012',
        ]
        operation = 'test:leak'
        self.addCleanup(self._delete, operation)
        self._enable()
        self._capture(
            KeyError('customer %s invoice %s for %s at %s (%s), VAT %s'
                     % tuple(secrets)),
            operation)

        ids = self._read_back(operation)
        self.assertEqual(len(ids), 1, 'the failure should have been queued')
        with self.registry.cursor() as cr:
            report = self.env(cr=cr)['atm.error.report'].browse(ids[0])
            payload = json.dumps(report._payload(), ensure_ascii=False)

        for secret in secrets:
            self.assertNotIn(secret, payload,
                             '%r reached the outgoing report' % secret)
        self.assertIn('KeyError', payload, 'the exception class should travel')

    def test_payload_field_is_the_request_itself(self):
        """The form shows the request body, not a summary of it."""
        operation = 'test:payload'
        self.addCleanup(self._delete, operation)
        self._enable()
        self._capture(TypeError('boom'), operation)

        ids = self._read_back(operation)
        with self.registry.cursor() as cr:
            report = self.env(cr=cr)['atm.error.report'].browse(ids[0])
            shown = json.loads(report.payload)
            self.assertEqual(shown, report._payload())
            # The install id is minted when the report is queued, so what the
            # form shows is not missing anything the send would add.
            self.assertTrue(shown['install_id'])

    # ------------------------------------------------------------------
    # Consent
    # ------------------------------------------------------------------
    def test_nothing_is_queued_without_consent(self):
        operation = 'test:silent'
        self.addCleanup(self._delete, operation)
        self.params.set_param(PARAM_CONSENT, 'off')
        self._capture(TypeError('boom'), operation)
        self.assertFalse(self._read_back(operation))

    def test_never_asked_counts_as_no(self):
        """An unset parameter must behave exactly like an explicit refusal."""
        operation = 'test:unasked'
        self.addCleanup(self._delete, operation)
        self.params.set_param(PARAM_CONSENT, '')
        self._capture(TypeError('boom'), operation)
        self.assertFalse(self._read_back(operation))

    # ------------------------------------------------------------------
    # What counts as a bug
    # ------------------------------------------------------------------
    def test_user_errors_are_not_reported(self):
        """The module talking to the user is not a defect."""
        operation = 'test:usererror'
        self.addCleanup(self._delete, operation)
        self._enable()
        self._capture(UserError('The exchange directory is not configured.'),
                      operation)
        self.assertFalse(self._read_back(operation))

    def test_incoming_data_problems_are_not_reported(self):
        """A product the other side never sent is their data, not our bug.

        This is the difference between this module and the others sharing the
        reporter: here such failures arrive by the fileful, and reporting them
        would bury the one real defect.
        """
        operation = 'test:dataerror'
        self.addCleanup(self._delete, operation)
        self._enable()
        self._capture(
            AtmDataError('Cannot resolve product: Promin LLC desk'), operation)
        self.assertFalse(self._read_back(operation))

    def test_unexpected_errors_are_reported(self):
        operation = 'test:realbug'
        self.addCleanup(self._delete, operation)
        self._enable()
        self._capture(AttributeError('NoneType has no attribute id'), operation)

        ids = self._read_back(operation)
        self.assertEqual(len(ids), 1)
        with self.registry.cursor() as cr:
            report = self.env(cr=cr)['atm.error.report'].browse(ids[0])
            self.assertEqual(report.error_type, 'AttributeError')
            self.assertEqual(report.state, 'pending')

    # ------------------------------------------------------------------
    # Volume
    # ------------------------------------------------------------------
    def test_the_same_bug_is_counted_not_requeued(self):
        """A failure in a loop is one report with a count, not a thousand."""
        operation = 'test:repeat'
        self.addCleanup(self._delete, operation)
        self._enable()
        for _unused in range(5):
            self._capture(ZeroDivisionError('division by zero'), operation)

        ids = self._read_back(operation)
        self.assertEqual(len(ids), 1, 'the same failure queued more than once')
        with self.registry.cursor() as cr:
            report = self.env(cr=cr)['atm.error.report'].browse(ids[0])
            self.assertEqual(report.occurrences, 5)

    def test_paths_are_cut_back_to_the_module(self):
        """A developer's home directory must not travel either."""
        from ..models.atm_error_report import _short_path

        self.assertEqual(
            _short_path(r'C:\Users\ivan\odoo\addons\atm\models\atm_exchange.py'),
            'atm/models/atm_exchange.py')
        self.assertEqual(
            _short_path('/home/ivan/.venv/lib/requests/adapters.py'),
            'requests/adapters.py')
        self.assertNotIn('ivan', _short_path('/home/ivan/x/atm/models/a.py'))

    def test_install_id_is_random_and_stable(self):
        """It separates one install failing often from many failing once."""
        self.params.set_param(PARAM_INSTALL_ID, '')
        first = self.Report._install_id()
        self.assertTrue(first)
        self.assertEqual(first, self.Report._install_id())
        self.assertNotIn(self.env.cr.dbname, first)

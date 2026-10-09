# -*- coding: utf-8 -*-
"""An import run names every record it could not write.

"1 failed" alone sends the user to the server log, which they usually cannot
read, and fixing one record at a time is a guessing game about how many are
left. The log message has to carry the count, each failed record with its
position in the file and the reason, and what to do next.
"""
import json
import os
import tempfile

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestImportReport(TransactionCase):

    def setUp(self):
        super().setUp()
        # The messages are compared in English; in a Ukrainian database the
        # same correct code would answer in Ukrainian.
        self.env = self.env(context=dict(self.env.context, lang='en_US'))
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.env['ir.config_parameter'].sudo().set_str(
            'atm.export_dir', self.folder.name)

    def _import_partners(self, records):
        path = os.path.join(self.folder.name, 'partners.json')
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump({'records': records}, handle)
        return self.env['atm.exchange'].import_entity('partner')

    def test_failed_records_are_named_with_their_position(self):
        log = self._import_partners([
            {'external_ref': 'ATM-TEST-1', 'name': 'Test Contact One'},
            {'vat': '1234567890'},
        ])
        self.assertEqual(log.state, 'done')
        self.assertEqual((log.record_count, log.created_count, log.failed_count),
                         (2, 1, 1))
        self.assertIn('Record 2:', log.message)
        self.assertIn('What to do', log.message)

    def test_a_clean_run_has_no_problem_list(self):
        log = self._import_partners([
            {'external_ref': 'ATM-TEST-2', 'name': 'Test Contact Two'},
        ])
        self.assertEqual(log.failed_count, 0)
        self.assertNotIn('What to do', log.message)

    def test_the_list_is_capped_but_the_count_is_exact(self):
        exchange = self.env['atm.exchange']
        problems = ['Record %d: broken' % n for n in range(1, exchange.PROBLEMS_SHOWN + 6)]
        message = exchange._import_message(0, 0, 0, len(problems), problems)
        self.assertIn('Records that could not be imported: %d' % len(problems), message)
        self.assertIn('Record %d: broken' % exchange.PROBLEMS_SHOWN, message)
        self.assertNotIn('Record %d: broken' % (exchange.PROBLEMS_SHOWN + 1), message)
        self.assertIn('... and 5 more.', message)

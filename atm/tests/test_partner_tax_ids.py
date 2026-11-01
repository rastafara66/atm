# -*- coding: utf-8 -*-
"""Two numbers of a Ukrainian partner travel through the file by name, not as a raw `vat`.

Which field holds the EDRPOU / RNOKPP code and which the VAT payer IPN depends on the Odoo series
(models/ua_tax_ids.py): the code is `company_registry` up to 19.0 and `vat` in 20.0, the IPN is `vat`
up to 19.0 and an additional identifier in 20.0. A raw `vat` exported from 19.0 would land in the code
field of 20.0. Numbers here are made up.
"""
import json
import os
import tempfile

from odoo.tests import TransactionCase, tagged

from ..models.entities import ENTITIES_BY_CODE

CODE, IPN = '12345678', '123456789012'


@tagged('post_install', '-at_install')
class TestPartnerTaxIds(TransactionCase):

    def setUp(self):
        super().setUp()
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.env['ir.config_parameter'].sudo().set_param('atm.export_dir', self.folder.name)
        self.ua = self.env.ref('base.ua')

    def _import(self, records):
        with open(os.path.join(self.folder.name, 'partners.json'), 'w', encoding='utf-8') as handle:
            json.dump({'records': records}, handle)
        return self.env['atm.exchange'].import_entity('partner')

    def test_export_names_both_numbers(self):
        Partner = self.env['res.partner']
        partner = Partner.create({'name': 'ТОВ «Експорт»', 'country_id': self.ua.id,
                                  **Partner._l10n_ua_tax_vals(code=CODE, ipn=IPN)})
        data = self.env['atm.exchange']._export_record(ENTITIES_BY_CODE['partner'], partner)
        self.assertEqual((data.get('ua_code'), data.get('ua_ipn')), (CODE, IPN))

    def test_import_puts_numbers_where_the_series_keeps_them(self):
        log = self._import([{'external_ref': 'ATM-UA-1', 'name': 'ТОВ «Імпорт»', 'vat': IPN,
                             'ua_code': CODE, 'ua_ipn': IPN}])
        self.assertEqual(log.failed_count, 0, log.message)
        partner = self.env['res.partner'].search([('atm_external_ref', '=', 'ATM-UA-1')])
        partner.country_id = self.ua
        self.assertEqual(partner._l10n_ua_tax_codes(), (CODE, IPN))
        # Update: the IPN changes, the code stays.
        log = self._import([{'external_ref': 'ATM-UA-1', 'name': 'ТОВ «Імпорт»', 'ua_code': CODE,
                             'ua_ipn': '123456789099'}])
        self.assertEqual(log.failed_count, 0, log.message)
        self.assertEqual(partner._l10n_ua_tax_codes(), (CODE, '123456789099'))


@tagged('post_install', '-at_install')
class TestPartnerNumbersChecked(TransactionCase):
    """A number of the wrong length does not lose the partner: it is corrected or left out, and the log says so.

    Odoo 20 refuses an IPN that is not 12 or 10 digits with a validation error, and the partner would not be
    imported at all; source systems often hold the 8-digit EDRPOU in the IPN field.
    """

    _import = TestPartnerTaxIds._import

    def setUp(self):
        super().setUp()
        # The messages are compared in English; a Ukrainian database answers the same in Ukrainian.
        self.env = self.env(context=dict(self.env.context, lang='en_US'))
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.env['ir.config_parameter'].sudo().set_param('atm.export_dir', self.folder.name)
        self.ua = self.env.ref('base.ua')

    def _partner(self, ref):
        partner = self.env['res.partner'].search([('atm_external_ref', '=', ref)])
        partner.country_id = self.ua
        return partner

    def test_eight_digits_in_the_ipn_field_are_the_code(self):
        log = self._import([{'external_ref': 'ATM-UA-8', 'name': 'ТОВ «Вісім»', 'ua_code': '', 'ua_ipn': CODE}])
        self.assertEqual((log.created_count, log.failed_count), (1, 0), log.message)
        self.assertEqual(self._partner('ATM-UA-8')._l10n_ua_tax_codes(), (CODE, ''))
        self.assertIn('Records imported with a correction: 1', log.message)
        self.assertIn('are an EDRPOU code', log.message)

    def test_an_ipn_of_the_wrong_length_is_left_out_and_named(self):
        log = self._import([{'external_ref': 'ATM-UA-9', 'name': 'ТОВ «Дев\'ять»', 'ua_code': CODE,
                             'ua_ipn': '123456789'}])
        self.assertEqual((log.created_count, log.failed_count), (1, 0), log.message)
        self.assertEqual(self._partner('ATM-UA-9')._l10n_ua_tax_codes(), (CODE, ''))
        self.assertIn('Record 1 (ATM-UA-9): the VAT payer IPN "123456789" is not 12 or 10 digits', log.message)
        self.assertIn('What to do: correct these numbers in the source system', log.message)

    def test_a_code_of_the_wrong_length_is_left_out_and_named(self):
        log = self._import([{'external_ref': 'ATM-UA-C', 'name': 'ТОВ «Код»', 'ua_code': '1234567', 'ua_ipn': IPN}])
        self.assertEqual((log.created_count, log.failed_count), (1, 0), log.message)
        self.assertEqual(self._partner('ATM-UA-C')._l10n_ua_tax_codes(), ('', IPN))
        self.assertIn('the EDRPOU / RNOKPP code "1234567" is not 8 or 10 digits', log.message)

    def test_the_code_repeated_in_the_ipn_field_needs_no_note(self):
        log = self._import([{'external_ref': 'ATM-UA-R', 'name': 'ТОВ «Повтор»', 'ua_code': CODE, 'ua_ipn': CODE}])
        self.assertEqual((log.created_count, log.failed_count), (1, 0), log.message)
        self.assertEqual(self._partner('ATM-UA-R')._l10n_ua_tax_codes(), (CODE, ''))
        self.assertNotIn('correction', log.message)

# -*- coding: utf-8 -*-
"""Settings screen: exchange directory, date filter and entity switches."""
import logging
import os

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .atm_error_report import DEFAULT_URL, PARAM_CONSENT, PARAM_URL
from .atm_exchange import ATM_TRUE
from .atm_update import (DEFAULT_URL as UPDATE_DEFAULT_URL, PARAM_CHECKED,
                         PARAM_UPDATE_CHECK, PARAM_URL as UPDATE_PARAM_URL,
                         parse_version)
from .entities import ENTITIES

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    atm_export_dir = fields.Char(
        string='Exchange Directory',
        config_parameter='atm.export_dir',
        help='Directory the JSON files are written to and read from. '
             'It must be reachable by the Odoo server process.',
    )
    # Deliberately not a ``config_parameter`` field: res.config.settings only
    # accepts boolean, integer, float, char, selection, many2one and datetime
    # there, and a Date makes the whole settings screen fail to open. The value
    # is read and written by hand below instead.
    atm_date_from = fields.Date(
        string='Exchange Documents Since',
        help='Documents dated before this day are never exported. '
             'Leave empty to export the whole history.',
    )
    atm_auto_confirm = fields.Boolean(
        string='Confirm Imported Documents',
        config_parameter='atm.auto_confirm',
        help='Imported documents are always created as drafts. Enable this to '
             'confirm orders and post invoices and payments that were already '
             'confirmed or posted in the external system.',
    )
    atm_system_code = fields.Char(
        string='System Code',
        config_parameter='atm.system_code',
        default='odoo',
        help='Short identifier of this database. It prefixes the external '
             'references generated for records that do not have one yet.',
    )

    # One switch per registered entity. These are not ``config_parameter``
    # fields either: Odoo deletes the parameter when a boolean is saved as
    # False, so "switched off by the user" and "never configured" would look
    # exactly the same, and a disabled entity would come back on. The value is
    # written explicitly as 'True' / 'False' below.
    atm_entity_partner = fields.Boolean(string='Contacts', default=True)
    atm_entity_product = fields.Boolean(string='Products', default=True)
    atm_entity_sale_order = fields.Boolean(string='Sales Orders', default=True)
    atm_entity_purchase_order = fields.Boolean(
        string='Purchase Orders', default=True)
    atm_entity_customer_invoice = fields.Boolean(
        string='Customer Invoices', default=True)
    atm_entity_vendor_bill = fields.Boolean(
        string='Vendor Bills', default=True)
    atm_entity_customer_refund = fields.Boolean(
        string='Customer Credit Notes', default=True)
    atm_entity_vendor_refund = fields.Boolean(
        string='Vendor Credit Notes', default=True)
    atm_entity_customer_payment = fields.Boolean(
        string='Customer Payments', default=True)
    atm_entity_vendor_payment = fields.Boolean(
        string='Vendor Payments', default=True)

    # Three states on purpose, not a boolean: "never asked" has to count as
    # "no", and a boolean cannot tell it from a deliberate "off". Nothing is
    # ever sent until someone explicitly chooses "on".
    atm_error_reports = fields.Selection(
        [('on', 'Send automatic error reports'),
         ('off', 'Do not send error reports')],
        string='Error Reports',
        config_parameter=PARAM_CONSENT,
        help='Off unless you turn it on. When on, unexpected failures are '
             'queued as the exception class and the line of code that failed '
             '-- never the error text, which is where names and amounts live. '
             'Every queued report can be read in full before it is sent.')
    atm_report_url = fields.Char(
        string='Reporting Endpoint',
        config_parameter=PARAM_URL,
        default=DEFAULT_URL,
        help='Where error reports are sent. Point it at your own collector if '
             'your policy forbids outbound calls.')

    # On unless switched off -- the opposite default to error reports above,
    # and deliberately so: this request carries no identifier of any kind, so
    # there is nothing to consent to, and a check nobody knows about would
    # never be switched on. See atm_update.py.
    atm_update_check = fields.Selection(
        [('on', 'Check for new versions once a day'),
         ('off', 'Never check')],
        string='Version Check',
        config_parameter=PARAM_UPDATE_CHECK,
        default='on',
        help='Odoo never asks the store whether a third-party module has been '
             'updated, so without this a fixed bug would stay in place until '
             'you happened to revisit the store page.')
    atm_update_url = fields.Char(
        string='Version Endpoint',
        config_parameter=UPDATE_PARAM_URL,
        default=UPDATE_DEFAULT_URL,
        help='Where the current version number is read from.')
    atm_version_installed = fields.Char('Installed Version', readonly=True)
    atm_version_latest = fields.Char('Latest Version', readonly=True)
    atm_version_checked = fields.Char('Last Checked', readonly=True)
    atm_update_available = fields.Boolean('Update Available', readonly=True)
    # Built as one sentence rather than assembled in the view: text interleaved
    # with fields reaches the translator as fragments, and a fragment cannot be
    # turned into a Ukrainian sentence -- the word order is not the same.
    atm_update_summary = fields.Char('Version Status', readonly=True)

    @api.model
    def get_values(self):
        res = super().get_values()
        param = self.env['ir.config_parameter'].sudo()
        res['atm_date_from'] = param.get_param('atm.date_from') or False
        for spec in ENTITIES:
            res['atm_entity_%s' % spec.code] = param.get_param(
                spec.setting_param, 'True') in ATM_TRUE
        res.update(self._atm_version_values())
        return res

    def _atm_version_values(self):
        """What the Updates block shows. Never raises: it renders a page."""
        param = self.env['ir.config_parameter'].sudo()
        module = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'atm')], limit=1)
        installed = module.installed_version or ''
        published = self.env['atm.update']._published()
        latest = published.get('atm') or ''
        available = bool(latest
                         and parse_version(latest) > parse_version(installed))
        checked = param.get_param(PARAM_CHECKED, '')

        if available:
            summary = _('Version %(latest)s is available. You have '
                        '%(installed)s.', latest=latest, installed=installed)
        elif latest:
            summary = _('You have version %(installed)s, which is the latest.',
                        installed=installed)
        else:
            # Not "up to date": with no answer, saying so would be a guess
            # dressed as a fact -- and the one thing this feature exists to
            # prevent is a customer who believes they are current.
            summary = _('You have version %(installed)s. The latest published '
                        'version is not known yet.', installed=installed)

        return {
            'atm_version_installed': installed,
            'atm_version_latest': latest,
            'atm_version_checked': checked,
            'atm_update_available': available,
            'atm_update_summary': summary,
        }

    def action_atm_check_update(self):
        """Check on demand and say what happened -- including why it failed.

        The daily job swallows failures on purpose, but a person who pressed a
        button and saw the page reload unchanged cannot tell "you are up to
        date" from "the request never left the building".
        """
        self.ensure_one()
        ok, reason = self.env['atm.update']._run_check()
        if not ok:
            message, kind = reason, 'warning'
        else:
            outdated = self.env['atm.update']._outdated()
            if outdated:
                name, installed, latest = outdated[0]
                message = _('A newer version of %(module)s is available: '
                            '%(latest)s (you have %(installed)s).',
                            module=name, latest=latest, installed=installed)
                kind = 'warning'
            else:
                message = _('You are up to date.')
                kind = 'success'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Version check'),
                'message': message,
                'type': kind,
                'sticky': kind == 'warning',
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def set_values(self):
        super().set_values()
        param = self.env['ir.config_parameter'].sudo()
        param.set_param('atm.date_from', self.atm_date_from or '')
        for spec in ENTITIES:
            param.set_param(
                spec.setting_param,
                'True' if self['atm_entity_%s' % spec.code] else 'False')

    def action_atm_export_now(self):
        """Run a full export immediately and report what happened."""
        self.ensure_one()
        logs = self.env['atm.exchange'].export_all()
        return self._atm_notify(logs, _('Export finished'))

    def action_atm_import_now(self):
        """Run a full import immediately and report what happened."""
        self.ensure_one()
        logs = self.env['atm.exchange'].import_all()
        return self._atm_notify(logs, _('Import finished'))

    def action_atm_open_logs(self):
        self.ensure_one()
        return self.env['ir.actions.act_window']._for_xml_id(
            'atm.action_atm_exchange_log')

    def action_atm_open_error_reports(self):
        self.ensure_one()
        return self.env['ir.actions.act_window']._for_xml_id(
            'atm.action_atm_error_report')

    def _atm_notify(self, logs, title):
        if not logs:
            raise UserError(_('No entity is enabled for exchange.'))
        failed = logs.filtered(lambda log: log.state == 'failed')
        message = _('%(total)s entity(ies) processed, %(failed)s failed.') % {
            'total': len(logs), 'failed': len(failed)}
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': 'danger' if failed else 'success',
                'sticky': bool(failed),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    @api.onchange('atm_export_dir')
    def _onchange_atm_export_dir(self):
        """Warn early: a wrong path only fails at the first cron run."""
        if self.atm_export_dir and not os.path.isdir(self.atm_export_dir):
            return {'warning': {
                'title': _('Directory not found'),
                'message': _('%s does not exist yet. It will be created on '
                             'the first export if the server may write there.')
                           % self.atm_export_dir,
            }}

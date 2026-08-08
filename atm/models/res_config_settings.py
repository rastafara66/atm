# -*- coding: utf-8 -*-
"""Settings screen: exchange directory, date filter and entity switches."""
import logging
import os

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    atm_export_dir = fields.Char(
        string='Exchange Directory',
        config_parameter='atm.export_dir',
        help='Directory the JSON files are written to and read from. '
             'It must be reachable by the Odoo server process.',
    )
    atm_date_from = fields.Date(
        string='Exchange Documents Since',
        config_parameter='atm.date_from',
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

    # One switch per registered entity. The config parameter names must stay
    # in sync with ``EntitySpec.setting_param``.
    atm_entity_partner = fields.Boolean(
        string='Contacts', default=True,
        config_parameter='atm.entity_partner')
    atm_entity_product = fields.Boolean(
        string='Products', default=True,
        config_parameter='atm.entity_product')
    atm_entity_sale_order = fields.Boolean(
        string='Sales Orders', default=True,
        config_parameter='atm.entity_sale_order')
    atm_entity_purchase_order = fields.Boolean(
        string='Purchase Orders', default=True,
        config_parameter='atm.entity_purchase_order')
    atm_entity_customer_invoice = fields.Boolean(
        string='Customer Invoices', default=True,
        config_parameter='atm.entity_customer_invoice')
    atm_entity_vendor_bill = fields.Boolean(
        string='Vendor Bills', default=True,
        config_parameter='atm.entity_vendor_bill')
    atm_entity_customer_refund = fields.Boolean(
        string='Customer Credit Notes', default=True,
        config_parameter='atm.entity_customer_refund')
    atm_entity_vendor_refund = fields.Boolean(
        string='Vendor Credit Notes', default=True,
        config_parameter='atm.entity_vendor_refund')
    atm_entity_customer_payment = fields.Boolean(
        string='Customer Payments', default=True,
        config_parameter='atm.entity_customer_payment')
    atm_entity_vendor_payment = fields.Boolean(
        string='Vendor Payments', default=True,
        config_parameter='atm.entity_vendor_payment')

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

# -*- coding: utf-8 -*-
"""Journal of every export and import run, so results are auditable."""
from odoo import _, fields, models

from .entities import ENTITIES


class AtmExchangeLog(models.Model):
    _name = 'atm.exchange.log'
    _description = 'Data Exchange Log'
    _order = 'create_date desc, id desc'

    direction = fields.Selection(
        [('export', 'Export'), ('import', 'Import')],
        string='Direction', required=True, readonly=True)
    entity = fields.Selection(
        selection=[(spec.code, spec.label) for spec in ENTITIES],
        string='Entity', required=True, readonly=True)
    state = fields.Selection(
        [('running', 'Running'), ('done', 'Done'), ('failed', 'Failed')],
        string='Status', default='running', readonly=True)
    file_path = fields.Char(string='File', readonly=True)
    record_count = fields.Integer(string='Records', readonly=True)
    created_count = fields.Integer(string='Created', readonly=True)
    updated_count = fields.Integer(string='Updated', readonly=True)
    skipped_count = fields.Integer(string='Skipped', readonly=True)
    failed_count = fields.Integer(string='Failed', readonly=True)
    message = fields.Text(string='Message', readonly=True)

    def _compute_display_name(self):
        directions = dict(self._fields['direction'].selection)
        entities = dict(self._fields['entity'].selection)
        for log in self:
            log.display_name = '%s: %s' % (
                directions.get(log.direction, ''),
                entities.get(log.entity, ''),
            )

    def action_open_file(self):
        """Show the path of the produced file, for a quick sanity check."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Exchange file'),
                'message': self.file_path or _('No file'),
                'sticky': False,
            },
        }

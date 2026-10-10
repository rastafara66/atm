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
        string='Direction', required=True, readonly=True,
        help='Export: records were written from this database to a file. '
             'Import: records were read from a file into this database.')
    entity = fields.Selection(
        selection=[(spec.code, spec.label) for spec in ENTITIES],
        string='Entity', required=True, readonly=True,
        help='What was exchanged in this run. Each entity has its own file '
             'and its own switch in Settings > Data Exchange.')
    state = fields.Selection(
        [('running', 'Running'), ('done', 'Done'), ('failed', 'Failed')],
        string='Status', default='running', readonly=True,
        help='Running: the run has not finished yet. Done: the file was '
             'processed; some records may still have failed, see Failures. '
             'Failed: the run stopped, or not a single record could be '
             'written; Message gives the reasons.')
    file_path = fields.Char(
        string='File', readonly=True,
        help='Full path of the file written or read, on the Odoo server.')
    record_count = fields.Integer(
        string='Records', readonly=True,
        help='How many records the file held (import) or received (export), '
             'whatever happened to each of them.')
    created_count = fields.Integer(
        string='Created', readonly=True,
        help='Records that were new to this database and were created.')
    updated_count = fields.Integer(
        string='Updated', readonly=True,
        help='Records found by their external reference and updated.')
    skipped_count = fields.Integer(
        string='Skipped', readonly=True,
        help='Records left untouched on purpose -- for example, a document '
             'that is already confirmed or posted here is never overwritten.')
    # 'Failures', not 'Failed': this counts records, while state uses 'Failed'
    # for the run itself. One word in English, two in most other languages --
    # keeping the source strings apart lets both translate correctly.
    failed_count = fields.Integer(
        string='Failures', readonly=True,
        help='Records that could not be written. Message names each of them '
             'and the reason; fix the data and run the exchange again.')
    message = fields.Text(
        string='Message', readonly=True,
        help='What happened in this run: every failed record with its reason '
             'and what to do about it.')

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

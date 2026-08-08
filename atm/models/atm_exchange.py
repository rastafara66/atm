# -*- coding: utf-8 -*-
"""Exchange engine: reads and writes JSON files for the registered entities.

The engine is deliberately file based. Odoo drops the files into a directory
and picks them up from the same place, so any external system able to read and
write JSON on a shared folder can be connected without opening a network port.
"""
import json
import logging
import os
from datetime import date, datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .entities import ENTITIES, ENTITIES_BY_CODE

_logger = logging.getLogger(__name__)

#: Bumped when the on-disk JSON layout changes in a backwards incompatible way.
FILE_FORMAT_VERSION = '1.0'


class AtmJSONEncoder(json.JSONEncoder):
    """Serialise dates the way the importer expects to read them back."""

    def default(self, o):
        if isinstance(o, datetime):
            return o.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(o, date):
            return o.strftime('%Y-%m-%d')
        return super().default(o)


class AtmExchange(models.AbstractModel):
    _name = 'atm.exchange'
    _description = 'ATM Exchange Engine'

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    @api.model
    def _get_param(self, key, default=None):
        value = self.env['ir.config_parameter'].sudo().get_param(key)
        return value if value not in (None, False, '') else default

    @api.model
    def _get_exchange_dir(self, create=False):
        """Return the configured exchange directory, or raise if unusable."""
        path = self._get_param('atm.export_dir')
        if not path:
            raise UserError(_(
                'The exchange directory is not configured. '
                'Set it in Settings > ATM.'))
        if not os.path.isdir(path):
            if not create:
                raise UserError(_('Exchange directory does not exist: %s')
                                % path)
            os.makedirs(path, exist_ok=True)
        return path

    @api.model
    def _get_enabled_entities(self):
        """Return the specs the user switched on, in registry order."""
        return [spec for spec in ENTITIES
                if self._get_param(spec.setting_param, 'True') in
                ('True', 'true', '1', True)]

    @api.model
    def _get_date_from(self):
        """Lower bound for time-filtered entities, or ``False`` for no bound."""
        value = self._get_param('atm.date_from')
        if not value:
            return False
        try:
            return fields.Date.to_date(value)
        except (ValueError, TypeError):
            _logger.warning('Invalid atm.date_from parameter: %s', value)
            return False

    # ------------------------------------------------------------------
    # External reference handling
    # ------------------------------------------------------------------
    @api.model
    def _system_prefix(self):
        """Short, stable identifier of this database, used in generated refs."""
        return self._get_param('atm.system_code', 'odoo')

    @api.model
    def _ensure_external_ref(self, record):
        """Return the record's external reference, assigning one if missing.

        The reference is persisted so that the same record keeps the same key
        across exports, which is what makes repeated imports idempotent on the
        other side.
        """
        ref = record.atm_external_ref
        if ref:
            return ref
        ref = '%s/%s/%s' % (self._system_prefix(), record._name, record.id)
        record.sudo().write({'atm_external_ref': ref})
        return ref

    @api.model
    def _export_m2o(self, record, field_name, entity_code):
        """Serialise a many2one as a resolvable descriptor, not as an id."""
        target = record[field_name]
        if not target:
            return False
        if entity_code and 'atm_external_ref' in target._fields:
            return {
                'external_ref': self._ensure_external_ref(target),
                'name': target.display_name,
            }
        # Reference data (countries, units, journals, accounts): matched by the
        # values that are stable across databases.
        descriptor = {'name': target.display_name}
        for key in ('code', 'login'):
            if key in target._fields:
                descriptor[key] = target[key]
        xmlid = target.get_external_id().get(target.id)
        if xmlid:
            descriptor['xmlid'] = xmlid
        return descriptor

    @api.model
    def _resolve_m2o(self, model_name, descriptor, entity_code):
        """Find the local record a serialised many2one descriptor points at."""
        if not descriptor:
            return False
        model = self.env[model_name]
        if isinstance(descriptor, str):
            descriptor = {'name': descriptor}

        external_ref = descriptor.get('external_ref')
        if external_ref and 'atm_external_ref' in model._fields:
            found = model.search(
                [('atm_external_ref', '=', external_ref)], limit=1)
            if found:
                return found.id

        xmlid = descriptor.get('xmlid')
        if xmlid:
            found = self.env.ref(xmlid, raise_if_not_found=False)
            if found and found._name == model_name:
                return found.id

        code = descriptor.get('code')
        if code and 'code' in model._fields:
            found = model.search([('code', '=', code)], limit=1)
            if found:
                return found.id

        name = descriptor.get('name')
        if name:
            found = model.search([('name', '=', name)], limit=1)
            if found:
                return found.id
            # Records whose display_name differs from ``name`` (partners with a
            # parent, products with variants) still match on display name.
            found = model.name_search(name, limit=1)
            if found:
                return found[0][0]

        if entity_code:
            _logger.debug('Unresolved %s reference: %s', model_name, descriptor)
        return False

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    @api.model
    def _export_domain(self, spec):
        domain = list(spec.domain)
        date_from = self._get_date_from()
        if date_from and spec.date_field:
            domain.append((spec.date_field, '>=', fields.Date.to_string(date_from)))
        return domain

    #: Line ``display_type`` values that only shape the printed document.
    #: Everything else -- including ``product``, the value carried by ordinary
    #: invoice lines -- is real content and must be exchanged.
    LAYOUT_DISPLAY_TYPES = ('line_section', 'line_subsection', 'line_note')

    @api.model
    def _is_layout_line(self, line):
        """True for section, subsection and note lines."""
        display_type = 'display_type' in line._fields and line.display_type
        return display_type in self.LAYOUT_DISPLAY_TYPES

    @api.model
    def _export_record(self, spec, record):
        """Turn one record into its JSON representation."""
        data = {'external_ref': self._ensure_external_ref(record)}
        for key, field_name in spec.fields.items():
            data[key] = record[field_name]
        for key, (field_name, entity_code) in spec.m2o_fields.items():
            data[key] = self._export_m2o(record, field_name, entity_code)

        if spec.line_field:
            lines = []
            for line in record[spec.line_field]:
                if self._is_layout_line(line):
                    continue
                line_data = {}
                for key, field_name in spec.line_fields.items():
                    line_data[key] = line[field_name]
                for key, (field_name, entity_code) in spec.line_m2o_fields.items():
                    line_data[key] = self._export_m2o(line, field_name, entity_code)
                lines.append(line_data)
            data['lines'] = lines
        return data

    @api.model
    def export_entity(self, code):
        """Export one entity to its JSON file. Returns the log record."""
        spec = ENTITIES_BY_CODE[code]
        log = self.env['atm.exchange.log'].create({
            'direction': 'export',
            'entity': code,
            'state': 'running',
        })
        try:
            path = self._get_exchange_dir(create=True)
            file_path = os.path.join(path, spec.filename)
            records = self.env[spec.model].search(self._export_domain(spec))
            payload = {
                'atm_format': FILE_FORMAT_VERSION,
                'entity': code,
                'model': spec.model,
                'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
                'source': {
                    'system': 'odoo',
                    'database': self.env.cr.dbname,
                    'company': self.env.company.name,
                },
                'records': [self._export_record(spec, rec) for rec in records],
            }
            with open(file_path, 'w', encoding='utf-8') as fh:
                json.dump(payload, fh, cls=AtmJSONEncoder, indent=2,
                          ensure_ascii=False)
            log.write({
                'state': 'done',
                'file_path': file_path,
                'record_count': len(records),
                'message': _('%s record(s) written.') % len(records),
            })
            _logger.info('ATM exported %s record(s) of %s to %s',
                         len(records), code, file_path)
        except Exception as error:  # noqa: BLE001 - reported through the log
            log.write({'state': 'failed', 'message': str(error)})
            _logger.exception('ATM export of %s failed', code)
        return log

    @api.model
    def export_all(self):
        """Export every enabled entity. Entry point of the export cron."""
        logs = self.env['atm.exchange.log']
        for spec in self._get_enabled_entities():
            logs |= self.export_entity(spec.code)
        return logs

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------
    @api.model
    def _prepare_values(self, spec, data):
        """Build the ``create``/``write`` values of one incoming record."""
        values = dict(spec.defaults)
        model = self.env[spec.model]
        for key, field_name in spec.fields.items():
            if key not in data:
                continue
            if field_name not in model._fields:
                continue
            if field_name == 'state':
                # Documents are always created as drafts: Odoo refuses to
                # create an already posted move, and confirming an order has
                # side effects that must go through its own business method.
                # ``_apply_target_state`` replays the state afterwards.
                continue
            if model._fields[field_name].readonly:
                # Document totals are derived from the lines. Being computed
                # is not the criterion -- quantities and unit prices are
                # computed too, yet perfectly writable.
                continue
            values[field_name] = data[key]
        for key, (field_name, entity_code) in spec.m2o_fields.items():
            if key not in data or field_name not in model._fields:
                continue
            comodel = model._fields[field_name].comodel_name
            resolved = self._resolve_m2o(comodel, data[key], entity_code)
            if resolved:
                values[field_name] = resolved
        return self._postprocess_values(spec, data, values)

    #: Models whose ``name`` is a legal sequence number owned by this database.
    #: Importing a foreign number would collide with the local sequence, so the
    #: source number is kept in a reference field instead.
    SEQUENCE_OWNED_MODELS = {
        'account.move': 'ref',
        'account.payment': 'memo',
    }

    @api.model
    def _postprocess_values(self, spec, data, values):
        """Adjust values that cannot be written as they came from the file."""
        reference_field = self.SEQUENCE_OWNED_MODELS.get(spec.model)
        if reference_field and reference_field in self.env[spec.model]._fields:
            values.pop('name', None)
            if not values.get(reference_field) and data.get('name'):
                values[reference_field] = data['name']
        return values

    @api.model
    def _prepare_line_values(self, spec, data):
        """Build the one2many commands for the lines of one document."""
        if not spec.line_field:
            return []
        model = self.env[spec.model]
        line_model = self.env[model._fields[spec.line_field].comodel_name]
        commands = [(5, 0, 0)]
        for line_data in data.get('lines') or []:
            values = {}
            for key, field_name in spec.line_fields.items():
                if key in line_data and field_name in line_model._fields:
                    if line_model._fields[field_name].readonly:
                        continue
                    values[field_name] = line_data[key]
            for key, (field_name, entity_code) in spec.line_m2o_fields.items():
                if key not in line_data or field_name not in line_model._fields:
                    continue
                comodel = line_model._fields[field_name].comodel_name
                resolved = self._resolve_m2o(comodel, line_data[key], entity_code)
                if resolved:
                    values[field_name] = resolved
            commands.append((0, 0, values))
        return commands

    @api.model
    def import_entity(self, code):
        """Import one entity from its JSON file. Returns the log record."""
        spec = ENTITIES_BY_CODE[code]
        log = self.env['atm.exchange.log'].create({
            'direction': 'import',
            'entity': code,
            'state': 'running',
        })
        created = updated = skipped = failed = 0
        try:
            path = self._get_exchange_dir()
            file_path = os.path.join(path, spec.filename)
            log.file_path = file_path
            if not os.path.isfile(file_path):
                log.write({
                    'state': 'done',
                    'message': _('No file to import: %s') % file_path,
                })
                return log

            with open(file_path, 'r', encoding='utf-8') as fh:
                payload = json.load(fh)
            # Files written by an older ATM had no envelope, just a list.
            records = payload.get('records', []) if isinstance(payload, dict) \
                else payload

            model = self.env[spec.model]
            for data in records:
                external_ref = data.get('external_ref') or data.get('name')
                if not external_ref:
                    failed += 1
                    continue
                try:
                    # A savepoint per record: a database level error (a
                    # duplicate document number, a failed constraint) aborts
                    # the whole transaction otherwise, and the rest of the
                    # file would be lost with it.
                    with self.env.cr.savepoint():
                        existing = model.search(
                            [('atm_external_ref', '=', external_ref)], limit=1)
                        values = self._prepare_values(spec, data)
                        values['atm_external_ref'] = external_ref
                        lines = self._prepare_line_values(spec, data)

                        if existing:
                            if not self._is_updatable(existing):
                                skipped += 1
                                continue
                            if lines:
                                values[spec.line_field] = lines
                            existing.write(values)
                            self._apply_target_state(existing, data)
                            updated += 1
                        else:
                            if lines:
                                values[spec.line_field] = lines
                            record = model.create(values)
                            self._apply_target_state(record, data)
                            created += 1
                except Exception as error:  # noqa: BLE001 - counted, not fatal
                    failed += 1
                    _logger.warning('ATM could not import %s %s: %s',
                                    code, external_ref, error)

            log.write({
                'state': 'failed' if failed and not (created or updated) else 'done',
                'record_count': created + updated,
                'created_count': created,
                'updated_count': updated,
                'skipped_count': skipped,
                'failed_count': failed,
                'message': _('%(created)s created, %(updated)s updated, '
                             '%(skipped)s skipped, %(failed)s failed.') % {
                    'created': created, 'updated': updated,
                    'skipped': skipped, 'failed': failed},
            })
            _logger.info('ATM imported %s: %s created, %s updated, %s skipped, '
                         '%s failed', code, created, updated, skipped, failed)
        except Exception as error:  # noqa: BLE001 - reported through the log
            log.write({'state': 'failed', 'message': str(error)})
            _logger.exception('ATM import of %s failed', code)
        return log

    #: Business method that moves a freshly imported record to the state it
    #: had in the source system, per model and per incoming state.
    CONFIRM_METHODS = {
        'sale.order': ({'sale', 'done'}, 'action_confirm'),
        'purchase.order': ({'purchase', 'done'}, 'button_confirm'),
        'account.move': ({'posted'}, 'action_post'),
        'account.payment': ({'posted', 'in_process', 'paid'}, 'action_post'),
    }

    @api.model
    def _apply_target_state(self, record, data):
        """Confirm or post an imported document, if the user asked for it.

        Off by default: posting is an accounting act, and an administrator
        should decide whether an external system may perform it.
        """
        if self._get_param('atm.auto_confirm', 'False') not in \
                ('True', 'true', '1', True):
            return False
        rule = self.CONFIRM_METHODS.get(record._name)
        if not rule:
            return False
        target_states, method_name = rule
        if data.get('state') not in target_states:
            return False
        if record.state not in ('draft', 'sent'):
            return False
        getattr(record, method_name)()
        return True

    @api.model
    def _is_updatable(self, record):
        """Never rewrite a record the accounting already relies on."""
        state = record._fields.get('state') and record.state
        if record._name in ('account.move', 'account.payment'):
            return state == 'draft'
        if record._name in ('sale.order', 'purchase.order'):
            return state in ('draft', 'sent')
        return True

    @api.model
    def import_all(self):
        """Import every enabled entity. Entry point of the import cron."""
        logs = self.env['atm.exchange.log']
        for spec in self._get_enabled_entities():
            logs |= self.import_entity(spec.code)
        return logs

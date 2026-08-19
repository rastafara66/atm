# -*- coding: utf-8 -*-
"""Automatic crash reports, built so they cannot carry business data.

The author cannot fix what he never hears about, and a company whose exchange
breaks almost never writes in -- they switch the crons off and go back to doing
it by hand. So unexpected failures report themselves.

The whole design follows from one constraint: this module handles contacts,
products, orders, invoices and payments, so an exception message here plausibly
contains a customer name, a document number or a sum. Scrubbing such a message
with regular expressions is a losing game -- a name is not a pattern.

So the message is never sent. What crosses the network is only:

* the exception *class* (``KeyError``), never its text;
* the *locations* in the traceback -- file and line, with paths cut back to the
  module root so a developer's home directory does not travel either;
* versions and an HTTP status code if there was one;
* whatever the user chose to type into the comment box.

You cannot leak a customer name through a field that only ever holds
``"KeyError"`` and ``"atm/models/atm_exchange.py:88"``. That is the point:
safety here is structural, not a filter someone has to keep ahead of.

What is DIFFERENT here from a module that talks to the user all day: this one
runs unattended, and it already catches its own failures -- every exception is
written to the exchange log and the run carries on. So there is no exception
escaping to be wrapped; the reporter is called from inside those handlers
instead. And the failures that are *expected* there -- a document referring to
a product this database never received -- are raised as :class:`AtmDataError`
and never reported, or the queue would fill with the other side's data problems
until a real defect could no longer be seen in it.

Reports are queued and sent by a scheduled action, never inline -- a failed
exchange must not turn into a hung run because the reporting endpoint is down.
"""

import hashlib
import json
import logging
import sys
import traceback
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import (
    AccessError,
    MissingError,
    RedirectWarning,
    UserError,
    ValidationError,
)

from .atm_exceptions import AtmDataError

_logger = logging.getLogger(__name__)

# Where reports go. Overridable per database, so a company with a policy
# against outbound calls can point it at their own collector.
#
# The receiver whitelists exactly the fields sent here and tells modules apart
# by ``module``, so this module shares the endpoint the author's other modules
# already use rather than needing one of its own.
PARAM_URL = 'atm.report_url'
PARAM_CONSENT = 'atm.error_reports'
PARAM_INSTALL_ID = 'atm.install_id'
DEFAULT_URL = 'https://yellow.in.ua/odoo-report'

# The report format, so an old client and a new collector can still talk.
SCHEMA = 1

# One database cannot flood the collector: a fingerprint already reported is
# only counted, not resent, and there is a hard ceiling per day.
MAX_PER_DAY = 20
MAX_ATTEMPTS = 5
SEND_TIMEOUT = 10

# How many traceback frames to keep. The top of the stack is the generic Odoo
# machinery and says nothing; the last frames are where the bug is.
KEEP_FRAMES = 12

# These are not bugs. The first five are the module talking to the user; the
# last is the other system sending something this database cannot resolve.
# Both carry the very data we refuse to send, and both would arrive in numbers
# a real defect could not be seen through. Never report them.
EXPECTED_EXCEPTIONS = (
    UserError,
    ValidationError,
    AccessError,
    MissingError,
    RedirectWarning,
    AtmDataError,
)


def _short_path(path):
    """Cut an absolute path back to something that identifies code, not a person.

    ``C:\\Users\\ivan\\odoo\\addons\\atm\\models\\atm_exchange.py`` becomes
    ``atm/models/atm_exchange.py``. For third-party frames there is no module
    root to anchor on, so keep the last two segments -- enough to recognise
    ``requests/adapters.py``, not enough to say whose machine it is.
    """
    parts = path.replace('\\', '/').split('/')
    for index, part in enumerate(parts):
        if part == 'atm' or part.startswith('atm_'):
            return '/'.join(parts[index:])
    return '/'.join(parts[-2:])


def _http_status(exception):
    """Pull a status code out of whatever was raised, if there is one.

    A status code is a three-digit number with no business data in it, and it
    separates "the server said no" from "our code is wrong" faster than
    anything else in the report.
    """
    response = getattr(exception, 'response', None)
    status = getattr(response, 'status_code', None)
    return status if isinstance(status, int) else 0


class AtmErrorReport(models.Model):
    """One queued crash report, kept visible so nothing is sent behind the user."""

    _name = 'atm.error.report'
    _description = 'Data Exchange Error Report'
    _order = 'create_date desc, id desc'
    _rec_name = 'error_type'

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    fingerprint = fields.Char(
        required=True,
        index=True,
        help='Identifies the same bug across occurrences, so it is reported once.')
    error_type = fields.Char(
        required=True, help='The exception class, never its text.')
    operation = fields.Char(
        help='What the module was doing: the exchange direction and entity.')
    module = fields.Char(
        default='atm',
        required=True,
        index=True,
        help='Which module raised it, so the collector tells reports apart.')
    http_status = fields.Integer()
    frames = fields.Text(
        help='Where in the code it failed. Paths are cut to the module root.')
    occurrences = fields.Integer(default=1)
    comment = fields.Text(
        string='Your comment',
        help='Optional. Anything typed here is sent as written -- do not paste '
             'customer names, document numbers or amounts.')
    state = fields.Selection(
        [('pending', 'To send'), ('sent', 'Sent'), ('failed', 'Could not send')],
        default='pending',
        required=True,
        index=True)
    attempts = fields.Integer(default=0)
    sent_date = fields.Datetime(readonly=True)
    payload = fields.Text(
        compute='_compute_payload',
        help='Exactly what leaves this database. Nothing else is transmitted.')

    # Declared the old way on purpose. ``models.Constraint`` exists only in
    # 19.0, while this form works in every series the module supports -- and
    # one definition across all four branches is worth more here than the
    # newer spelling: version drift between copies is exactly what has bitten
    # this module before.
    _sql_constraints = [
        ('fingerprint_company_uniq',
         'UNIQUE(fingerprint, company_id)',
         'The same failure is only queued once per company.'),
    ]

    @api.depends('fingerprint', 'error_type', 'operation', 'http_status',
                 'frames', 'occurrences', 'comment')
    def _compute_payload(self):
        """Render the outgoing JSON for the user to read before it is sent.

        This is the whole transparency story: the field on the form *is* the
        request body, not a summary of it, so "what do you send about me?" has
        a literal answer.
        """
        for report in self:
            report.payload = json.dumps(
                report._payload(), indent=2, ensure_ascii=False)

    def _payload(self):
        self.ensure_one()
        return {
            'schema': SCHEMA,
            'install_id': self.env['ir.config_parameter'].sudo().get_param(
                PARAM_INSTALL_ID, ''),
            'odoo_version': self._odoo_version(),
            'module': self.module or 'atm',
            'module_version': self._module_version(),
            'operation': self.operation or '',
            'error_type': self.error_type,
            'http_status': self.http_status,
            'fingerprint': self.fingerprint,
            'occurrences': self.occurrences,
            'frames': (self.frames or '').splitlines(),
            'comment': self.comment or '',
        }

    @api.model
    def _odoo_version(self):
        from odoo.release import version

        return version

    def _module_version(self):
        module = self.env['ir.module.module'].sudo().search(
            [('name', '=', self.module or 'atm')], limit=1)
        return module.installed_version or ''

    # ------------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------------
    @api.model
    def _capture(self, operation, module='atm'):
        """Queue a report for the exception currently being handled.

        Called from inside an ``except`` block, so ``sys.exc_info()`` is the
        failure we want. Returns silently when there is no live exception,
        because the caller should not have to care.

        Runs in its own cursor: the caller is on the failure path and may be
        rolled back, and a report that vanishes with the rollback would only
        ever be queued for errors that did not matter.
        """
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_value is None:
            return False
        if isinstance(exc_value, EXPECTED_EXCEPTIONS):
            return False
        if not self._reporting_enabled():
            return False

        company = self.env.company
        vals = self._build_vals(
            exc_type, exc_value, exc_tb, operation, company, module)
        try:
            with self.env.registry.cursor() as cr:
                cr.execute("SET LOCAL lock_timeout = '5s'")
                env = api.Environment(cr, self.env.uid, {})
                # Mint the install id here, not at send time. The form promises
                # that what it shows *is* the request body, and a queued report
                # rendered before the first send would otherwise display an
                # empty id and then travel with a filled one.
                env[self._name]._install_id()
                existing = env[self._name].sudo().search(
                    [('fingerprint', '=', vals['fingerprint']),
                     ('company_id', '=', company.id)],
                    limit=1)
                if existing:
                    # Same bug again: count it rather than queue it twice. The
                    # count is itself the useful signal -- "once" and "400 times
                    # a day" are different bugs to the person fixing them.
                    existing.occurrences += 1
                    return existing.id
                return env[self._name].sudo().create(vals).id
        except Exception:  # noqa: BLE001 - reporting must never mask the real error
            _logger.exception('Could not queue a Data Exchange error report')
            return False

    @api.model
    def _build_vals(self, exc_type, exc_value, exc_tb, operation, company,
                    module='atm'):
        frames = [
            '%s:%s in %s' % (_short_path(frame.filename), frame.lineno, frame.name)
            for frame in traceback.extract_tb(exc_tb)[-KEEP_FRAMES:]
        ]
        error_type = getattr(exc_type, '__name__', 'Exception')
        status = _http_status(exc_value)
        # Deliberately hashes only what is already in the report: two reports
        # with the same fingerprint are the same report, and the hash reveals
        # nothing the payload does not.
        digest = hashlib.sha256(
            '|'.join([module or '', error_type, str(status), operation or '']
                     + frames).encode()).hexdigest()[:16]
        return {
            'company_id': company.id,
            'fingerprint': digest,
            'error_type': error_type,
            'operation': operation or '',
            'module': module or 'atm',
            'http_status': status,
            'frames': '\n'.join(frames),
        }

    @api.model
    def _reporting_enabled(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            PARAM_CONSENT) == 'on'

    @api.model
    def _install_id(self):
        """A random per-database id, created on first use.

        It distinguishes "one install failing fifty times" from "fifty installs
        failing once" -- which is the difference between a local
        misconfiguration and a bug worth dropping everything for. It is a
        random number and says nothing about who the database belongs to.
        """
        params = self.env['ir.config_parameter'].sudo()
        value = params.get_param(PARAM_INSTALL_ID)
        if not value:
            value = uuid.uuid4().hex
            params.set_param(PARAM_INSTALL_ID, value)
        return value

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------
    @api.model
    def _cron_send_reports(self):
        if not self._reporting_enabled():
            return
        self._install_id()
        today_start = fields.Datetime.subtract(fields.Datetime.now(), hours=24)
        sent_today = self.sudo().search_count(
            [('state', '=', 'sent'), ('sent_date', '>=', today_start)])
        budget = MAX_PER_DAY - sent_today
        if budget <= 0:
            return
        pending = self.sudo().search(
            [('state', '=', 'pending'), ('attempts', '<', MAX_ATTEMPTS)],
            limit=budget)
        for report in pending:
            report._send()

    def _send(self):
        self.ensure_one()
        url = self.env['ir.config_parameter'].sudo().get_param(
            PARAM_URL, DEFAULT_URL)
        if not url:
            return False
        # Imported here: a database that never enables reporting should not
        # need the dependency present at all.
        import requests

        self.attempts += 1
        try:
            response = requests.post(
                url,
                json=self._payload(),
                timeout=SEND_TIMEOUT,
                headers={'Content-Type': 'application/json'})
            response.raise_for_status()
        except Exception as error:  # noqa: BLE001 - a failed report is not an incident
            _logger.info('Data Exchange error report not delivered: %s', error)
            if self.attempts >= MAX_ATTEMPTS:
                self.state = 'failed'
            return False
        self.write({'state': 'sent', 'sent_date': fields.Datetime.now()})
        return True

    def action_send_now(self):
        """Send this report immediately, from the button on the form."""
        for report in self:
            report._send()
        return True

    def action_discard(self):
        self.unlink()
        return {'type': 'ir.actions.act_window_closed'}

    @api.autovacuum
    def _gc_reports(self):
        """Sent reports have done their job; keep the list short."""
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), days=30)
        self.search([('state', '=', 'sent'),
                     ('sent_date', '<', cutoff)]).unlink()

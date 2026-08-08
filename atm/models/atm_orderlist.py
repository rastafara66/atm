# -*- coding: utf-8 -*-
"""Backwards compatibility with version 1.x.

Earlier versions exposed a single model, ``atm.orderlist``, with two methods
that databases upgrading from those versions still reference in their scheduled
actions. The methods are kept and delegate to the exchange engine so those
crons keep working after the upgrade.
"""
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class OrderList(models.Model):
    _name = 'atm.orderlist'
    _description = 'Order list (deprecated, use the exchange engine)'

    @api.model
    def export_order_list_to_json(self):
        """Deprecated: exports sales orders only. Use ``atm.exchange``."""
        _logger.info('atm.orderlist.export_order_list_to_json is deprecated; '
                     'delegating to the exchange engine.')
        log = self.env['atm.exchange'].export_entity('sale_order')
        return log.state == 'done'

    @api.model
    def import_order_list_from_json(self):
        """Deprecated: imports sales orders only. Use ``atm.exchange``."""
        _logger.info('atm.orderlist.import_order_list_from_json is deprecated; '
                     'delegating to the exchange engine.')
        log = self.env['atm.exchange'].import_entity('sale_order')
        return log.state == 'done'

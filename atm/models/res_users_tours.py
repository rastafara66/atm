# -*- coding: utf-8 -*-
"""Odoo onboarding tours (the web_tour "drops") are off for good.

Odoo switches them on for every administrator of a database without demo data, and "Stop tour" does not get rid of
them: any tour started by hand (a button, a ``?tour=`` link) switches them back on for the user
(``switch_tour_enabled`` in ``web_tour/static/src/js/tour_service.js``). So a new user gets them off, nobody can
switch them on, and ``data/tours_off.xml`` switches them off for everyone already in the database -- on install
and on every update of the module. ``web_tour`` is a declared dependency, so this class overrides its methods
whatever the module order.
"""
from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.depends('create_date')
    def _compute_tour_enabled(self):
        for user in self:
            user.tour_enabled = False

    @api.model
    def switch_tour_enabled(self, val):
        self.env.user.sudo().tour_enabled = False
        return False

    @api.model
    def _atm_tours_off(self):
        self.sudo().with_context(active_test=False).search(
            [('tour_enabled', '=', True)]).write({'tour_enabled': False})

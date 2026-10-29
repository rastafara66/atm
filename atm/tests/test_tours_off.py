# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestToursOff(TransactionCase):
    """Odoo onboarding tours: installing or updating the module switches them off for existing users,
    a tour started by hand does not switch them back on, a new user has none."""

    def test_tours_stay_off(self):
        admin = self.env.ref("base.user_admin")
        admin.tour_enabled = True
        self.env["res.users"]._atm_tours_off()
        self.assertFalse(admin.tour_enabled, "installing or updating the module switches tours off for existing users")
        self.assertFalse(self.env["res.users"].with_user(admin).switch_tour_enabled(True))
        self.assertFalse(admin.tour_enabled, "a tour started by hand does not switch tours back on")
        admin._compute_tour_enabled()
        self.assertFalse(admin.tour_enabled, "a new user has no tours")
        self.assertFalse(self.env["web_tour.tour"].with_user(admin).get_current_tour(), "no tour starts by itself")

# -*- coding: utf-8 -*-
"""Встановив — і ВСЕ працює. Перевірка з боку того, хто ставив.

🔴 НАВІЩО ЦЕЙ ТЕСТ ІСНУЄ. Права модуля роздано власній групі `atm.group_atm_manager`, а
адміністратор, ЗАВЕДЕНИЙ ПОКУПЦЕМ, у ці групи не входить. До 10.09.2026 він
не відкривав 2 моделі з 3 — тобто купив, поставив і не побачив нічого.

Чому цього не ловив жоден інший тест:
* штатні тести Odoo йдуть під `superuser`, якому доступне все;
* розробник дивиться під вбудованим `base.user_admin`, а це ІНШИЙ запис,
  якому права дісталися при першому встановленні на його машині;
* гейт «інсталл у чисту базу» робить `-i`, а вада вилазить на `-u`.

Тому тест саме СТВОРЮЄ користувача, а не бере наявного. Це і є та
відмінність, через яку вада жила непоміченою.
"""
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInstallerCanUseIt(TransactionCase):

    def _fresh_admin(self):
        """Адміністратор, ЯКОГО ЩОЙНО ЗАВЕЛИ. Не `base.user_admin`."""
        return self.env["res.users"].create({
            "name": "Freshly created administrator",
            "login": "fresh-admin-atm",
            "group_ids": [(6, 0, [
                self.env.ref("base.group_user").id,
                self.env.ref("base.group_system").id,
            ])],
        })

    def _menu_models(self):
        """Моделі, до яких ведуть МЕНЮ модуля — а не ті, які я вважаю за
        важливі: список «важливих» завжди відстає від меню."""
        data = self.env["ir.model.data"].search([
            ("module", "=", "atm"), ("model", "=", "ir.ui.menu")])
        models = set()
        for rec in data:
            menu = self.env["ir.ui.menu"].browse(rec.res_id).exists()
            if menu and menu.action and getattr(menu.action, "res_model", False):
                models.add(menu.action.res_model)
        return models

    def test_a_freshly_created_administrator_opens_every_menu(self):
        user = self._fresh_admin()
        models = self._menu_models()
        self.assertTrue(models, "меню модуля не знайдено — тест перевіряв би порожнечу")

        closed = []
        for model in sorted(models):
            if model not in self.env:
                continue
            try:
                self.env[model].with_user(user).search([], limit=1)
            except Exception:
                closed.append(model)

        self.assertFalse(
            closed,
            "адміністратор, заведений покупцем, не відкриває: %s. "
            "Саме так виглядає «встановив — і нічого не працює»." % ", ".join(closed))

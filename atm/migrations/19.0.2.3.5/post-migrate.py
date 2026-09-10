# -*- coding: utf-8 -*-
"""Дати адміністраторові доступ до модуля — інакше він не бачить нічого.

🔴 Запис у XML вирішує задачу для НОВИХ баз. У наявних
`base.group_system` уже існує, а записи на штатні ідентифікатори Odoo при
оновленні пропускає мовчки (`noupdate` у `ir_model_data`). Тому базам, які
оновлюються зі старої версії, потрібен цей прохід.

Групу `group_atm_manager` оголошено у файлі з `noupdate`, а до
     адміністратора вона не підключена ніяк: гейт показав, що щойно
     заведений адміністратор не відкриває 2 моделі з 3.

Знайдено гейтом `3A/tools/store/check_installer_access.py` 10.09.2026.
"""
import logging

_logger = logging.getLogger(__name__)

WIRING = [("base.group_system", "atm.group_atm_manager")]


def migrate(cr, version):
    if not version:
        return                      # перше встановлення — XML уже все зробив

    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    fixed = []
    for base_xid, our_xid in WIRING:
        base_group = env.ref(base_xid, raise_if_not_found=False)
        target = env.ref(our_xid, raise_if_not_found=False)
        if not base_group or not target:
            _logger.warning("групи %s або %s немає — пропускаю", base_xid, our_xid)
            continue
        if target in base_group.implied_ids:
            continue                # ідемпотентно
        base_group.write({"implied_ids": [(4, target.id)]})
        fixed.append("%s -> %s" % (base_xid, our_xid))

    _logger.info("права: %s", "; ".join(fixed) if fixed else "вже на місці")

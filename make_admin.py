"""Встроить вкладки «Rai: подписки», «Rai: правила», «Rai: уведомления» и «Rai: скидки» в admin.php основного сайта (rteam.info) — одним файлом.

    python make_admin.py путь/к/admin.php готовый/admin.php            # без ключа: ключ вводится в самой вкладке
    python make_admin.py admin.php out/admin.php --key 64-символьный-ключ  # ключ сразу внутри (ADMIN_API_KEY Rai)

Код вкладки — hosting/admin/admin_rai.php: он вставляется в admin.php целиком (между метками RAI: НАЧАЛО / КОНЕЦ),
плюс пять небольших вставок: права на действия, пункт меню, вывод вкладки, плитки на главной и уведомление.
Повторный запуск на уже обработанном файле просто обновляет вкладку. Всё остальное для Rai лежит на rai.rteam.info.
"""

import argparse
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(BASE, "hosting", "admin", "admin_rai.php")
START, END = "/* ==== RAI: НАЧАЛО (вкладка «Rai: подписки», собрано make_admin.py) ==== */", "/* ==== RAI: КОНЕЦ ==== */"

PERMS = '''    // Rai (rai.rteam.info): подписки
    "rai_grant" => "users.manage", "rai_revoke" => "users.manage", "rai_order_check" => "users.manage",
    "rai_save" => "settings.manage", "rai_check" => "settings.manage", "rai_plans" => "settings.manage",
    "rai_plans_reset" => "settings.manage", "rai_platega" => "settings.manage",
'''
PERMS_RULES = '''    // Rai: правила — нарушения и блокировки
    "rai_seen" => "users.manage", "rai_vdel" => "users.manage", "rai_ban" => "users.manage", "rai_unban" => "users.manage",
'''
PERMS_PUSH = '''    // Rai: уведомления — рассылка и устройства админов
    "rai_push_send" => "users.manage", "rai_push_del" => "users.manage",
'''
PERMS_MORE = '''    // Rai: роли (создатель, разработчик), скидки и промокоды
    "rai_role" => "users.manage", "rai_sale" => "settings.manage", "rai_sale_off" => "settings.manage",
    "rai_promo" => "settings.manage", "rai_promo_del" => "settings.manage",
'''
TAB_PUSH = '''    "rai_push"  => ["Rai: уведомления", "🔔", ["users.manage"],                             "Работа"],
'''
TAB_SALE = '''    "rai_sale"  => ["Rai: скидки",    "🏷", ["settings.manage"],                            "Работа"],
'''
RENDER_SALE = '''    <?php elseif ($tab === "rai_sale"): rai_sale_render(); ?>

'''
RENDER_PUSH = '''    <?php elseif ($tab === "rai_push"): rai_push_render(); ?>

'''
TAB = '''    "rai"       => ["Rai: подписки",  "✨", ["users.manage", "settings.manage"],            "Работа"],
'''
TAB_RULES = '''    "rai_rules" => ["Rai: правила",   "🚫", ["users.manage"],                               "Работа"],
'''
RENDER = '''    <?php elseif ($tab === "rai"): rai_admin_render(); ?>

'''
RENDER_RULES = '''    <?php elseif ($tab === "rai_rules"): rai_rules_render(); ?>

'''
KPI = '''            if (tab_allowed("rai") && ($rai_kpi = rai_cached_stats())) {  // Rai: подписки
                $kpis[] = ["rai", "✨", $rai_kpi["subscribers"], "подписчиков Rai", $rai_kpi["expiring"] > 0];
                $kpis[] = ["rai", "💳", number_format($rai_kpi["revenue_month"], 0, ",", " ") . " ₽", "оплат Rai за месяц", false];
            }
'''
NOTIF = '''                if (tab_allowed("rai") && ($rai_n = rai_cached_stats()) && $rai_n["expiring"]) $notif[] = ["rai", "⏳", $rai_n["expiring"], "подписок Rai кончаются"];
'''
NOTIF_RULES = '''                if (tab_allowed("rai_rules") && ($rai_v = rai_cached_stats()) && !empty($rai_v["violations_new"])) $notif[] = ["rai_rules", "🚫", $rai_v["violations_new"], "нарушений правил в Rai"];
'''
KPI_RULES = '''            if (tab_allowed("rai_rules") && ($rai_r = rai_cached_stats()) && !empty($rai_r["violations_new"])) {  // Rai: правила
                $kpis[] = ["rai_rules", "🚫", $rai_r["violations_new"], "нарушений правил Rai", true];
            }
'''


class PatchError(Exception):
    pass


def insert_after(text, anchor, addition, marker):
    """Вставить addition после строки с anchor (если ещё не вставлено)."""
    if marker in text:
        return text
    i = text.find(anchor)
    if i < 0:
        raise PatchError("не нашёл в admin.php: " + anchor[:70])
    end = text.index("\n", i) + 1
    return text[:end] + addition + text[end:]


def insert_before(text, anchor, addition, marker):
    if marker in text:
        return text
    i = text.find(anchor)
    if i < 0:
        raise PatchError("не нашёл в admin.php: " + anchor[:70])
    start = text.rfind("\n", 0, i) + 1
    return text[:start] + addition + text[start:]


def block(key=None):
    with open(SOURCE, encoding="utf-8") as f:
        code = f.read()
    code = re.sub(r"^<\?php\s*\n", "", code, count=1)
    if key:
        if not re.fullmatch(r"[A-Za-z0-9_\-]{32,}", key):
            raise PatchError("ключ: от 32 символов, латиница и цифры")
        code = ("// Ключ связи с rai.rteam.info — тот же, что ADMIN_API_KEY в config.php Rai. Не выкладывайте этот файл в GitHub.\n"
                f"if (!defined('RAI_ADMIN_KEY')) define('RAI_ADMIN_KEY', '{key}');\n\n") + code
    return (START + "\n" + code.rstrip() + "\n\n"
            "if ($tab === \"rai\") rai_admin_export();  // ?tab=rai&export=csv — файл вместо страницы\n"
            "if ($_SERVER[\"REQUEST_METHOD\"] === \"POST\" && $tab === \"rai\") rai_admin_post();\n"
            "if ($_SERVER[\"REQUEST_METHOD\"] === \"POST\" && $tab === \"rai_rules\") rai_rules_post();\n"
            "if ($_SERVER[\"REQUEST_METHOD\"] === \"POST\" && $tab === \"rai_push\") rai_push_post();\n"
            "if ($_SERVER[\"REQUEST_METHOD\"] === \"POST\" && $tab === \"rai_sale\") rai_sale_post();\n" + END + "\n\n")


def patch(text, key=None):
    # старая схема (отдельный admin_rai.php) — убираем
    text = re.sub(r"/\* RAI: ПОДПИСКИ \(вкладка «Rai», логика — в admin_rai\.php рядом с этим файлом\) \*/\n"
                  r"require_once __DIR__ \. '/admin_rai\.php';\n.*?rai_admin_post\(\);\n\n", "", text, flags=re.S)
    # сама вкладка: заменить, если уже есть, иначе вставить перед обработкой остальных форм
    if START in text:
        a, b = text.index(START), text.index(END) + len(END)
        text = text[:a] + block(key).rstrip("\n") + text[b:]
    else:
        text = insert_before(text, "/* POST ДЛЯ ОСТАЛЬНОГО */", block(key), START)
    text = insert_after(text, '"save_perms" => "perms.manage", "reset_perms" => "perms.manage",', PERMS, '"rai_order_check" =>')
    text = insert_after(text, '"rai_plans_reset" => "settings.manage", "rai_platega" => "settings.manage",', PERMS_RULES, '"rai_ban" =>')
    text = insert_after(text, '"rai_ban" => "users.manage", "rai_unban" => "users.manage",', PERMS_PUSH, '"rai_push_send" =>')
    text = insert_after(text, '"rai_push_send" => "users.manage", "rai_push_del" => "users.manage",', PERMS_MORE, '"rai_role" =>')
    text = insert_after(text, '"directors" => ["Директора школ"', TAB, '"rai"       => ["Rai')
    text = insert_after(text, '"rai"       => ["Rai: подписки"', TAB_RULES, '"rai_rules" => ["Rai')
    text = insert_after(text, '"rai_rules" => ["Rai: правила"', TAB_PUSH, '"rai_push"  => ["Rai')
    text = insert_after(text, '"rai_push"  => ["Rai: уведомления"', TAB_SALE, '"rai_sale"  => ["Rai')
    text = insert_before(text, '<?php elseif ($tab === "directors"): ?>', RENDER, 'rai_admin_render(); ?>')
    text = insert_before(text, '<?php elseif ($tab === "directors"): ?>', RENDER_RULES, 'rai_rules_render(); ?>')
    text = insert_before(text, '<?php elseif ($tab === "directors"): ?>', RENDER_PUSH, 'rai_push_render(); ?>')
    text = insert_before(text, '<?php elseif ($tab === "directors"): ?>', RENDER_SALE, 'rai_sale_render(); ?>')
    text = insert_after(text, 'if (can("projects.manage"))  $kpis[] = ["projects"', KPI, '$rai_kpi = rai_cached_stats()')
    text = insert_after(text, 'if ($my_unpaid_fines)                                 $notif[] = ["fines"', NOTIF, '$rai_n = rai_cached_stats()')
    text = insert_after(text, '$rai_n = rai_cached_stats()', NOTIF_RULES, '$rai_v = rai_cached_stats()')
    text = insert_after(text, '$kpis[] = ["rai", "💳"', KPI_RULES, '$rai_r = rai_cached_stats()')
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("admin", help="исходный admin.php")
    parser.add_argument("out", help="куда сохранить готовый admin.php")
    parser.add_argument("--key", help="ключ ADMIN_API_KEY (вписать сразу; иначе вводится во вкладке)")
    args = parser.parse_args()
    with open(args.admin, encoding="utf-8") as f:
        text = f.read()
    try:
        result = patch(text, args.key)
    except PatchError as e:
        sys.exit("Ошибка: " + str(e))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"Готово: {args.out} (+{result.count(chr(10)) - text.count(chr(10))} строк, ключ {'вписан' if args.key else 'не вписан'})")


if __name__ == "__main__":
    main()

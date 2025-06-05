"""
dashboard_data.py – сбор и подготовка статистики для Dashboard Overall (Poker‑Copilot style)

• Работает с базой bbline.sqlite (структура из твоего дампа).
• Считает основные метрики в формате, привычном по Poker Copilot.
  ‑ VPIP, PFR
  ‑ WtS  (Went to Showdown %)
  ‑ WaS  (Won at Showdown %)
  ‑ WwS  (Won without Showdown %)
  ‑ WWSF (Won When Saw Flop %)
  ‑ TBB/100 (bb per 100 hands)
  ‑ Profit $, Profit bb, Hero Rake $.
• Данные округляются как в HUD: проценты без десятых, деньги – 2 знака, bb – 1 знак.
• Готовит серию для графика профита по датам – сразу с округлением.

Если база лежит не там – поправь DB_PATH.
"""

import sqlite3
from typing import Dict, Any, List, Tuple

DB_PATH = r"C:\Users\GameBase\BBLine\bbline\database\bbline.sqlite"


def get_saw_flop_ids(cur: sqlite3.Cursor) -> List[str]:
    """Возвращает список hand_id, где был флоп (board не пустой)."""
    cur.execute("SELECT hand_id FROM hands WHERE board IS NOT NULL AND board != ''")
    return [row[0] for row in cur.fetchall()]


def get_dashboard_stats() -> Dict[str, Any]:
    """
    Возвращает словарь метрик, совпадающих с Poker Copilot/H2N.
    Все проценты — только среди рук, где был флоп (для WTSD, WWSF, WwS, WaS).
    """
    with sqlite3.connect(DB_PATH) as cx:
        cur = cx.cursor()

        # Основные (не зависят от board)
        hands_cnt = cur.execute("SELECT COUNT(*) FROM hands").fetchone()[0] or 0
        profit_usd = round(cur.execute("SELECT SUM(hero_net) FROM hands").fetchone()[0] or 0.0, 2)
        profit_bb = round(cur.execute("SELECT SUM(net_bb) FROM hands").fetchone()[0] or 0.0, 1)
        hero_rake_usd = round(
            cur.execute("SELECT SUM(hero_rake) FROM hands").fetchone()[0] or 0.0, 2
        )
        tbb_per_100 = round((profit_bb / hands_cnt) * 100 if hands_cnt else 0.0, 1)

        # VPIP, PFR — по всем рукам
        vpip_pct, pfr_pct = cur.execute(
            """
            SELECT 100.0 * SUM(vpip) / COUNT(*),
                   100.0 * SUM(pfr)  / COUNT(*)
            FROM   computed_stats;
            """
        ).fetchone()
        vpip_pct = round(vpip_pct or 0.0)
        pfr_pct = round(pfr_pct or 0.0)

        # Флопнутые руки (по ним и считается всё постфлоп)
        flop_hand_ids = get_saw_flop_ids(cur)
        flop_cnt = len(flop_hand_ids)

        # Если нет рук с флопом — всё 0
        if flop_cnt == 0:
            return {
                "Hands": hands_cnt,
                "Profit $": profit_usd,
                "Profit bb": profit_bb,
                "TBB/100": tbb_per_100,
                "Hero Rake $": hero_rake_usd,
                "VPIP": vpip_pct,
                "PFR": pfr_pct,
                "WtS": 0,  # Went to Showdown
                "WaS": 0,  # Won at Showdown
                "WwS": 0,  # Won without Showdown
                "WWSF": 0,  # Won When Saw Flop
            }

        # Считаем WTSD (дошёл до вскрытия среди рук с флопом)
        sql_ids = ",".join(["?"] * flop_cnt)
        # WTSD numerator: рук, где дошёл до вскрытия
        wt_s_cnt = (
            cur.execute(
                f"SELECT COUNT(*) FROM computed_stats WHERE hand_id IN ({sql_ids}) AND wt_sd = 1",
                flop_hand_ids,
            ).fetchone()[0]
            or 0
        )
        # WSD numerator: выиграл шоудаун среди WTSD рук
        wa_s_cnt = (
            cur.execute(
                f"SELECT COUNT(*) FROM computed_stats WHERE hand_id IN ({sql_ids}) AND w_sd = 1",
                flop_hand_ids,
            ).fetchone()[0]
            or 0
        )
        # WwS numerator: выиграл без вскрытия (wwsf = 1, но НЕ дошёл до вскрытия)
        # Строго: wwsf=1 и wt_sd=0
        ww_s_cnt = (
            cur.execute(
                f"SELECT COUNT(*) FROM computed_stats WHERE hand_id IN ({sql_ids}) AND wwsf = 1 AND wt_sd = 0",
                flop_hand_ids,
            ).fetchone()[0]
            or 0
        )
        # WWSF numerator: выиграл после флопа (или шоудаун, или без вскрытия)
        wwsf_cnt = (
            cur.execute(
                f"SELECT COUNT(*) FROM computed_stats WHERE hand_id IN ({sql_ids}) AND (wwsf = 1 OR w_sd = 1)",
                flop_hand_ids,
            ).fetchone()[0]
            or 0
        )

        # Делим аккуратно
        def pct(num: int, den: int) -> int:
            return round((num / den) * 100) if den else 0

        WtS = pct(wt_s_cnt, flop_cnt)
        WaS = pct(wa_s_cnt, wt_s_cnt) if wt_s_cnt else 0
        WwS = pct(ww_s_cnt, flop_cnt)
        WWSF = pct(wwsf_cnt, flop_cnt)

        return {
            "Hands": hands_cnt,
            "Profit $": profit_usd,
            "Profit bb": profit_bb,
            "TBB/100": tbb_per_100,
            "Hero Rake $": hero_rake_usd,
            "VPIP": vpip_pct,
            "PFR": pfr_pct,
            "WtS": WtS,
            "WaS": WaS,
            "WwS": WwS,
            "WWSF": WWSF,
        }


def get_profit_by_date() -> List[Tuple[str, float, float]]:
    """Список (дата, profit $, profit bb) – всё округлено."""
    with sqlite3.connect(DB_PATH) as cx:
        cur = cx.cursor()
        rows = cur.execute(
            """
            SELECT SUBSTR(datetime_utc, 1, 10)         AS d,
                   ROUND(SUM(hero_net), 2)            AS profit_usd,
                   ROUND(SUM(net_bb), 1)              AS profit_bb
            FROM   hands
            GROUP  BY d
            ORDER  BY d;
            """
        ).fetchall()
        # Округлить дату сразу
        return [(d, round(profit_usd, 2), round(profit_bb, 1)) for d, profit_usd, profit_bb in rows]


if __name__ == "__main__":
    from pprint import pprint

    print("\nDashboard Stats ->")
    pprint(get_dashboard_stats(), sort_dicts=False)
    print("\nProfit by Date ->")
    for line in get_profit_by_date():
        print(line)

# bbline/analysis/analyzer.py
"""
Глобальный аналитический модуль BBLine.

Считает:
• hands_cnt            – число рук
• profit_usd           – суммарная прибыль ($)
• bb_per_100           – винрейт в bb/100
• vpip, pfr, 3bet      – % основных префлоп-метрик
• wwsf, wt_sd, w_sd    – постфлоп итоги
• cbet_flop            – частота C-bet на флопе
• fold_to_3b, fold_to_cbet – частота фолдов

!!! Перед запуском убедись, что
    1) import HH → parse_hand
    2) python -m bbline.analysis.rebuild_computed
уже гонялись и заполнили таблицы.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Tuple

DB = Path(__file__).resolve().parents[1] / "database" / "bbline.sqlite"


def _fetch_one(cur: sqlite3.Cursor, sql: str, params: Tuple[Any, ...] = ()) -> Any:
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else None


def get_basic_stats() -> Dict[str, float]:
    """
    Возвращает все ключевые метрики одним dict’ом.
    """
    with sqlite3.connect(DB) as cx:
        cx.row_factory = sqlite3.Row
        cur = cx.cursor()

        # ---------------- базовые числа ----------------
        hands_cnt = _fetch_one(cur, "SELECT COUNT(*) FROM hands WHERE hero_seat IS NOT NULL;") or 0
        if hands_cnt == 0:
            return {"hands_cnt": 0}

        profit = _fetch_one(cur, "SELECT SUM(hero_net) FROM hands;") or 0.0

        bb_per_100 = (
            _fetch_one(
                cur,
                """
              SELECT  ROUND(AVG(net_bb) * 100, 2)
              FROM    hands
              WHERE   net_bb IS NOT NULL;
            """,
            )
            or 0.0
        )

        # ------------------- префлоп -------------------
        vpip = (
            _fetch_one(
                cur,
                """
            SELECT ROUND(AVG(vpip)*100, 1) FROM computed_stats;
            """,
            )
            or 0.0
        )

        pfr = _fetch_one(cur, "SELECT ROUND(AVG(pfr)*100, 1) FROM computed_stats;") or 0.0
        threebet = _fetch_one(cur, "SELECT ROUND(AVG(threebet)*100, 2) FROM computed_stats;") or 0.0
        fold_to_3b = (
            _fetch_one(cur, "SELECT ROUND(AVG(fold_to_3b)*100, 1) FROM computed_stats;") or 0.0
        )

        # ------------------- постфлоп ------------------
        cbet_flop = (
            _fetch_one(cur, "SELECT ROUND(AVG(cbet_flop)*100, 1) FROM computed_stats;") or 0.0
        )
        fold_to_cbet = (
            _fetch_one(cur, "SELECT ROUND(AVG(fold_to_cbet)*100, 1) FROM computed_stats;") or 0.0
        )

        wwsf = _fetch_one(cur, "SELECT ROUND(AVG(wwsf)*100, 1) FROM computed_stats;") or 0.0
        wt_sd = _fetch_one(cur, "SELECT ROUND(AVG(wt_sd)*100, 1) FROM computed_stats;") or 0.0
        w_sd = _fetch_one(cur, "SELECT ROUND(AVG(w_sd)*100, 1) FROM computed_stats;") or 0.0

        # -------------- герой-рейк и EV future ----------
        hero_rake = _fetch_one(cur, "SELECT ROUND(SUM(hero_rake), 2) FROM hands;") or 0.0

    return {
        "hands_cnt": hands_cnt,
        "profit_usd": round(profit, 2),
        "bb_per_100": bb_per_100,
        "vpip_pct": vpip,
        "pfr_pct": pfr,
        "threebet_pct": threebet,
        "fold_to_3b_pct": fold_to_3b,
        "cbet_flop_pct": cbet_flop,
        "fold_to_cbet_pct": fold_to_cbet,
        "wwsf_pct": wwsf,
        "wt_sd_pct": wt_sd,
        "w_sd_pct": w_sd,
        "hero_rake_usd": hero_rake,
    }


# -------------------- CLI / quick test --------------------
if __name__ == "__main__":
    from pprint import pprint

    stats = get_basic_stats()
    if stats["hands_cnt"] == 0:
        print("🛑 В базе нет рук героя – сначала заимпортируй HH и пересчитай.")
    else:
        print("========== HERO SUMMARY ==========")
        pprint(stats, sort_dicts=False)

"""
Модуль для работы с данными дашборда.

Содержит функции для получения статистики и графиков.

Сбор и подготовка статистики для Dashboard Overall (Poker Copilot‑style)
с поддержкой фильтров **дата → лимит → позиция**.

• Фильтр по дате (inclusive): date_from, date_to  → 'YYYY‑MM‑DD'.
• Фильтр по лимиту (limit_bb, список float) — можно выбрать NL2 = 0.02, NL5 = 0.05 …
• Фильтр по позиции Hero (BTN / CO / MP / UTG / SB / BB).

Метрики:
  Hands, Profit $, Profit bb, bb/100, Hero Rake, VPIP, PFR,
  WtS, WaS, WwS, WWSF (строго среди рук, где был флоп).

Использование:
    from dashboard_data import get_dashboard_stats, get_profit_by_date
    stats = get_dashboard_stats(date_from="2025-01-01", positions=["BTN","CO"])
    graph  = get_profit_by_date(date_from="2025-01-01")

Если база лежит не рядом — поправь DB_PATH.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple, Literal
from bbline.analysis.leakfinder import run_leakfinder
from .utils import DB_PATH, get_hand_ids
import pandas as pd

# Константы для позиций
POSITIONS = ["BB", "SB", "BTN", "CO", "MP", "EP"]

# Константы для лимитов
LIMITS = [0.02, 0.05, 0.10, 0.25, 0.50, 1.00]

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _pos_from_seats(hero: int, btn: int) -> Literal["BB", "SB", "BTN", "CO", "MP", "EP"]:
    """Mapping seat → позиция (6‑max).
    offset = (hero – btn) mod 6
        0  BTN
        1  SB
        2  BB
        3  UTG
        4  MP
        5  CO
    """
    offset = (hero - btn) % 6
    return POSITIONS[offset]


def _fetch_one(cur: sqlite3.Cursor, query: str, params: Sequence[Any] | None = None) -> float:
    """Выполняет SQL-запрос и возвращает одно значение с проверкой на None."""
    val = cur.execute(query, params or ()).fetchone()[0]
    return val or 0.0


def _validate_filters(
    date_from: str | None,
    date_to: str | None,
    limits: List[float] | None,
    positions: List[str] | None,
) -> None:
    """Проверяет корректность входных фильтров."""
    if date_from and not _is_valid_date(date_from):
        raise ValueError(f"Invalid date_from format: {date_from}. Use YYYY-MM-DD")
    if date_to and not _is_valid_date(date_to):
        raise ValueError(f"Invalid date_to format: {date_to}. Use YYYY-MM-DD")
    if date_from and date_to and date_from > date_to:
        raise ValueError("date_from must be <= date_to")
    if positions and not all(p in POSITIONS for p in positions):
        raise ValueError(f"Invalid positions. Use any of: {', '.join(POSITIONS)}")
    if limits and not all(
        isinstance(limit_val, (int, float)) and limit_val > 0 for limit_val in limits
    ):
        raise ValueError("All limits must be positive numbers")


def _is_valid_date(date_str: str) -> bool:
    """Проверяет формат даты YYYY-MM-DD."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def get_saw_flop_ids(cur: sqlite3.Cursor) -> List[str]:
    """Возвращает список hand_id, где был флоп (board не пустой)."""
    cur.execute("SELECT hand_id FROM hands WHERE board IS NOT NULL AND board != ''")
    return [row[0] for row in cur.fetchall()]


def get_dashboard_stats(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limits: Optional[List[float]] = None,
    positions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Возвращает агрегаты с учётом фильтров."""
    _validate_filters(date_from, date_to, limits, positions)

    with sqlite3.connect(DB_PATH) as cx:
        cur = cx.cursor()

        # --- отфильтрованные hand_ids --------------------------------------
        hand_ids = get_hand_ids(cur, date_from, date_to, limits, positions)
        if not hand_ids:
            return {
                k: 0
                for k in [
                    "Hands",
                    "Profit $",
                    "Profit bb",
                    "TBB/100",
                    "Hero Rake $",
                    "VPIP",
                    "PFR",
                    "WtS",
                    "WaS",
                    "WwS",
                    "WWSF",
                ]
            }

        placeholders = ",".join(["?"] * len(hand_ids))

        # --- базовые агрегаты (из hands) -----------------------------------
        hands_cnt = len(hand_ids)
        profit_usd = round(
            _fetch_one(
                cur, f"SELECT SUM(hero_net) FROM hands WHERE hand_id IN ({placeholders})", hand_ids
            ),
            2,
        )
        profit_bb = round(
            _fetch_one(
                cur, f"SELECT SUM(net_bb) FROM hands WHERE hand_id IN ({placeholders})", hand_ids
            ),
            1,
        )
        hero_rake_usd = round(
            _fetch_one(
                cur, f"SELECT SUM(hero_rake) FROM hands WHERE hand_id IN ({placeholders})", hand_ids
            ),
            2,
        )
        tbb_per_100 = round((profit_bb / hands_cnt) * 100, 1)

        # --- VPIP / PFR ------------------------------------------------------
        vpip_pct, pfr_pct = cur.execute(
            f"""
            SELECT 100.0 * SUM(vpip) / COUNT(*),
                   100.0 * SUM(pfr)  / COUNT(*)
            FROM   computed_stats WHERE hand_id IN ({placeholders});
            """,
            hand_ids,
        ).fetchone()
        vpip_pct = round(vpip_pct or 0.0)
        pfr_pct = round(pfr_pct or 0.0)

        # --- постфлоп & шоудаун --------------------------------------------
        wt_s_cnt, w_sd_cnt, wwsf_only_cnt = cur.execute(
            f"""
            SELECT SUM(wt_sd),
                   SUM(w_sd),
                   SUM(CASE WHEN wwsf=1 AND wt_sd=0 THEN 1 ELSE 0 END)
            FROM   computed_stats WHERE hand_id IN ({placeholders});
            """,
            hand_ids,
        ).fetchone()
        wt_s_cnt = int(wt_s_cnt or 0)
        w_sd_cnt = int(w_sd_cnt or 0)
        wws_only_cnt = int(wwsf_only_cnt or 0)  # выиграл без вскрытия

        # --- сколько рук дошли до флопа ------------------------------------
        flop_cnt = _fetch_one(
            cur,
            f"SELECT COUNT(*) FROM hands WHERE hand_id IN ({placeholders}) AND board IS NOT NULL AND board != ''",
            hand_ids,
        )
        flop_cnt = int(flop_cnt)

        def pct(num: int, den: int) -> int:
            return round((num / den) * 100) if den else 0

        WtS = pct(wt_s_cnt, flop_cnt)
        WaS = pct(w_sd_cnt, wt_s_cnt) if wt_s_cnt else 0
        WwS = pct(wws_only_cnt, flop_cnt)
        WWSF = pct(w_sd_cnt + wws_only_cnt, flop_cnt)

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


def get_profit_by_date(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limits: Optional[List[float]] = None,
    positions: Optional[List[str]] = None,
) -> Tuple[List[str], List[float]]:
    """Возвращает даты и профит для графика."""
    _validate_filters(date_from, date_to, limits, positions)

    with sqlite3.connect(DB_PATH) as cx:
        cur = cx.cursor()
        hand_ids = get_hand_ids(cur, date_from, date_to, limits, positions)
        if not hand_ids:
            return [], []
        placeholders = ",".join(["?"] * len(hand_ids))
        rows = cur.execute(
            f"""
            SELECT SUBSTR(datetime_utc, 1, 10) as d,
                   ROUND(SUM(hero_net), 2)
            FROM   hands
            WHERE  hand_id IN ({placeholders})
            GROUP  BY d
            ORDER  BY d;
            """,
            hand_ids,
        ).fetchall()
        return [row[0] for row in rows], [row[1] for row in rows]


if __name__ == "__main__":
    from pprint import pprint

    # Пример использования с фильтрами
    print("\nВсе руки:")
    pprint(get_dashboard_stats())

    print("\nТолько BTN и CO:")
    pprint(get_dashboard_stats(positions=["BTN", "CO"]))

    print("\nNL2 и NL5:")
    pprint(get_dashboard_stats(limits=[LIMITS[0], LIMITS[1]]))

    print("\nЗа последний месяц:")
    from datetime import datetime, timedelta

    today = datetime.now()
    month_ago = today - timedelta(days=30)
    pprint(
        get_dashboard_stats(
            date_from=month_ago.strftime("%Y-%m-%d"), date_to=today.strftime("%Y-%m-%d")
        )
    )

    leaks = run_leakfinder(
        date_from="2024-01-01", date_to="2024-03-20", limits=[2, 5], positions=["BTN", "CO"]
    )

    dates, profit_usd = get_profit_by_date(
        date_from="2024-01-01", date_to="2024-03-20", limits=[2, 5], positions=["BTN", "CO"]
    )
    df = pd.DataFrame(
        {
            "Дата": dates,
            "Профит $": profit_usd,
        }
    )

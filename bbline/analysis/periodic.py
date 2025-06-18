"""
Модуль для анализа статистики и утечек по временным периодам (день/неделя/месяц).
"""

from typing import Literal, List, Dict, Any
import sqlite3
from bbline.utils import DB_PATH

Period = Literal["day", "week", "month"]


def _period_expr(period: Period) -> str:
    """Возвращает SQL-выражение для группировки по периоду."""
    return {
        "day": "strftime('%Y-%m-%d', datetime_utc)",
        "week": "strftime('%Y-%W', datetime_utc)",  # ISO-week
        "month": "strftime('%Y-%m', datetime_utc)",
    }[period]


def agg_stats_by_period(period: Period = "week") -> List[Dict[str, Any]]:
    """
    Возвращает агрегированную статистику по периодам.

    Args:
        period: Период группировки ('day', 'week', 'month')

    Returns:
        Список словарей с метриками по каждому периоду
    """
    expr = _period_expr(period)
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            f"""
            SELECT {expr} AS period,
                   SUM(fold_to_3b)  AS fold_to_3b,
                   SUM(threebet)    AS threebet,
                   SUM(cbet_flop)   AS cbet_flop,
                   COUNT(*)         AS total
            FROM   computed_stats cs
            JOIN   hands h USING(hand_id)
            GROUP  BY period
            ORDER  BY period DESC;
        """
        ).fetchall()
    return [
        {
            "period": r["period"],
            "fold_to_3b_pct": round(r["fold_to_3b"] * 100 / r["total"], 1),
            "threebet_pct": round(r["threebet"] * 100 / r["total"], 1),
            "cbet_flop_pct": round(r["cbet_flop"] * 100 / r["total"], 1),
            "hands": r["total"],
        }
        for r in rows
    ]


def top_losing_hands(period: Period = "week", n: int = 5) -> List[Dict[str, Any]]:
    """
    Возвращает топ-N самых убыточных рук в каждом периоде.

    Args:
        period: Период группировки ('day', 'week', 'month')
        n: Количество рук для каждого периода

    Returns:
        Список словарей с периодами и их худшими руками
    """
    expr = _period_expr(period)
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            f"""
            SELECT  period,
                    hand_id,
                    hero_net
            FROM (
                SELECT {expr} AS period,
                       hand_id,
                       hero_net,
                       ROW_NUMBER() OVER (
                           PARTITION BY {expr}
                           ORDER BY hero_net  -- минусы идут первыми
                       ) AS rn
                FROM hands
            )
            WHERE rn <= ?
            ORDER BY period DESC, hero_net;
        """,
            (n,),
        ).fetchall()
    # группируем в Python для удобства
    out: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        out.setdefault(r["period"], []).append({"hand_id": r["hand_id"], "hero_net": r["hero_net"]})
    return [{"period": p, "hands": lst} for p, lst in out.items()]


def leaks_by_period(period: Period = "week") -> List[Dict[str, Any]]:
    """
    Возвращает список утечек по периодам.

    Args:
        period: Период группировки ('day', 'week', 'month')

    Returns:
        Список словарей с периодами и их утечками
    """
    rows = agg_stats_by_period(period)
    leaks = []
    for r in rows:
        week_leaks = []
        if r["fold_to_3b_pct"] >= 65:
            week_leaks.append("Overfold vs 3-Bet")
        if r["threebet_pct"] <= 5:
            week_leaks.append("Low 3-Bet Frequency")
        if r["cbet_flop_pct"] >= 80:
            week_leaks.append("Over-CBet Flop")
        leaks.append({"period": r["period"], "leaks": week_leaks})
    return leaks

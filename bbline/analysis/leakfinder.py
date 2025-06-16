"""
leakfinder.py – LeakFinder Lite (3 простых правила)

Идея: пробегаем агрегаты hero'а по базе (с учётом тех же фильтров,
что и dashboard) и возвращаем список «критических» ликов.
Каждый лик – это структура {
    'name':       читабельное имя,
    'metric':     метрика, которую проверяем,
    'value':      фактическое значение в %,
    'threshold':  порог
}

⚠️  Использует таблицу computed_stats для быстрых счётчиков.
    Поля, которые уже есть (по README):
        threebet, fold_to_3b, cbet_flop

Правила Lite (#1 MVP):
    1. Overfold vs 3‑Bet – fold_to_3b ≥ 65 %
    2. Low 3‑Bet Frequency – threebet ≤ 5 %
    3. Over‑CBet Flop – cbet_flop ≥ 80 %

Фильтры (date_from / date_to / limits / positions) такие же, как в dashboard_data.
"""

from __future__ import annotations

import random
import sqlite3
from typing import Any, Dict, List

from bbline.utils import get_hand_ids, DB_PATH

# ---------------------------------------------------------------------------
# rule definitions
# ---------------------------------------------------------------------------
Rule = Dict[str, Any]

RULES: List[Rule] = [
    {
        "name": "Overfold vs 3-Bet",
        "metric": "fold_to_3b_pct",
        "cmp": "ge",  # >= threshold
        "threshold": 65,
        "condition_sql": "fold_to_3b = 1",
        "explain": "Ты слишком часто фолдишь на 3‑бет. Открывай диапазон защиты или оппоненты будут давить чаще.",
    },
    {
        "name": "Low 3-Bet Frequency",
        "metric": "threebet_pct",
        "cmp": "le",  # <= threshold
        "threshold": 5,
        "condition_sql": "threebet = 0",
        "explain": "3‑бетишь реже 5 % рук. Реги стилим безнаказанно.",
    },
    {
        "name": "Over‑CBet Flop",
        "metric": "cbet_flop_pct",
        "cmp": "ge",
        "threshold": 80,
        "condition_sql": "cbet_flop = 1",
        "explain": "Ставишь контбет почти всегда. Оппоненты будут подстраиваться – чек‑рейз / float чаще.",
    },
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _ensure_tags_table(cur: sqlite3.Cursor):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tags (
            hand_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            note TEXT,
            PRIMARY KEY (hand_id, tag)
        );
        """
    )


def _pct(num: int, den: int) -> float:
    """Вычисляет процентное соотношение с округлением до 1 знака после запятой."""
    return round((num / den) * 100, 1) if den else 0.0


def _aggregate_stats(cur: sqlite3.Cursor, hand_ids: List[str]) -> Dict[str, float]:
    """Возвращает процентные метрики по выбранным hand_id."""
    if not hand_ids:
        return {r["metric"]: 0.0 for r in RULES}
    ph = ",".join(["?"] * len(hand_ids))
    row = cur.execute(
        f"""
        SELECT
            SUM(fold_to_3b),
            SUM(threebet),
            SUM(cbet_flop),
            COUNT(*)
        FROM computed_stats
        WHERE hand_id IN ({ph});
        """,
        hand_ids,
    ).fetchone()
    fold_to_3b, threebet, cbet_flop, total = (int(x or 0) for x in row)
    return {
        "fold_to_3b_pct": _pct(fold_to_3b, total),
        "threebet_pct": _pct(threebet, total),
        "cbet_flop_pct": _pct(cbet_flop, total),
    }


def _tag_leaks(cur: sqlite3.Cursor, rule: Rule, hand_ids: List[str]):
    """Помечает руки в таблице tags под имя лика (INSERT OR IGNORE)."""
    if not hand_ids:
        return
    ph = ",".join(["?"] * len(hand_ids))
    # Отобрать руки по condition_sql
    rows = cur.execute(
        f"SELECT hand_id FROM computed_stats WHERE hand_id IN ({ph}) AND {rule['condition_sql']};",
        hand_ids,
    ).fetchall()
    leak_hand_ids = [r[0] for r in rows]
    cur.executemany(
        "INSERT OR IGNORE INTO tags (hand_id, tag, note) VALUES (?, ?, NULL);",
        [(hid, rule["name"]) for hid in leak_hand_ids],
    )


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------
def run_leakfinder(
    date_from: str | None = None,
    date_to: str | None = None,
    limits: List[float] | None = None,
    positions: List[str] | None = None,
    save_tags: bool = False,
) -> List[Dict[str, Any]]:
    """Возвращает список нарушенных правил и (опц.) сохраняет теги в БД."""
    with sqlite3.connect(DB_PATH) as cx:
        cur = cx.cursor()
        if save_tags:
            _ensure_tags_table(cur)
        hand_ids = get_hand_ids(cur, date_from, date_to, limits, positions)
        stats = _aggregate_stats(cur, hand_ids)
        leaks: List[Dict[str, Any]] = []
        for rule in RULES:
            val = stats[rule["metric"]]
            violated = (rule["cmp"] == "ge" and val >= rule["threshold"]) or (
                rule["cmp"] == "le" and val <= rule["threshold"]
            )
            if violated:
                leaks.append(
                    {
                        "name": rule["name"],
                        "value": val,
                        "threshold": rule["threshold"],
                        "explain": rule["explain"],
                    }
                )
                if save_tags:
                    _tag_leaks(cur, rule, hand_ids)
        if save_tags:
            cx.commit()
    return leaks


def get_example_hands(
    leak_name: str,
    n: int = 5,
    order: str = "loss",  # 'loss' → самые минусовые; 'rand' → случайные; 'win' → плюсовые
) -> List[Dict[str, Any]]:
    """Возвращает n hand_id (+ net$) для выбранного лика из таблицы tags."""
    with sqlite3.connect(DB_PATH) as cx:
        cur = cx.cursor()
        _ensure_tags_table(cur)
        cur.execute(
            """
            SELECT h.hand_id, h.hero_net
            FROM   hands h
            JOIN   tags  t ON t.hand_id = h.hand_id
            WHERE  t.tag = ?
            """,
            (leak_name,),
        )
        rows = cur.fetchall()
    if not rows:
        return []
    # сорт/сэмпл
    if order == "loss":
        rows.sort(key=lambda x: x[1])  # от самых больших минусов
    elif order == "win":
        rows.sort(key=lambda x: x[1], reverse=True)
    else:  # rand
        random.shuffle(rows)
    rows = rows[:n]
    return [{"hand_id": hid, "hero_net": net} for hid, net in rows]


if __name__ == "__main__":
    from pprint import pprint

    print("Violations →")
    pprint(run_leakfinder(save_tags=True))
    print("\nExamples (Overfold) →")
    pprint(get_example_hands("Overfold vs 3-Bet", n=3))

# analysis/hero_hands.py
"""
BBLine – отчёт по карманкам Hero
────────────────────────────────
Показывает:
  • частоту раздач каждой руки
  • общий результат в BB
  • winrate (bb/100)
Сначала выводит минусовые руки, затем плюсовые.
"""

import sqlite3
from collections import defaultdict
from pathlib import Path

DB_PATH = Path("db/bbline.sqlite")


def fetch_hero_cards():
    """Возвращает список кортежей (card1, card2, suited, won_bb)."""
    if not DB_PATH.exists():
        print("❌ База не найдена – сначала запусти парсер.")
        return []

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT hc.card1, hc.card2, hc.suited, p.won_bb
          FROM hero_cards  AS hc
          JOIN players     AS p  ON p.hand_id = hc.hand_id
         WHERE p.player_id = 'Hero'
        """
    )

    rows = cur.fetchall()
    conn.close()
    return rows


def normalize(card1: str, card2: str, suited: int) -> str:
    """Нормализует запись руки (A2s, TJo и т.п.)."""
    order = "23456789TJQKA"
    r1, r2 = card1[0], card2[0]

    # старшая карта первой
    if order.index(r1) < order.index(r2):
        r1, r2 = r2, r1

    return f"{r1}{r2}{'s' if suited else 'o'}"


def build_stats(rows):
    """Группирует данные по рукам и считает сумму/частоту."""
    stats = defaultdict(lambda: {"count": 0, "bb": 0.0})
    for c1, c2, suited, won_bb in rows:
        hand = normalize(c1, c2, suited)
        stats[hand]["count"] += 1
        stats[hand]["bb"] += won_bb or 0.0
    return stats


def print_table(title, items):
    """Красивый вывод таблицы."""
    if not items:
        print(f"🔸 {title}: нет данных\n")
        return

    print(f"\n🔸 {title}")
    print(f"{'Hand':<5} | {'Count':<5} | {'Total BB':<9} | {'bb/100':<8}")
    print("-" * 38)
    for hand, d in items:
        cnt, bb = d["count"], d["bb"]
        bb100 = (bb / cnt) * 100 if cnt else 0
        print(f"{hand:<5} | {cnt:<5} | {bb:<9.2f} | {bb100:<8.2f}")
    print("-" * 38 + "\n")


def main():
    rows = fetch_hero_cards()
    if not rows:
        print("😓 У Hero пока нет сыгранных рук.")
        return

    stats = build_stats(rows)

    minus = [(h, d) for h, d in stats.items() if d["bb"] < 0]
    plus  = [(h, d) for h, d in stats.items() if d["bb"] >= 0]

    # сортировка: сначала по убыванию убытка/прибыли, потом по частоте
    minus.sort(key=lambda x: (x[1]["bb"], -x[1]["count"]))  # самый большой минус сверху
    plus.sort(key=lambda x: (-x[1]["bb"], -x[1]["count"]))  # самый большой плюс сверху

    print_table("Убыточные руки", minus)
    print_table("Прибыльные руки", plus)


if __name__ == "__main__":
    main()

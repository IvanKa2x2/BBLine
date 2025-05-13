"""
BBLine – итоговый отчёт Hero
‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
Выводит:
  1. Общий результат (hands, BB, bb/100)
  2. Net‑BB по позициям
  3. Net‑BB по префлоп‑действиям
  4. Табличку динамики стека (hand_id → end_stack_bb)
"""

import sqlite3
from collections import defaultdict

DB_PATH = "db/bbline.sqlite"

def fetch(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(query, params).fetchall()


def overall():
    rows = fetch("""
        SELECT COUNT(DISTINCT hand_id), SUM(net_bb)
        FROM players
        WHERE player_id LIKE '%Hero%'
    """)
    hands, net = rows[0]
    bb100 = (net / hands) * 100 if hands else 0
    print(f"🧮  Hero сыграл: {hands} рук | Итог: {net:+.2f} BB | {bb100:+.2f} bb/100\n")


def by_position():
    rows = fetch("""
        SELECT player_pos, COUNT(*), SUM(net_bb)
        FROM players
        WHERE player_id LIKE '%Hero%'
        GROUP BY player_pos
    """)
    print("📌  Net‑BB по позициям")
    print(f"{'Pos':<5} | {'Hands':<5} | {'Net BB':<8} | {'bb/100':<8}")
    print("-"*34)
    for pos, cnt, net in rows:
        bb100 = (net / cnt) * 100 if cnt else 0
        print(f"{pos:<5} | {cnt:<5} | {net:+8.2f} | {bb100:+8.2f}")
    print()


def by_action():
    rows = fetch("""
        SELECT preflop_action, COUNT(*), SUM(net_bb)
        FROM players
        WHERE player_id LIKE '%Hero%' AND preflop_action IS NOT NULL
        GROUP BY preflop_action
    """)
    print("🎲  Net‑BB по префлоп‑действию")
    print(f"{'Action':<8} | {'Hands':<5} | {'Net BB':<8} | {'bb/100':<8}")
    print("-"*38)
    for act, cnt, net in rows:
        bb100 = (net / cnt) * 100 if cnt else 0
        print(f"{act:<8} | {cnt:<5} | {net:+8.2f} | {bb100:+8.2f}")
    print()


def stack_timeline(limit=15):
    rows = fetch("""
        SELECT h.date_ts, p.hand_id, p.end_stack_bb
        FROM players p
        JOIN hands h USING(hand_id)
        WHERE p.player_id LIKE '%Hero%'
        ORDER BY h.date_ts
    """)
    print(f"📈  Динамика стека (последние {limit} рук)")
    print(f"{'hand_id':<12} | {'end_stack_bb':>12}")
    print("-"*27)
    for _, hand_id, stack in rows[-limit:]:
        print(f"{hand_id:<12} | {stack:>12.2f}")
    print()


if __name__ == "__main__":
    overall()
    by_position()
    by_action()
    stack_timeline()

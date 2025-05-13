# analysis/street_loss.py
"""
Отчёт: Потери Hero по улицам (Preflop / Flop / Turn / River)
"""

import sqlite3
from collections import defaultdict

DB_PATH = "db/bbline.sqlite"

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Выбираем действия только Hero
    query = """
        SELECT a.street, a.action, a.amount_bb
        FROM actions a
        JOIN players p ON a.hand_id = p.hand_id AND a.seat = p.seat
        WHERE p.player_id = 'Hero'
    """
    rows = c.execute(query).fetchall()
    conn.close()

    if not rows:
        print("😓 Нет данных по Hero.")
        return

    street_names = {"P": "Preflop", "F": "Flop", "T": "Turn", "R": "River"}
    street_totals = defaultdict(float)

    for street, action, amount in rows:
        if action in ("call", "bet", "raise"):
            street_totals[street] += amount  # учитываем вложенные BB

    print(f"{'Street':<8} | {'Invested BB':<12}")
    print("-" * 24)
    for code in "PFTR":
        name = street_names[code]
        bb = street_totals.get(code, 0.0)
        print(f"{name:<8} | {bb:<12.2f}")

    total = sum(street_totals.values())
    print("-" * 24)
    print(f"{'ИТОГО':<8} | {total:<12.2f}")

if __name__ == "__main__":
    main()

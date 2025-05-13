# analysis/hands_by_position.py
"""
Отчёт: Руки Hero по позициям (BB, winrate)
"""

import sqlite3
from collections import defaultdict

DB_PATH = "db/bbline.sqlite"

def normalize(card1, card2, suited):
    """A♠ K♣ → AKs / AKo"""
    order = "23456789TJQKA"
    r1, r2 = card1[0], card2[0]
    if order.index(r1) < order.index(r2):
        r1, r2 = r2, r1
    return f"{r1}{r2}{'s' if suited else 'o'}"

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = """
        SELECT hc.card1, hc.card2, hc.suited, p.player_pos, p.won_bb
        FROM hero_cards hc
        JOIN players p ON hc.hand_id = p.hand_id
        WHERE p.player_id = 'Hero'
    """
    rows = c.execute(query).fetchall()
    conn.close()

    if not rows:
        print("😓 Нет данных по Hero.")
        return

    stats = defaultdict(lambda: {"count": 0, "bb": 0.0})

    for c1, c2, suited, pos, won in rows:
        if not pos:
            continue  # пропускаем если нет позиции
        hand = normalize(c1, c2, suited)
        key = (hand, pos)
        stats[key]["count"] += 1
        stats[key]["bb"] += won or 0.0

    print(f"{'Hand':<5} | {'Pos':<5} | {'Count':<5} | {'BB':<7} | {'bb/100':<8}")
    print("-" * 40)
    for (hand, pos), d in sorted(stats.items(), key=lambda x: (-x[1]['count'], x[0])):
        count = d["count"]
        bb = d["bb"]
        bb100 = (bb / count) * 100 if count else 0
        print(f"{hand:<5} | {pos:<5} | {count:<5} | {bb:<7.2f} | {bb100:<8.2f}")

if __name__ == "__main__":
    main()

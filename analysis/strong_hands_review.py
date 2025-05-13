# analysis/strong_hands_review.py
"""
Отчёт: Сильные руки Hero (AK, AQ, JJ и пр.)
"""

import sqlite3
from collections import defaultdict

DB_PATH = "db/bbline.sqlite"

# Только эти руки отслеживаем
TRACKED_HANDS = {"AKs", "AKo", "AQs", "AQo", "AJs", "AJo", "KQs", "JJ", "TT", "QQ", "KK", "AA"}

def normalize(card1, card2, suited):
    order = "23456789TJQKA"
    r1, r2 = card1[0], card2[0]
    if order.index(r1) < order.index(r2):
        r1, r2 = r2, r1
    combo = f"{r1}{r2}"
    return combo + ("s" if suited else "o") if combo not in ["AA", "KK", "QQ", "JJ", "TT"] else combo

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = """
        SELECT hc.hand_id, hc.card1, hc.card2, hc.suited, p.won_bb
        FROM hero_cards hc
        JOIN players p ON hc.hand_id = p.hand_id
        WHERE p.player_id = 'Hero'
    """
    hands = c.execute(query).fetchall()

    # Дополнительно: собираем folded на флопе
    action_rows = c.execute("""
        SELECT hand_id
        FROM actions
        WHERE street = 'F' AND action = 'fold'
    """).fetchall()
    folded_flop_ids = {row[0] for row in action_rows}

    conn.close()

    stats = defaultdict(lambda: {"count": 0, "bb": 0.0, "fold_flop": 0})

    for hand_id, c1, c2, suited, won in hands:
        hand = normalize(c1, c2, suited)
        if hand not in TRACKED_HANDS:
            continue
        stats[hand]["count"] += 1
        stats[hand]["bb"] += won or 0.0
        if hand_id in folded_flop_ids:
            stats[hand]["fold_flop"] += 1

    print(f"{'Hand':<5} | {'Count':<5} | {'BB':<7} | {'bb/100':<8} | {'FoldFlop %':<10}")
    print("-" * 50)
    for hand, d in sorted(stats.items(), key=lambda x: -x[1]["count"]):
        count = d["count"]
        bb = d["bb"]
        bb100 = (bb / count) * 100 if count else 0
        fold_rate = (d["fold_flop"] / count) * 100 if count else 0
        print(f"{hand:<5} | {count:<5} | {bb:<7.2f} | {bb100:<8.2f} | {fold_rate:<10.1f}")

if __name__ == "__main__":
    main()

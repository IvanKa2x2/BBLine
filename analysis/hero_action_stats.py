# analysis/hero_action_stats.py
"""
Hero — префлоп-действия и результат (winrate по action)
"""

import sqlite3
from collections import defaultdict

DB_PATH = "db/bbline.sqlite"

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Префлоп-действия Hero
    query = """
        SELECT a.hand_id, a.action, a.amount_bb
        FROM actions a
        JOIN players p ON a.hand_id = p.hand_id AND a.seat = p.seat
        WHERE a.street = 'P' AND p.player_id = 'Hero'
    """
    actions = c.execute(query).fetchall()

    # Выгружаем выигрыш по каждой раздаче Hero
    win_query = """
        SELECT hand_id, won_bb
        FROM players
        WHERE player_id = 'Hero'
    """
    wins = dict(c.execute(win_query).fetchall())
    conn.close()

    stats = defaultdict(lambda: {"count": 0, "bb": 0.0})

    for hand_id, action, _ in actions:
        stats[action]["count"] += 1
        stats[action]["bb"] += wins.get(hand_id, 0.0)

    print(f"{'Action':<8} | {'Count':<5} | {'Total BB':<9} | {'bb/100':<8}")
    print("-" * 40)

    for action, d in stats.items():
        count = d["count"]
        bb = d["bb"]
        bb100 = (bb / count) * 100 if count else 0
        print(f"{action:<8} | {count:<5} | {bb:<9.2f} | {bb100:<8.2f}")

    if not stats:
        print("😓 Нет префлоп-действий Hero в базе.")

if __name__ == "__main__":
    main()

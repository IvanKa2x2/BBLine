# analysis/hero_stats.py

import sqlite3

DB_PATH = "db/bbline.sqlite"

def calculate_hero_winrate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = """
        SELECT
            COUNT(DISTINCT hand_id) AS total_hands,
            SUM(won_bb) AS total_bb
        FROM players
        WHERE player_id = 'Hero'
    """

    result = c.execute(query).fetchone()
    total_hands = result[0] or 0
    total_bb = result[1] or 0.0

    conn.close()

    if total_hands == 0:
        print("❌ Нет данных по Hero")
        return

    winrate = (total_bb / total_hands) * 100
    print(f"🧠 Hero сыграл {total_hands} рук")
    print(f"📈 Общий результат: {total_bb:.2f} BB")
    print(f"🔥 Winrate: {winrate:.2f} bb/100")

def hero_winrate_by_position():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = """
        SELECT hero_pos, 
               COUNT(*) AS hands,
               SUM(won_bb) AS total_bb,
               ROUND((SUM(won_bb) * 100.0 / COUNT()), 2) AS bb_per_100
        FROM players
        JOIN hands USING(hand_id)
        WHERE player_id = 'Hero'
        GROUP BY hero_pos
        ORDER BY hands DESC
    """

    rows = c.execute(query).fetchall()
    conn.close()

    if not rows:
        print("❌ Нет данных по позициям")
        return

    print("\n📍 Winrate по позициям:")
    print(f"{'Позиция':<8} | {'Руки':<5} | {'BB':<6} | {'bb/100':<8}")
    print("-" * 32)
    for row in rows:
        pos, hands, bb, bb100 = row
        pos = pos if pos is not None else "?"
        bb = bb if bb is not None else 0.0
        bb100 = bb100 if bb100 is not None else 0.0
        print(f"{pos:<8} | {hands:<5} | {bb:<6.2f} | {bb100:<8.2f}")


if __name__ == "__main__":
    calculate_hero_winrate()
    hero_winrate_by_position()

# analysis/summary.py единый отчет по Hero (винрейт, позиции, действия, динамика)
from utils import fetchall, print_table

def summary():
    stats = fetchall("""
        SELECT COUNT(DISTINCT hand_id) AS hands, SUM(net_bb) AS net_bb
        FROM players WHERE player_id LIKE '%Hero%'
    """)[0]
    if not stats or stats['hands'] == 0:
        print("❌ Нет данных по Hero")
        return
    hands, net_bb = stats['hands'], stats['net_bb']
    winrate = (net_bb / hands) * 100 if hands else 0
    print(f"\n🧠 Hero сыграл {hands} рук\n📈 Итог: {net_bb:+.2f} BB | {winrate:+.2f} bb/100")

def by_position():
    rows = fetchall("""
        SELECT h.hero_pos, COUNT(*) AS hands, SUM(p.net_bb) AS net_bb,
               ROUND((SUM(p.net_bb)*100.0/COUNT()),2) AS bb100
        FROM players p
        JOIN hands h ON h.hand_id = p.hand_id
        WHERE p.player_id LIKE '%Hero%'
        GROUP BY h.hero_pos
    """)
    print_table("Winrate по позициям",
                ["Позиция", "Руки", "BB", "bb/100"],
                [(r["hero_pos"], r["hands"], r["net_bb"], r["bb100"]) for r in rows])

def by_action():
    rows = fetchall("""
        SELECT preflop_action, COUNT(*) AS hands, SUM(net_bb) AS net_bb,
               ROUND((SUM(net_bb)*100.0/COUNT()),2) AS bb100
        FROM players
        WHERE player_id LIKE '%Hero%' AND preflop_action IS NOT NULL
        GROUP BY preflop_action
    """)
    print_table("Net-BB по префлоп-действиям",
                ["Action", "Hands", "Net BB", "bb/100"],
                [(r["preflop_action"], r["hands"], r["net_bb"], r["bb100"]) for r in rows])

def stack_timeline(limit=15):
    rows = fetchall("""
        SELECT h.date_ts, p.hand_id, p.end_stack_bb
        FROM players p
        JOIN hands h ON h.hand_id = p.hand_id
        WHERE p.player_id LIKE '%Hero%'
        ORDER BY h.date_ts
    """)
    print_table(f"Динамика стека (последние {limit} рук)",
                ["Hand_id", "Stack_bb"],
                [(r["hand_id"], r["end_stack_bb"]) for r in rows[-limit:]])

if __name__ == "__main__":
    summary()
    by_position()
    by_action()
    stack_timeline()

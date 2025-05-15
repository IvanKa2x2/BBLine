# analysis/hands_stats.py анализ по рукам (AJo, TT, AKs...)
from utils import fetchall, normalize, print_table
from collections import defaultdict

def main():
    rows = fetchall("""
        SELECT hc.card1, hc.card2, hc.suited, p.won_bb
        FROM hero_cards hc
        JOIN players p ON hc.hand_id = p.hand_id
        WHERE p.player_id = 'Hero'
    """)
    stats = defaultdict(lambda: {"count": 0, "bb": 0.0})
    for c1, c2, suited, bb in rows:
        hand = normalize(c1, c2, suited)
        stats[hand]["count"] += 1
        stats[hand]["bb"] += bb or 0.0
    items = sorted(stats.items(), key=lambda x: (x[1]["bb"], -x[1]["count"]))  # по убыванию результата
    print_table("Руки Hero (по убыточности)",
                ["Hand", "Count", "Total BB", "bb/100"],
                [(h, d["count"], d["bb"], (d["bb"]/d["count"]*100 if d["count"] else 0)) for h, d in items])

if __name__ == "__main__":
    main()

# analysis/strong_hands.py только сильные руки
from utils import fetchall, normalize, print_table
from collections import defaultdict

TRACKED = {"AKs", "AKo", "AQs", "AQo", "AJs", "AJo", "KQs", "JJ", "TT", "QQ", "KK", "AA"}

def main():
    rows = fetchall("""
        SELECT hc.hand_id, hc.card1, hc.card2, hc.suited, p.won_bb
        FROM hero_cards hc
        JOIN players p ON hc.hand_id = p.hand_id
        WHERE p.player_id = 'Hero'
    """)
    stats = defaultdict(lambda: {"count": 0, "bb": 0.0, "fold_flop": 0})
    # folded on flop
    folded_ids = {r["hand_id"] for r in fetchall("""
        SELECT hand_id FROM actions WHERE street='F' AND action='fold'
    """)}
    for hand_id, c1, c2, suited, bb in rows:
        hand = normalize(c1, c2, suited)
        if hand not in TRACKED: continue
        stats[hand]["count"] += 1
        stats[hand]["bb"] += bb or 0.0
        if hand_id in folded_ids:
            stats[hand]["fold_flop"] += 1
    items = sorted(stats.items(), key=lambda x: -x[1]["count"])
    print_table("Сильные руки Hero",
        ["Hand", "Count", "Total BB", "bb/100", "FoldFlop%"],
        [(h, d["count"], d["bb"], (d["bb"]/d["count"]*100 if d["count"] else 0),
          (d["fold_flop"]/d["count"]*100 if d["count"] else 0)) for h, d in items])

if __name__ == "__main__":
    main()

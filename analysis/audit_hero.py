# analysis/audit_hero.py
import sqlite3
from collections import Counter, defaultdict
import os

DB_PATH = "db/bbline.sqlite"

def fetchall(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(query, params).fetchall()
def get_hero_stats():
    rows = fetchall("""
        SELECT preflop_action, street, action
        FROM players p
        JOIN actions a ON p.hand_id = a.hand_id AND p.seat = a.seat
        WHERE p.player_id LIKE '%Hero%'
    """)
    
    total = 0
    vpip = 0
    pfr  = 0
    cbet_total = 0
    cbet_done  = 0

    for r in rows:
        if r["street"] == "P":
            total += 1
            if r["preflop_action"] in ("call", "raise"):
                vpip += 1
            if r["preflop_action"] == "raise":
                pfr += 1
        if r["street"] == "F":
            cbet_total += 1
            if r["action"] in ("bet", "raise"):
                cbet_done += 1

    return {
        "VPIP": round(100 * vpip / total, 1),
        "PFR":  round(100 * pfr / total, 1),
        "CBet (Flop)": round(100 * cbet_done / cbet_total, 1) if cbet_total else 0,
    }


def net_bb_by_position():
    rows = fetchall("""
        SELECT h.hero_pos, p.net_bb
        FROM players p
        JOIN hands h ON h.hand_id = p.hand_id
        WHERE p.player_id LIKE '%Hero%'
    """)
    pos_stats = defaultdict(float)
    for row in rows:
        pos_stats[row["hero_pos"]] += row["net_bb"]
    return pos_stats


def top_negative_hands(limit=10):
    rows = fetchall("""
        SELECT p.hand_id, net_bb, hero_pos, h.date_ts
        FROM players p
        JOIN hands h ON h.hand_id = p.hand_id
        WHERE player_id LIKE '%Hero%' AND net_bb < 0
        ORDER BY net_bb ASC
        LIMIT ?
    """, (limit,))
    return rows

def count_flags():
    rows = fetchall("SELECT * FROM flags")
    total = len(rows)
    flags_count = Counter()
    for row in rows:
        for key in ("missed_cbet", "lost_stack", "cooler", "tilt_tag"):
            if row[key]:
                flags_count[key] += 1
    return flags_count, total

def run():
    print("📊 Анализ Hero игры:")
    print_stats_vs_norm()
    # Убыточные позиции
    pos_net = net_bb_by_position()
    print("\n🪑 net_bb по позициям:")
    for pos, net in sorted(pos_net.items(), key=lambda x: x[1]):
        print(f"  {pos:>3} → {net:6.1f} bb")

    # Частые флаги
    flags, total = count_flags()
    print("\n🚩 Частота флагов:")
    for flag, count in flags.items():
        print(f"  {flag:<13}: {count:>3} / {total} рук ({count/total*100:.1f}%)")

    # Топ 10 проигрышных раздач
    print("\n💸 Топ-10 самых убыточных рук:")
    for r in top_negative_hands():
        print(f"  {r['hand_id']} ({r['hero_pos']}) → {r['net_bb']} bb")

def print_stats_vs_norm():
    stats = get_hero_stats()
    print("\n📈 Hero статы vs нормы:")
    norms = {
        "VPIP": (22, 28),
        "PFR": (17, 23),
        "CBet (Flop)": (65, 75),
    }

    for stat, value in stats.items():
        low, high = norms.get(stat, (0, 100))
        mark = "✅" if low <= value <= high else "⚠️" if abs(value - (low+high)/2) <= 5 else "❌"
        print(f"  {stat:<12}: {value:>5.1f}%  | норма: {low}-{high}% → {mark}")




if __name__ == "__main__":
    run()

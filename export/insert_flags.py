# export/insert_flags.py
import sqlite3
from collections import deque

DB_PATH = "db/bbline.sqlite"

def detect_missed_cbet(c, hand_id, hero_seat):
    """Hero был PFR, но на флопе ни разу не бетнул / не рейзнул."""
    # Hero PFR?
    c.execute("""
        SELECT preflop_action FROM players
        WHERE hand_id = ? AND seat = ?
    """, (hand_id, hero_seat))
    row = c.fetchone()
    if not row or row[0] not in ("raise", "bet"):
        return False

    # Искали bet/raise на FLOP
    c.execute("""
        SELECT 1 FROM actions
        WHERE hand_id = ? AND street = 'F'
              AND seat = ? AND action IN ('bet','raise')
        LIMIT 1
    """, (hand_id, hero_seat))
    return c.fetchone() is None  # True → бетов нет ⇒ мисс-CBET

def detect_lost_stack(end_stack_bb, net_bb):
    return end_stack_bb <= 0.5 or net_bb <= -50

def detect_cooler(lost_stack, invested_bb):
    return lost_stack and invested_bb >= 50

def mark_tilt_tags(hero_hands):
    """
    Помечаем tilt_tag, если подряд ≥3 рук с отрицательным net_bb.
    hero_hands = list[(hand_id, date_ts, net_bb)]
    """
    tilt_hand_ids = set()
    streak = deque()  # (hand_id, net_bb)
    for hand_id, _, net in sorted(hero_hands, key=lambda x: x[1]):  # по времени
        streak.append((hand_id, net))
        if len(streak) > 3:
            streak.popleft()
        if len(streak) == 3 and all(net_bb < 0 for _, net_bb in streak):
            tilt_hand_ids.update(h for h, _ in streak)
    return tilt_hand_ids

def run():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Сначала собираем все hero-раздачи (hand_id, date_ts, net_bb, …)
    c.execute("""
        SELECT p.hand_id, h.date_ts, p.seat,
               p.end_stack_bb, p.net_bb, p.invested_bb
        FROM players p
        JOIN hands h ON h.hand_id = p.hand_id
        WHERE p.player_id LIKE '%Hero%'
    """)
    hero_rows = c.fetchall()

    # Для tilt-детектора
    hero_timeline = [(hid, ts, net_bb) for hid, ts, _, _, net_bb, _ in hero_rows]
    tilt_ids = mark_tilt_tags(hero_timeline)

    for hand_id, _, seat, end_stack, net_bb, invested_bb in hero_rows:
        missed_cbet = detect_missed_cbet(c, hand_id, seat)
        lost_stack   = detect_lost_stack(end_stack, net_bb)
        cooler       = detect_cooler(lost_stack, invested_bb)
        tilt_tag     = hand_id in tilt_ids

        c.execute("""
            INSERT INTO flags (hand_id, missed_cbet, lost_stack, cooler, tilt_tag)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(hand_id) DO UPDATE SET
                missed_cbet=excluded.missed_cbet,
                lost_stack =excluded.lost_stack,
                cooler     =excluded.cooler,
                tilt_tag   =excluded.tilt_tag
        """, (hand_id, missed_cbet, lost_stack, cooler, tilt_tag))

    conn.commit()
    conn.close()
    print("✅ flags заполнены / обновлены.")

if __name__ == "__main__":
    run()

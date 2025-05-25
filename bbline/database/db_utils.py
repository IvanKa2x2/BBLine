import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("bbline.sqlite")


def insert_hand(hand):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # 1. hands
    cur.execute(
        """
        INSERT OR IGNORE INTO hands (
            hand_id, site, game_type, limit_bb, datetime_utc,
            button_seat, hero_seat, hero_name, hero_cards,
            board, hero_invested, rake, jackpot, final_pot,
            hero_net, hero_showdown
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            hand["hand_id"],
            hand["site"],
            hand["game_type"],
            hand["limit_bb"],
            hand["datetime_utc"],
            hand["button_seat"],
            hand["hero_seat"],
            hand["hero_name"],
            hand["hero_cards"],
            hand["board"],
            hand["hero_invested"],  # ← добавили
            hand["rake"],
            hand["jackpot"],
            hand["final_pot"],
            hand.get("hero_net"),
            hand.get("hero_showdown", 0),
        ),
    )

    # 2. seats
    for seat in hand["seats"]:
        cur.execute(
            """
            INSERT OR IGNORE INTO seats (hand_id, seat_no, player_id, chips)
            VALUES (?, ?, ?, ?)
        """,
            (hand["hand_id"], seat["seat_no"], seat["player_id"], seat["chips"]),
        )

    # 3. actions
    for action in hand["actions"]:
        cur.execute(
            """
            INSERT INTO actions (hand_id, street, order_no, seat_no, act, amount, allin)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                hand["hand_id"],
                action["street"],
                action["order_no"],
                action["seat_no"],
                action["act"],
                action.get("amount"),
                action.get("allin", 0),
            ),
        )
    cur.execute("PRAGMA foreign_keys = ON;")
    # 4. showdowns
    for sd in hand.get("showdowns", []):
        cur.execute(
            """
            INSERT OR IGNORE INTO showdowns (hand_id, seat_no, cards, won)
            VALUES (?, ?, ?, ?)
            """,
            (
                hand["hand_id"],
                sd["seat_no"],
                sd["cards"],
                sd.get("won", 0.0),  # ← ставим 0.0 вместо None
            ),
        )

    conn.commit()
    conn.close()

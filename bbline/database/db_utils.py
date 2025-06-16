# db_utils.py

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("bbline.sqlite")


def insert_hand(hand: dict, cx: sqlite3.Connection | None = None) -> bool:
    """True -> вставили новую руку, False -> дубликат"""
    own_conn = cx is None
    if own_conn:
        cx = sqlite3.connect(DB_PATH)
    cur = cx.cursor()

    cur.execute(
        """
        INSERT OR IGNORE INTO hands (
            hand_id, site, game_type, limit_bb, datetime_utc,
            button_seat, hero_seat, hero_name, hero_cards, board,
            hero_invested, hero_collected, hero_rake, rake, jackpot,
            final_pot, hero_net, hero_showdown
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
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
            hand["hero_invested"],
            hand["hero_collected"],
            hand["hero_rake"],
            hand["rake"],
            hand["jackpot"],
            hand["final_pot"],
            hand["hero_net"],
            hand["hero_showdown"],
        ),
    )
    inserted = cur.rowcount == 1  # <-- золото
    if inserted:
        # пишем в связанные таблицы seats, actions, collected, showdowns
        for seat in hand["seats"]:
            cur.execute(
                "INSERT OR REPLACE INTO seats (hand_id, seat_no, player_id, chips) VALUES (?,?,?,?);",
                (hand["hand_id"], seat["seat_no"], seat["player_id"], seat["chips"]),
            )
        for action in hand["actions"]:
            cur.execute(
                "INSERT INTO actions (hand_id, street, order_no, seat_no, act, amount, allin) VALUES (?,?,?,?,?,?,?);",
                (
                    hand["hand_id"],
                    action["street"],
                    action["order_no"],
                    action["seat_no"],
                    action["act"],
                    action["amount"],
                    action["allin"],
                ),
            )
        for collected_row in hand["collected_rows"]:
            cur.execute(
                "INSERT INTO collected (hand_id, seat_no, amount) VALUES (?,?,?);",
                (hand["hand_id"], collected_row["seat_no"], collected_row["amount"]),
            )
        for showdown in hand["showdowns"]:
            cur.execute(
                "INSERT INTO showdowns (hand_id, seat_no, player_id, cards, is_winner, won_amount) VALUES (?,?,?,?,?,?);",
                (
                    hand["hand_id"],
                    showdown["seat_no"],
                    showdown["player_id"],
                    showdown["cards"],
                    showdown["is_winner"],
                    showdown["won_amount"],
                ),
            )

    if own_conn:
        cx.commit()
        cx.close()
    return inserted

# bbline/analysis/rebuild_computed.py
"""
Пересчитывает флаги в computed_stats для КАЖДОЙ руки.
Запуск:
    python -m bbline.analysis.rebuild_computed
"""

import sqlite3
from pathlib import Path
from collections import defaultdict

DB = Path(__file__).resolve().parents[1] / "database" / "bbline.sqlite"
VPIP = {"CALL", "BET", "RAISE"}
RAISE = {"RAISE"}


def rebuild():
    cx = sqlite3.connect(DB)
    cx.row_factory = sqlite3.Row
    cur = cx.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    cur.execute("DELETE FROM computed_stats;")

    # Берём все руки -> потом отдельно действия по каждой
    hands = cur.execute(
        """
        SELECT hand_id, hero_seat, hero_net, hero_showdown
        FROM   hands
    """
    ).fetchall()

    for h in hands:
        hand_id = h["hand_id"]
        hero_seat = h["hero_seat"]
        hero_net = h["hero_net"] or 0  # None => 0
        hero_showdown = h["hero_showdown"]

        # дефолтные флаги
        st = defaultdict(int)
        st["wtsd"] = int(bool(hero_showdown))
        st["wsd"] = int(hero_showdown and hero_net > 0)
        st["wwsf"] = int((hero_net > 0) and not hero_showdown)

        # тянем действия только этой руки
        acts = cur.execute(
            """
            SELECT street, seat_no, act
            FROM   actions
            WHERE  hand_id = ?
            ORDER  BY order_no
        """,
            (hand_id,),
        ).fetchall()

        preflop_raises = 0
        hero_raised_pf = False
        hero_faced_3b = False
        flop_bet_seen = False

        for a in acts:
            street, seat, act = a["street"], a["seat_no"], a["act"]

            # PREFLOP ---------------------------------
            if street == "PREFLOP":
                if act in VPIP and seat == hero_seat:
                    st["vpip"] = 1
                if act in RAISE:
                    preflop_raises += 1
                    if seat == hero_seat:
                        if preflop_raises == 1:
                            st["pfr"] = 1
                            hero_raised_pf = True
                        elif preflop_raises == 2:
                            st["threebet"] = 1
                    else:
                        if hero_raised_pf:
                            hero_faced_3b = True
                if act == "FOLD" and seat == hero_seat and hero_faced_3b:
                    st["fold_to_3b"] = 1

            # FLOP ------------------------------------
            if street == "FLOP":
                if act == "BET" and not flop_bet_seen:
                    flop_bet_seen = True
                    if hero_raised_pf and seat == hero_seat:
                        st["cbet_flop"] = 1
                if act == "FOLD" and seat == hero_seat and flop_bet_seen:
                    st["fold_to_cbet"] = 1

        cur.execute(
            """
          INSERT OR REPLACE INTO computed_stats (
              hand_id, vpip, pfr, threebet,
              fold_to_3b, cbet_flop, fold_to_cbet,
              wwsf, wt_sd, w_sd
          ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
            (
                hand_id,
                st["vpip"],
                st["pfr"],
                st["threebet"],
                st["fold_to_3b"],
                st["cbet_flop"],
                st["fold_to_cbet"],
                st["wwsf"],
                st["wtsd"],
                st["wsd"],
            ),
        )

    cx.commit()
    cx.close()
    print("✅ computed_stats: {} рук обновлено".format(len(hands)))


if __name__ == "__main__":
    rebuild()

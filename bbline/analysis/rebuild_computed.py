# bbline/analysis/rebuild_computed.py
"""
Пересчитывает флаги в computed_stats для КАЖДОЙ руки + обновляет hero_invested, hero_rake, net_bb.
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

    # Берём все руки
    hands = cur.execute(
        """
        SELECT hand_id, hero_seat, hero_net, hero_showdown, hero_invested, rake, final_pot
        FROM   hands
    """
    ).fetchall()

    for h in hands:
        hand_id = h["hand_id"]
        hero_seat = h["hero_seat"]
        hero_net = h["hero_net"]
        hero_showdown = h["hero_showdown"]
        hero_in = h["hero_invested"] or 0
        rake_tot = h["rake"] or 0
        final_pot = h["final_pot"] or 0

        # bb для этой руки (1 строка)
        bb_row = cur.execute("SELECT limit_bb FROM hands WHERE hand_id = ?", (hand_id,)).fetchone()
        bb = bb_row[0] if bb_row and bb_row[0] else 0.02  # fallback на 0.02

        # Доля рейка героя (safe)
        hero_rake = rake_tot * (hero_in / final_pot) if final_pot else 0

        # ---- КОРРЕКТНАЯ прибыль ----
        profit = (hero_net if hero_net is not None else 0) - hero_in
        net_bb = profit / bb if bb else 0

        # Сразу обновим hands!
        cur.execute(
            """
            UPDATE hands
               SET hero_rake = ?,
                   net_bb    = ?
             WHERE hand_id   = ?;
            """,
            (hero_rake, net_bb, hand_id),
        )

        # дефолтные флаги
        st = defaultdict(int)
        st["wtsd"] = int(bool(hero_showdown))
        st["wsd"] = int(hero_showdown and (hero_net or 0) > 0)
        st["wwsf"] = int(((hero_net or 0) > 0) and not hero_showdown)

        # действия только этой руки
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
                        st["pfr"] = 1  # ← флаг ставится ВСЕГДА, раз герой рейзит
                        if preflop_raises == 1:  # впервые в раздаче → open/iso-raise
                            hero_raised_pf = True
                        elif preflop_raises == 2:  # вторая волна рейзов → 3-бет
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
    print("✅ computed_stats и winrate обновлены для {} рук".format(len(hands)))


if __name__ == "__main__":
    rebuild()

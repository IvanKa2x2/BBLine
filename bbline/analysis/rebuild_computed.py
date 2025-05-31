# bbline/analysis/rebuild_computed.py
"""
Пересчитывает computed_stats + hero_rake, net_bb в 'hands'.
Запуск:
    python -m bbline.analysis.rebuild_computed
"""

import sqlite3
from pathlib import Path
from collections import defaultdict

DB = Path(__file__).resolve().parents[1] / "database" / "bbline.sqlite"

VPIP = {"CALL", "BET", "RAISE"}
RAISE = {"RAISE"}


def rebuild() -> None:
    with sqlite3.connect(DB) as cx:
        cx.row_factory = sqlite3.Row
        cur = cx.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")

        # чистим computed_stats
        cur.execute("DELETE FROM computed_stats;")

        # забираем всё нужное одним запросом
        hands = cur.execute(
            """
            SELECT  hand_id, hero_seat, hero_net, hero_showdown,
                    hero_invested, rake, final_pot, limit_bb
            FROM    hands;
        """
        ).fetchall()

        for h in hands:
            hand_id = h["hand_id"]
            hero_seat = h["hero_seat"]
            hero_net = h["hero_net"] or 0.0
            hero_in = h["hero_invested"] or 0.0
            hero_sd = bool(h["hero_showdown"])
            rake_total = h["rake"] or 0.0
            final_pot = h["final_pot"] or 0.0  # уже после рейка
            bb = h["limit_bb"] or 0.02  # страхуемся

            # --- корректная доля рейка героя ---
            rakeable_pot = final_pot + rake_total  # до вычета
            hero_rake = round(rake_total * (hero_in / rakeable_pot) if rakeable_pot else 0.0, 2)

            # --- чистый профит и winrate ---
            profit = hero_net or 0.0  # hero_net уже «чистый»
            net_bb = round(profit / bb, 4)  # bb > 0 гарантирован
            # обновляем руки
            cur.execute(
                """
                UPDATE hands
                   SET hero_rake = ?,
                       net_bb    = ?
                 WHERE hand_id   = ?;
            """,
                (hero_rake, net_bb, hand_id),
            )

            # ---------------- computed_stats -------------
            st = defaultdict(int)

            # исходы
            st["wtsd"] = int(hero_sd)
            st["wsd"] = int(hero_sd and profit > 0)
            st["wwsf"] = int((profit > 0) and not hero_sd)

            # действия по руке
            acts = cur.execute(
                """
                SELECT street, seat_no, act
                FROM   actions
                WHERE  hand_id = ?
                ORDER  BY order_no;
            """,
                (hand_id,),
            ).fetchall()

            preflop_raises = 0
            hero_raised_pf = False
            hero_faced_3bet = False
            flop_bet_seen = False

            for a in acts:
                street, seat, act = a["street"], a["seat_no"], a["act"]

                # ---------- PREFLOP ----------
                if street == "PREFLOP":
                    if act in VPIP and seat == hero_seat:
                        st["vpip"] = 1

                    if act in RAISE:
                        preflop_raises += 1

                        if seat == hero_seat:  #   действия героя
                            st["pfr"] = 1
                            if preflop_raises == 1:
                                hero_raised_pf = True
                            elif preflop_raises == 2:
                                st["threebet"] = 1
                        else:  #   действия оппа
                            if hero_raised_pf:
                                hero_faced_3bet = True

                    if act == "FOLD" and seat == hero_seat and hero_faced_3bet:
                        st["fold_to_3b"] = 1

                # ---------- FLOP ----------
                if street == "FLOP":
                    if act == "BET" and not flop_bet_seen:
                        flop_bet_seen = True
                        if hero_raised_pf and seat == hero_seat:
                            st["cbet_flop"] = 1
                    if act == "FOLD" and seat == hero_seat and flop_bet_seen:
                        st["fold_to_cbet"] = 1

            # пишем в таблицу
            cur.execute(
                """
                INSERT OR REPLACE INTO computed_stats (
                    hand_id, vpip, pfr, threebet,
                    fold_to_3b, cbet_flop, fold_to_cbet,
                    wwsf, wt_sd, w_sd
                ) VALUES (?,?,?,?,?,?,?,?,?,?);
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

    print(f"✅  пересчитали computed_stats + winrate для {len(hands)} рук")


if __name__ == "__main__":
    rebuild()

"""
replayer/replay_one.py

Лёгкий «консоль + Streamlit» реплеер одной раздачи (Hero‑only).
Запуск (CLI):
    python -m replayer.replay_one HD2268701058  # где HD… – hand_id

Запуск (Streamlit):
    streamlit run replayer/replay_one.py   # появится селектор hand_id

Требования: streamlit (для UI‑режима) + база bbline.sqlite.
"""

from __future__ import annotations

import sqlite3
import sys
from typing import List, Tuple

from bbline.utils import DB_PATH  # Импортируем DB_PATH из utils

# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------


def _fetch_hand(cur: sqlite3.Cursor, hand_id: str):
    hand = cur.execute("SELECT * FROM hands WHERE hand_id = ?", (hand_id,)).fetchone()
    if not hand:
        raise ValueError(f"hand_id {hand_id} not found")
    return hand


def _fetch_actions(cur: sqlite3.Cursor, hand_id: str) -> List[Tuple]:
    return cur.execute(
        """
        SELECT street, order_no, seat_no, act, amount, allin
        FROM   actions
        WHERE  hand_id = ?
        ORDER  BY CASE street
                      WHEN 'PREFLOP' THEN 0 WHEN 'FLOP' THEN 1
                      WHEN 'TURN' THEN 2 WHEN 'RIVER' THEN 3 ELSE 4 END,
                  order_no;
        """,
        (hand_id,),
    ).fetchall()


def _street_color(street: str) -> str:
    return {
        "PREFLOP": "#cccccc",
        "FLOP": "#4caf50",
        "TURN": "#2196f3",
        "RIVER": "#ff9800",
    }.get(street, "white")


# ----------------------------------------------------------------------------
# core printer
# ----------------------------------------------------------------------------


def print_hand(hand, actions):
    print("-" * 60)
    print(f"HandID    : {hand['hand_id']}   ({hand['datetime_utc']})")
    print(f"Limit     : NL${hand['limit_bb']*50:.0f}/{hand['limit_bb']*100:.0f}")
    print(f"Hero cards: {hand['hero_cards']}")
    print(f"Board     : {hand['board'] or '--'}")
    print(f"Final pot : {hand['final_pot'] or 0:.2f}   Profit: {hand['hero_net'] or 0:.2f}$")
    print("-" * 60)

    last_street = None
    for street, order_no, seat_no, act, amount, allin in actions:
        if street != last_street:
            print(f"\n[{street}]")
            last_street = street
        allin_tag = " (all‑in)" if allin else ""
        amt = f" {amount:.2f}$" if amount else ""
        print(f"  Seat {seat_no}: {act}{amt}{allin_tag}")
    print("-" * 60)


# ----------------------------------------------------------------------------
# streamlit UI (callable) - Для использования в main.py
# ----------------------------------------------------------------------------


def display_hand_replay(hand_id: str):
    import streamlit as st  # Импортируем Streamlit здесь, если он нужен

    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        cur = cx.cursor()
        try:
            hand = _fetch_hand(cur, hand_id)
            actions = _fetch_actions(cur, hand_id)
        except ValueError as e:
            st.error(f"Ошибка: {e}")
            return

    st.subheader(
        f"{hand['hand_id']} | {hand['datetime_utc']} | {hand['hero_cards']} -> {hand['board'] or '--'}"
    )
    st.write(f"Профит: **{hand['hero_net'] or 0:.2f}$** | Пот: {hand['final_pot'] or 0:.2f}$")

    for street in ("PREFLOP", "FLOP", "TURN", "RIVER"):
        st.markdown(f"**{street}**", unsafe_allow_html=True)
        street_actions = [a for a in actions if a[0] == street]
        if not street_actions:
            st.write("—")
            continue
        for _, _, seat_no, act, amount, allin in street_actions:
            tag = " (all‑in)" if allin else ""
            amt = f" {amount:.2f}$" if amount else ""
            st.write(f"▶ Seat {seat_no}: {act}{amt}{tag}")


# ----------------------------------------------------------------------------
# main entry
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        # CLI режим
        hand_id = sys.argv[1]
        with sqlite3.connect(DB_PATH) as cx:
            cx.row_factory = sqlite3.Row
            cur = cx.cursor()
            try:
                hand = _fetch_hand(cur, hand_id)
                actions = _fetch_actions(cur, hand_id)
                print_hand(hand, actions)
            except ValueError as e:
                print(f"Ошибка: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        # Запуск Streamlit UI отдельно (для тестирования или прямого использования)
        try:
            import streamlit as st

            st.set_page_config(page_title="Hand Replayer", layout="wide")
            st.title("🂡 Hand Replayer (BBLine)")
            with sqlite3.connect(DB_PATH) as cx:
                cx.row_factory = sqlite3.Row
                cur = cx.cursor()
                ids = [
                    r[0]
                    for r in cur.execute(
                        "SELECT hand_id FROM hands ORDER BY datetime_utc DESC"
                    ).fetchall()
                ]
            selected_hand_id = st.selectbox("Выбери раздачу", ids)
            if selected_hand_id:
                display_hand_replay(selected_hand_id)
            else:
                st.info("Выберите Hand ID для отображения раздачи.")

        except ImportError:
            sys.exit("Установи streamlit или укажи hand_id в аргументах.")

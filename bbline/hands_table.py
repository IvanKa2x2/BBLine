import sqlite3
import pandas as pd
from bbline.utils import get_hand_ids, DB_PATH, _pos_from_seats  # Изменены импорты


def fetch_hands_df(
    date_from: str | None = None,
    date_to: str | None = None,
    limits: list[float] | None = None,
    positions: list[str] | None = None,
) -> pd.DataFrame:
    """Возвращает DataFrame со всеми нужными колонками под UI-таблицу."""
    with sqlite3.connect(DB_PATH) as cx:
        cur = cx.cursor()
        hand_ids = get_hand_ids(cur, date_from, date_to, limits, positions)
        if not hand_ids:
            return pd.DataFrame()

        ph = ",".join("?" * len(hand_ids))
        rows = cur.execute(
            f"""
            SELECT  h.hand_id,
                    SUBSTR(h.datetime_utc, 1, 10)        AS date,
                    h.hero_cards,
                    h.board,
                    h.hero_net          AS profit_usd,
                    h.net_bb            AS profit_bb,
                    h.limit_bb,
                    h.hero_seat, h.button_seat
            FROM    hands h
            WHERE   h.hand_id IN ({ph})
            ORDER BY h.datetime_utc DESC
            """,
            hand_ids,
        ).fetchall()

    df = pd.DataFrame(
        rows,
        columns=[
            "hand_id",
            "date",
            "hole_cards",
            "board",
            "$",
            "bb",
            "limit_bb",
            "hero_seat",
            "button_seat",
        ],
    )
    # маппинг позиции
    df["pos"] = df.apply(
        lambda r: _pos_from_seats(int(r["hero_seat"]), int(r["button_seat"])), axis=1
    )
    # косметика/порядок
    df = df[["date", "hand_id", "hole_cards", "board", "$", "bb", "pos", "limit_bb"]].rename(
        columns={
            "date": "Дата",
            "hand_id": "HandID",
            "hole_cards": "Карты",
            "board": "Борд",
            "$": "Профит $",
            "bb": "Профит bb",
            "pos": "Позиция",
            "limit_bb": "Лимит",
        }
    )
    # округление
    df["Профит $"] = df["Профит $"].round(2)
    df["Профит bb"] = df["Профит bb"].round(1)
    return df

# db_utils.py

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("bbline.sqlite")


def insert_hand(hand: dict, cx: sqlite3.Connection | None = None) -> bool:
    """
    Вставляет раздачу в базу данных.

    Args:
        hand: Словарь с данными раздачи
        cx: Существующее соединение с БД (опционально)

    Returns:
        bool: True если раздача была вставлена, False если это дубликат

    Raises:
        sqlite3.Error: При ошибках работы с БД
    """
    own_conn = cx is None
    try:
        if own_conn:
            cx = sqlite3.connect(DB_PATH, timeout=30.0)  # Увеличиваем таймаут
        cur = cx.cursor()

        # Проверяем наличие всех необходимых полей
        required_fields = [
            "hand_id",
            "site",
            "game_type",
            "limit_bb",
            "datetime_utc",
            "button_seat",
            "hero_seat",
            "hero_name",
            "hero_cards",
            "board",
            "hero_invested",
            "hero_collected",
            "hero_rake",
            "rake",
            "jackpot",
            "final_pot",
            "hero_net",
            "hero_showdown",
        ]
        for field in required_fields:
            if field not in hand:
                raise ValueError(f"Отсутствует обязательное поле: {field}")

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
        inserted = cur.rowcount == 1

        if inserted:
            # Проверяем наличие всех необходимых данных для связанных таблиц
            if "seats" not in hand:
                raise ValueError("Отсутствуют данные о местах игроков")
            if "actions" not in hand:
                raise ValueError("Отсутствуют данные о действиях")
            if "collected_rows" not in hand:
                raise ValueError("Отсутствуют данные о выигрышах")
            if "showdowns" not in hand:
                raise ValueError("Отсутствуют данные о шоудаунах")

            # Пишем в связанные таблицы
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
            # Проверяем формат collected_rows
            for row in hand["collected_rows"]:
                if not isinstance(row, (list, tuple)) or len(row) != 3:
                    raise ValueError(f"Неверный формат записи в collected_rows: {row}")
                if not isinstance(row[0], str):
                    raise ValueError(f"hand_id должен быть строкой, получен {type(row[0])}")
                if not isinstance(row[1], int):
                    raise ValueError(f"seat_no должен быть целым числом, получен {type(row[1])}")
                if not isinstance(row[2], (int, float)):
                    raise ValueError(f"amount должен быть числом, получен {type(row[2])}")

            # Вставляем данные о выигрышах
            cur.executemany(
                "INSERT INTO collected (hand_id, seat_no, amount) VALUES (?,?,?);",
                hand["collected_rows"],
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

        return inserted

    except sqlite3.Error as e:
        if own_conn and cx:
            cx.rollback()
        raise sqlite3.Error(
            f"Ошибка при вставке раздачи {hand.get('hand_id', 'unknown')}: {str(e)}"
        )
    finally:
        if own_conn and cx:
            cx.close()

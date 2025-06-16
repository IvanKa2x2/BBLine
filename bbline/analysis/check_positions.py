"""
Скрипт для проверки формулы определения позиций.
Берет случайные раздачи из базы и выводит детальную информацию о позициях.
"""

import sqlite3

# import random # Удаляем неиспользуемый импорт
from pathlib import Path
from typing import List, Dict, Any

DB = Path(__file__).resolve().parents[1] / "database" / "bbline.sqlite"


def _pos_from_seats(hero_seat: int, button_seat: int) -> str:
    """Возвращает позицию героя по номерам мест (6-max)."""
    positions = ["BTN", "SB", "BB", "UTG", "MP", "CO"]
    offset = (hero_seat - button_seat) % 6
    return positions[offset]


def get_hands_by_ids(hand_ids: List[str]) -> List[Dict[str, Any]]:
    """Получает конкретные раздачи из базы данных."""
    with sqlite3.connect(DB) as cx:
        cx.row_factory = sqlite3.Row
        cur = cx.cursor()

        # Получаем детальную информацию
        hands = []
        for hand_id in hand_ids:
            hand = cur.execute(
                """
                SELECT h.hand_id, h.hero_seat, h.button_seat, h.hero_cards, h.board,
                       h.datetime_utc, h.limit_bb
                FROM hands h
                WHERE h.hand_id = ?
            """,
                (hand_id,),
            ).fetchone()

            if hand:
                hands.append(dict(hand))

        return hands


def count_invalid_seat_hands() -> int:
    """Подсчитывает количество рук, где hero_seat или button_seat равны -1."""
    with sqlite3.connect(DB) as cx:
        cur = cx.cursor()
        row = cur.execute(
            "SELECT COUNT(*) FROM hands WHERE hero_seat = -1 OR button_seat = -1;"
        ).fetchone()
        return row[0] if row else 0


def print_hand_info(hand: Dict[str, Any]) -> None:
    """Выводит информацию о раздаче в читаемом формате."""
    print("\n" + "=" * 50)
    print(f"Раздача: {hand['hand_id']}")
    print(f"Дата: {hand['datetime_utc']}")
    print(f"Лимит: {hand['limit_bb']} BB")
    print(f"Карты: {hand['hero_cards']}")
    print(f"Флоп: {hand['board']}")
    print(f"Место героя: {hand['hero_seat']}")
    print(f"Место баттона: {hand['button_seat']}")

    # Вычисляем позицию
    position = _pos_from_seats(hand["hero_seat"], hand["button_seat"])
    print(f"Вычисленная позиция: {position}")

    # Выводим схему стола
    print("\nСхема стола:")
    seats = ["BTN", "SB", "BB", "UTG", "MP", "CO"]
    offset = (hand["hero_seat"] - hand["button_seat"]) % 6
    for i in range(6):
        pos = seats[(i - offset) % 6]
        if i == hand["hero_seat"]:
            print(f"Seat {i}: {pos} (HERO)")
        elif i == hand["button_seat"]:
            print(f"Seat {i}: {pos} (BTN)")
        else:
            print(f"Seat {i}: {pos}")


def main():
    """Основная функция для проверки позиций."""
    print("Проверка формулы определения позиций")
    print("=" * 50)

    # Подсчитываем руки с некорректными местами
    invalid_hands_count = count_invalid_seat_hands()
    print(f"Количество рук с некорректными hero_seat или button_seat: {invalid_hands_count}")

    # Проверяем конкретную раздачу (или случайные, если нужно)
    # hand_ids = ["HD2249992322"]
    # hands = get_hands_by_ids(hand_ids)

    # if not hands:
    #     print("Раздача не найдена в базе данных")
    #     return

    # for hand in hands:
    #     print_hand_info(hand)


if __name__ == "__main__":
    main()

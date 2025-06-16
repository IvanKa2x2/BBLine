"""
Общие утилиты для работы с БД и фильтрами.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import pandas as pd

# Путь к БД (относительно текущего файла)
DB_PATH = Path(__file__).parent / "database" / "bbline.sqlite"

# Константы для позиций
POSITIONS = ["BB", "SB", "BTN", "CO", "MP", "EP"]

# Константы для лимитов
LIMITS = [0.02, 0.05, 0.10, 0.25, 0.50, 1.00]


def _validate_date(date_str: str) -> bool:
    """Проверяет формат даты YYYY-MM-DD."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _validate_limits(limits: List[float]) -> bool:
    """Проверяет, что все лимиты из списка стандартные."""
    return all(limit in LIMITS for limit in limits)


def _validate_positions(positions: List[str]) -> bool:
    """Проверяет, что все позиции из списка валидные."""
    return all(pos in POSITIONS for pos in positions)


def _pos_from_seats(hero_seat: int, button_seat: int) -> str:
    """Возвращает позицию героя по номерам мест (6-max)."""
    positions = ["BTN", "SB", "BB", "UTG", "MP", "CO"]
    offset = (hero_seat - button_seat) % 6
    return positions[offset]


def get_hand_ids(
    cur: sqlite3.Cursor,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limits: Optional[List[float]] = None,
    positions: Optional[List[str]] = None,
) -> List[str]:
    """Возвращает список hand_id с учетом фильтров (позиция фильтруется в Python)."""
    conditions = []
    params = []

    if date_from and _validate_date(date_from):
        conditions.append("date(datetime_utc) >= date(?)")
        params.append(date_from)

    if date_to and _validate_date(date_to):
        conditions.append("date(datetime_utc) <= date(?)")
        params.append(date_to)

    if limits and _validate_limits(limits):
        placeholders = ",".join(["?"] * len(limits))
        conditions.append(f"limit_bb IN ({placeholders})")
        params.extend(limits)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
    SELECT hand_id, hero_seat, button_seat
    FROM hands
    WHERE {where_clause}
    ORDER BY datetime_utc DESC, hand_id DESC;
    """

    hand_ids = []
    for hand_id, hero_seat, button_seat in cur.execute(query, params):
        pos = _pos_from_seats(hero_seat, button_seat)
        if not positions or pos in positions:
            hand_ids.append(hand_id)
    return hand_ids


def get_profit_by_date(cur: sqlite3.Cursor, hand_id: str) -> List[List[str]]:
    """Возвращает список [дата, профит $, профит bb] для конкретного hand_id."""
    query = """
    SELECT date(datetime_utc) AS date, profit_usd, profit_bb
    FROM hands
    WHERE hand_id = ?;
    """
    return [list(row) for row in cur.execute(query, (hand_id,))]


def get_profit_by_date_df(cur: sqlite3.Cursor, hand_id: str) -> pd.DataFrame:
    """Возвращает DataFrame с данными о профитах для конкретного hand_id."""
    data = get_profit_by_date(cur, hand_id)
    dates, profit_usd, profit_bb = zip(*data)
    df = pd.DataFrame(
        {
            "Дата": dates,
            "Профит $": profit_usd,
            "Профит bb": profit_bb,
        }
    )
    return df

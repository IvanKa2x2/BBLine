# src/analysis/utils.py

import sqlite3
from pathlib import Path

DB_PATH = Path("db/bbline.sqlite")


def check_db_exists():
    """Явная проверка наличия базы. Бросает исключение (используй в тестах или аналитике)."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"❌ База не найдена: {DB_PATH}")


def fetchall(query, params=(), safe=True):
    """
    Выполняет SQL-запрос и возвращает list[sqlite3.Row].
    safe=True — печатает ошибку и возвращает пустой список (для CLI/отчётов).
    safe=False — бросает исключение (для тестов).
    """
    try:
        check_db_exists()
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(query, params).fetchall()
    except Exception as e:
        if safe:
            print(f"⚠️ Ошибка запроса: {e}\nSQL: {query}")
            return []
        else:
            raise


def validate_table(table):
    """Проверяет, что нужная таблица есть в базе."""
    check_db_exists()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not c.fetchone():
            raise RuntimeError(f"❌ Таблица {table} не найдена в базе данных!")


def normalize(card1, card2, suited):
    """A♠ K♣ → AKs / AKo"""
    order = "23456789TJQKA"
    r1, r2 = card1[0], card2[0]
    if order.index(r1) < order.index(r2):
        r1, r2 = r2, r1
    combo = f"{r1}{r2}"
    return combo if combo in {"AA", "KK", "QQ", "JJ", "TT"} else f"{combo}{'s' if suited else 'o'}"


def print_table(title, headers, rows):
    print(f"\n🔸 {title}")
    print(" | ".join(f"{h:<10}" for h in headers))
    print("-" * (len(headers) * 12))
    for row in rows:
        print(" | ".join(f"{str(x):<10}" for x in row))
    print("-" * (len(headers) * 12))

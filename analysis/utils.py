# analysis/utils.py все общее и повторяющееся

import sqlite3
from pathlib import Path

DB_PATH = Path("db/bbline.sqlite")

def fetchall(query, params=()):
    """Упрощённый запрос: возвращает list[sqlite3.Row]"""
    if not DB_PATH.exists():
        print("❌ База не найдена: db/bbline.sqlite")
        return []
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(query, params).fetchall()

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

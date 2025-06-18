import sqlite3

cx = sqlite3.connect("bbline/database/bbline.sqlite")
cur = cx.cursor()

print("Таблица hands:")
for row in cur.execute("PRAGMA table_info(hands)").fetchall():
    print(row)
print("\nПример строки:")
print(cur.execute("SELECT * FROM hands LIMIT 1").fetchone())

print("\nТаблица actions:")
for row in cur.execute("PRAGMA table_info(actions)").fetchall():
    print(row)
print("\nПример строки:")
print(cur.execute("SELECT * FROM actions LIMIT 1").fetchone())

rows = cur.execute(
    """
    SELECT a.hand_id, a.seat_no, a.action, h.hero_pos, a.amount
    FROM actions a
    JOIN hands h ON a.hand_id = h.hand_id
    WHERE a.street = 'PREFLOP' AND a.action = 'call' AND a.seat_no = h.hero_pos
    LIMIT 20
"""
).fetchall()
print("Найдено строк:", len(rows))
for r in rows:
    print(r)

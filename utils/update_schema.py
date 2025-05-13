import sqlite3

conn = sqlite3.connect("db/bbline.sqlite")
c = conn.cursor()

# Добавим колонку, если её ещё нет
try:
    c.execute("ALTER TABLE players ADD COLUMN player_pos TEXT")
    print("✅ Колонка player_pos добавлена")
except sqlite3.OperationalError:
    print("⚠️ Колонка уже существует")

conn.commit()
conn.close()

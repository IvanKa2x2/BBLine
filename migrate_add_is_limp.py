import sqlite3

DB_PATH = "bbline/database/bbline.sqlite"

with sqlite3.connect(DB_PATH) as cx:
    cur = cx.cursor()
    try:
        cur.execute("ALTER TABLE computed_stats ADD COLUMN is_limp INTEGER DEFAULT 0")
        print("Поле is_limp добавлено.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e) or "already exists" in str(e):
            print("Поле is_limp уже существует.")
        else:
            raise
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stats_limp ON computed_stats(is_limp)")
    print("Индекс для is_limp создан.")

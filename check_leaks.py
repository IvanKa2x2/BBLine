from bbline.analysis.leakfinder import run_leakfinder
import sqlite3

# Проверяем утечки
leaks = run_leakfinder()
print("Найденные утечки:")
for leak in leaks:
    print(f"- {leak['name']}: {leak['value']}% (порог: {leak['threshold']}%)")

# Проверяем теги
cx = sqlite3.connect("bbline/database/bbline.sqlite")
cur = cx.cursor()
print("\nКоличество тегов:", cur.execute("SELECT COUNT(*) FROM tags").fetchone()[0])
print("Примеры тегов:", cur.execute("SELECT * FROM tags LIMIT 5").fetchall())
cx.close()

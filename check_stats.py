import sqlite3

cx = sqlite3.connect("bbline/database/bbline.sqlite")
cur = cx.cursor()

# Проверяем средние значения метрик
stats = cur.execute(
    """
    SELECT 
        ROUND(AVG(fold_to_3b) * 100, 1) as fold_to_3b_pct,
        ROUND(AVG(threebet) * 100, 1) as threebet_pct,
        ROUND(AVG(cbet_flop) * 100, 1) as cbet_flop_pct,
        COUNT(*) as total_hands
    FROM computed_stats
"""
).fetchone()

print("Статистика по всем рукам:")
print(f"Всего рук: {stats[3]}")
print(f"Fold to 3-bet: {stats[0]}%")
print(f"3-bet frequency: {stats[1]}%")
print(f"C-bet flop: {stats[2]}%")

cx.close()

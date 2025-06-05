"""
batch_import.py — пакетный импорт HH в базу BBLine
Запуск:
    python -m bbline.ingest.batch_import <папка_с_HH> [--ext .txt]
По дефолту импортит все .txt из указанной папки.

Важно:
- Игнорирует файлы, которые уже были импортированы (по hand_id).
- После каждого файла пишет короткий итог.
- Можно использовать для ежедневного/массового импорта архивов.
"""

import sys
from pathlib import Path
from bbline.parse.hand_parser import parse_file
from bbline.database.db_utils import insert_hand


def batch_import(folder, ext=".txt", db_path=None):
    folder = Path(folder)
    files = list(folder.glob(f"*{ext}"))
    if not files:
        print(f"[!] Нет файлов с расширением {ext} в {folder}")
        return

    total, skipped, imported = 0, 0, 0
    all_collected_rows = []  # Сюда складываем winners_rows

    for file in files:
        try:
            hands = parse_file(str(file))
        except Exception as e:
            print(f"[ERR] Не удалось разобрать {file}: {e}")
            continue

        for hand in hands:
            total += 1
            try:
                res = insert_hand(hand)
                if res:
                    imported += 1
                    # winners_rows = hand["collected_rows"]   # старое имя
                    winners_rows = hand.get("collected_rows", [])
                    all_collected_rows.extend(winners_rows)
                else:
                    skipped += 1
            except Exception as e:
                print(f"[ERR] Не удалось вставить {hand.get('hand_id')} — {e}")

    # Запишем всю кучу winners_rows в collected одним махом (если есть)
    if db_path and all_collected_rows:
        import sqlite3

        print(f"Вставляю {len(all_collected_rows)} записей в collected...")
        with sqlite3.connect(db_path) as cx:
            cur = cx.cursor()
            cur.executemany(
                """
                INSERT OR IGNORE INTO collected (hand_id, seat_no, amount)
                VALUES (?, ?, ?)
                """,
                all_collected_rows,
            )
            cx.commit()
        print("✅  winners_rows успешно записаны в collected")

    print("\n=== Batch импорт завершён ===")
    print(
        f"Итого файлов: {len(files)} | Рук всего: {total} | Новых: {imported} | Дубликатов: {skipped}"
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Используй: python -m bbline.ingest.batch_import <папка_с_HH> [--ext .txt]")
        sys.exit(1)
    folder = sys.argv[1]
    ext = ".txt"
    db_path = str(Path(__file__).resolve().parents[2] / "database" / "bbline.sqlite")
    if len(sys.argv) > 2 and sys.argv[2].startswith("--ext"):
        ext = sys.argv[2].split("=")[-1]
    batch_import(folder, ext, db_path=db_path)

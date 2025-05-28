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
from bbline.database.db_utils import insert_hand  # твой метод вставки одной раздачи


def batch_import(folder, ext=".txt"):
    folder = Path(folder)
    files = list(folder.glob(f"*{ext}"))
    if not files:
        print(f"[!] Нет файлов с расширением {ext} в {folder}")
        return

    total, skipped, imported = 0, 0, 0

    for file in files:
        # print(f"\n===> Обрабатываем: {file.name}")
        try:
            hands = parse_file(str(file))
        except Exception as e:
            print(f"[ERR] Не удалось разобрать {file}: {e}")
            continue

        for hand in hands:
            total += 1
            try:
                res = insert_hand(
                    hand
                )  # твоя функция должна корректно отлавливать дубликаты по hand_id
                if res:  # например, возвращает True если реально добавил
                    imported += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"[ERR] Не удалось вставить {hand.get('hand_id')} — {e}")

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
    if len(sys.argv) > 2 and sys.argv[2].startswith("--ext"):
        ext = sys.argv[2].split("=")[-1]
    batch_import(folder, ext)

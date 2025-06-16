"""
batch_import.py — пакетный импорт HH в базу BBLine
Запуск:
    python -m bbline.ingest.batch_import <папка_с_HH> [--ext .txt]
По дефолту импортит все .txt из указанной папки.

Важно:
- Игнорирует файлы, которые уже были импортированы (по hand_id).
- После каждого файла пишет короткий итог.
- Можно использовать для ежедневного/массового импорта архивов.
- Удаляет файлы после успешного импорта.
"""

import sys
import os
from pathlib import Path
from bbline.parse.hand_parser import parse_file
from bbline.database.db_utils import insert_hand


def batch_import(folder, ext=".txt", db_path=None):
    """
    Импортирует файлы с историей рук в базу данных.

    Args:
        folder (str): Путь к папке с файлами
        ext (str): Расширение файлов для импорта
        db_path (str): Путь к базе данных
    """
    folder = Path(folder)
    files = list(folder.glob(f"*{ext}"))
    if not files:
        print(f"[!] Нет файлов с расширением {ext} в {folder}")
        return

    total, skipped, imported = 0, 0, 0
    deleted_files = 0

    for file in files:
        file_imported, file_skipped = 0, 0
        try:
            hands = parse_file(str(file))

            for hand in hands:
                total += 1
                try:
                    res = insert_hand(hand)
                    status = "OK" if res else "dup"
                    print(f"  {hand['hand_id']} ... {status}")
                    if res:
                        imported += 1
                        file_imported += 1
                    else:
                        skipped += 1
                        file_skipped += 1
                except Exception as e:
                    print(f"[ERR] Не удалось вставить {hand.get('hand_id')} — {e}")

            # Удаляем файл только если в этом конкретном файле не было дублей
            if file_imported > 0 and file_skipped == 0:
                try:
                    os.remove(file)
                    deleted_files += 1
                    print(f"✅ Файл {file.name} успешно импортирован и удален")
                except Exception as e:
                    print(f"[ERR] Не удалось удалить файл {file}: {e}")

        except Exception as e:
            print(f"[ERR] Не удалось разобрать {file}: {e}")
            continue

    print("\n=== Batch импорт завершён ===")
    print(
        f"Итого файлов: {len(files)} | Рук всего: {total} | Новых: {imported} | "
        f"Пропущено (уже в базе): {skipped} | Удалено файлов: {deleted_files}"
    )


if __name__ == "__main__":
    # if len(sys.argv) < 2:
    #     print("Используй: python -m bbline.ingest.batch_import <папка_с_HH> [--ext .txt]")
    #     sys.exit(1)
    folder = (
        r"C:\Users\GameBase\BBLine\bbline\assets\raw"  # Прописываем папку с раздачами на постоянку
    )
    ext = ".txt"
    db_path = str(Path(__file__).resolve().parents[2] / "database" / "bbline.sqlite")
    if len(sys.argv) > 2 and sys.argv[2].startswith("--ext"):
        ext = sys.argv[2].split("=")[-1]
    batch_import(folder, ext, db_path=db_path)

from bbline.parse.hand_parser import parse_file
from bbline.database.db_utils import insert_hand

# Путь к файлу
PATH = "bbline/assets/test_session.txt"

hands = parse_file(PATH)
print(f"Найдено {len(hands)} раздач для импорта.")

for hand in hands:
    insert_hand(hand)
print("✅ Импорт завершён.")

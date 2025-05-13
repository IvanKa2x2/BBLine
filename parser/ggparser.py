# parser/ggparser.py

import re
import sqlite3
from datetime import datetime
import sys, os

# Добавляем путь до utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.db_schema import create_database

DB_PATH = "db/bbline.sqlite"

# Чтение файла и разделение на раздачи
def parse_gg_file(filepath):
    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    hands = []
    current_hand = []

    for line in lines:
        if line.startswith("Poker Hand #"):
            if current_hand:
                hands.append(current_hand)
            current_hand = [line.strip()]
        else:
            current_hand.append(line.strip())

    if current_hand:
        hands.append(current_hand)

    return hands

def parse_hand_meta(hand_lines):
    btn_seat = None
    hero_seat = None
    hero_pos = None
    pot_rake = None
    pot_total = None
    winner_seat = None

    for line in hand_lines:
        if "Seat #" in line and "button" in line:
            match = re.search(r"Seat #(\d+)", line)
            if match:
                btn_seat = int(match.group(1))

        if "Dealt to Hero" in line:
            for context_line in hand_lines:
                seat_match = re.match(r"Seat (\d+): Hero", context_line)
                if seat_match:
                    hero_seat = int(seat_match.group(1))

        if "Total pot $" in line:
            match = re.search(r"Total pot \$(\d+\.\d+).*?Rake \$(\d+\.\d+)", line)
            if match:
                pot_total = float(match.group(1))
                pot_rake = float(match.group(2))

        if "collected" in line:
            match = re.match(r"Seat (\d+): .*collected", line)
            if match:
                winner_seat = int(match.group(1))

    # Расчёт позиции героя по баттону
    if btn_seat and hero_seat:
        diff = (hero_seat - btn_seat) % 6  # для 6-max
        pos_map = {
            0: "BTN",
            1: "SB",
            2: "BB",
            3: "UTG",
            4: "MP",
            5: "CO"
        }
        hero_pos = pos_map.get(diff)

    return btn_seat, hero_seat, hero_pos, pot_total, pot_rake, winner_seat


# Парсинг игроков и начальных стеков
def parse_players(hand_lines, btn_seat=None):
    """
    Возвращает список игроков со стеком и позицией относительно баттона.
    Работает при любом количестве игроков (2‑6) и не падает, если
    описания сидящего на баттоне нет среди строк «Seat X: …».
    """
    pos_names = ['BTN', 'SB', 'BB', 'UTG', 'MP', 'CO']  # для 6‑max

    players = []
    for line in hand_lines:
        m = re.match(r"Seat (\d+): (.+?) \(\$(\d+\.\d{2})", line)
        if not m:
            continue

        seat = int(m.group(1))
        name = m.group(2).strip()
        stack = float(m.group(3))

        # позиция по умолчанию неизвестна
        player_pos = None

        if btn_seat:  # баттон известен
            diff = (seat - btn_seat) % 6          # 0‑5
            player_pos = pos_names[diff]          # BTN, SB, BB, …

        players.append({
            "seat": seat,
            "player_id": name,
            "start_stack_bb": stack,
            "player_pos": player_pos or "?"
        })

    return players


# Парсинг выигрышей из SUMMARY
def parse_summary_winnings(hand_lines, bb):
    seat_summary = {}
    in_summary = False

    for line in hand_lines:
        if line.startswith("*** SUMMARY ***"):
            in_summary = True
            continue

        if in_summary and line.startswith("Seat"):
            seat_match = re.match(r"Seat (\d+):", line)
            win_match = re.search(r"(collected|won) \(\$([\d\.]+)\)", line)

            if seat_match:
                seat = int(seat_match.group(1))
                won_bb = float(win_match.group(2)) / bb if win_match else 0.0
                seat_summary[seat] = (None, won_bb)
    return seat_summary

# Парсинг карманки Hero
def parse_hero_cards(hand_lines):
    for line in hand_lines:
        match = re.search(r"Dealt to Hero \[(\w\w) (\w\w)\]", line)
        if match:
            card1 = match.group(1)
            card2 = match.group(2)
            suited = card1[1] == card2[1]
            return card1, card2, suited
    return None, None, None

# Парсинг действий по улицам
def parse_actions(hand_lines, bb):
    actions = []
    current_street = "P"
    street_markers = {
        "*** FLOP ***": "F",
        "*** TURN ***": "T",
        "*** RIVER ***": "R",
        "*** SHOW DOWN ***": None,
        "*** SUMMARY ***": None
    }

    for line in hand_lines:
        for marker, street in street_markers.items():
            if line.startswith(marker):
                current_street = street
                break

        match = re.match(r"(.+?): (bets|calls|raises|checks|folds)( to)? ?\$?([\d\.]+)?", line)
        if match and current_street:
            player = match.group(1).strip()
            action_type = match.group(2)
            amount = float(match.group(4)) if match.group(4) else 0.0

            action_map = {
                "bets": "bet",
                "calls": "call",
                "raises": "raise",
                "checks": "check",
                "folds": "fold"
            }

            actions.append({
                "player_id": player,
                "action": action_map[action_type],
                "amount_bb": amount / bb if amount else 0.0,
                "street": current_street
            })

    return actions

# Главная функция обработки всех раздач
def parse_and_insert_hands(filepath):
    create_database(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    all_hands = parse_gg_file(filepath)
    print(f"🔍 Найдено {len(all_hands)} раздач")

    for hand in all_hands:
        try:
            joined = "\n".join(hand)

            # Общие данные
            hand_id_match = re.search(r'#(HD\d+):', joined)
            table_name_match = re.search(r"Table '(.+?)'", joined)
            timestamp_match = re.search(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})', joined)
            stakes_match = re.search(r"\(\$(\d+\.\d+)/\$(\d+\.\d+)\)", joined)

            if not (hand_id_match and table_name_match and timestamp_match and stakes_match):
                raise ValueError("Не удалось найти необходимые поля")

            hand_id = hand_id_match.group(1)
            table_name = table_name_match.group(1)
            dt = datetime.strptime(timestamp_match.group(1), "%Y/%m/%d %H:%M:%S")
            timestamp = int(dt.timestamp())
            sb = float(stakes_match.group(1))
            bb = float(stakes_match.group(2))

            # Вставка в таблицу hands
            c.execute("INSERT OR IGNORE INTO hands (hand_id, date_ts, table_name, sb, bb) VALUES (?, ?, ?, ?, ?)",
                    (hand_id, timestamp, table_name, sb, bb))

            # Парсим метаданные раздачи
            btn_seat, hero_seat, hero_pos, pot_total, pot_rake, winner_seat = parse_hand_meta(hand)

            # Обновляем hands этими полями
            c.execute("""
                UPDATE hands
                SET btn_seat = ?, hero_seat = ?, hero_pos = ?, pot_total = ?, pot_rake = ?, winner_seat = ?
                WHERE hand_id = ?
            """, (btn_seat, hero_seat, hero_pos, pot_total, pot_rake, winner_seat, hand_id))

            # Парсим игроков (передаём btn_seat!)
            players = parse_players(hand, btn_seat)

            if not players:
                raise ValueError("Игроки не найдены")

            for player in players:
                print(f"[INSERT] {player['player_id']} | seat {player['seat']} → {player['player_pos']}")
                c.execute("""
                INSERT OR REPLACE INTO players
                        (hand_id, seat, player_id, start_stack_bb, player_pos)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    hand_id,
                    player["seat"],
                    player["player_id"],
                    player["start_stack_bb"] / bb,
                    player["player_pos"]
                ))


            # Парсим карманку Hero
            card1, card2, suited = parse_hero_cards(hand)
            if card1 and card2:
                c.execute("""
                    INSERT OR IGNORE INTO hero_cards (hand_id, card1, card2, suited)
                    VALUES (?, ?, ?, ?)
                """, (hand_id, card1, card2, suited))

            # Парсим действия
            seat_map = {p["player_id"]: p["seat"] for p in players}
            parsed_actions = parse_actions(hand, bb)

            for act in parsed_actions:
                seat = seat_map.get(act["player_id"])
                if seat is None:
                    continue
                c.execute("""
                    INSERT INTO actions (hand_id, street, seat, action, amount_bb)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    hand_id,
                    act["street"],
                    seat,
                    act["action"],
                    act["amount_bb"]
                ))

            # Обновляем выигрыши
            seat_summary = parse_summary_winnings(hand, bb)
            for seat, (end_stack, won_bb) in seat_summary.items():
                c.execute("""
                    UPDATE players
                    SET end_stack_bb = ?, won_bb = ?
                    WHERE hand_id = ? AND seat = ?
                """, (end_stack, won_bb, hand_id, seat))

        except Exception as e:
            print(f"❌ Ошибка в раздаче: {hand[:2]} — {e}")

    conn.commit()
    conn.close()
    print("✅ Все руки обработаны и добавлены в базу.")

# Запуск
if __name__ == "__main__":
    parse_and_insert_hands("data/raw/GG20250509-1348 - NLHWhite65 - 0.01 - 0.02 - 6max.txt")

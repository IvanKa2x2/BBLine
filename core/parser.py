# parser/ggparser.py
"""
Парсер HH **только для GGPoker**. Другие румы не поддерживаются.
"""

import re
import sqlite3
from datetime import datetime
import sys
import os
import glob

# Добавляем путь до utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db.db_schema import create_database

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


def get_pos(seat, btn_seat, seats_list):
    n = len(seats_list)
    pos_map = {
        6: ["BTN", "SB", "BB", "UTG", "MP", "CO"],
        5: ["BTN", "SB", "BB", "UTG", "CO"],
        4: ["BTN", "SB", "BB", "UTG"],
        3: ["BTN", "SB", "BB"],
        2: ["BTN", "BB"],
    }
    if n not in pos_map or btn_seat not in seats_list:
        return "?"   # вот это ключ! Не падаем, а просто ставим неизвестную позицию
    sorted_seats = sorted(seats_list)
    btn_idx = sorted_seats.index(btn_seat)
    order = [sorted_seats[(btn_idx + i) % n] for i in range(n)]
    seat2pos = {seat: pos for seat, pos in zip(order, pos_map[n])}
    return seat2pos.get(seat, "?")


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
        pos_map = {0: "BTN", 1: "SB", 2: "BB", 3: "UTG", 4: "MP", 5: "CO"}
        hero_pos = pos_map.get(diff)

    return btn_seat, hero_seat, hero_pos, pot_total, pot_rake, winner_seat


# Парсинг игроков и начальных стеков
def parse_players(hand_lines, btn_seat=None):
    """
    Возвращает список игроков со стеком и позицией относительно баттона.
    Работает при любом количестве игроков (2‑6) и не падает, если
    описания сидящего на баттоне нет среди строк «Seat X: …».
    """

    # 1. Собираем все seat
    seats = []
    for line in hand_lines:
        m = re.match(r"Seat (\d+): (.+?) \(\$(\d+\.\d{2})", line)
        if m:
            seats.append(int(m.group(1)))

    players = []
    for line in hand_lines:
        m = re.match(r"Seat (\d+): (.+?) \(\$(\d+\.\d{2})", line)
        if not m:
            continue

        seat = int(m.group(1))
        name = m.group(2).strip()
        stack = float(m.group(3))

        player_pos = "?"
        if btn_seat and seats:
            player_pos = get_pos(seat, btn_seat, seats)

        players.append(
            {
                "seat": seat,
                "player_id": name,
                "start_stack_bb": stack,
                "player_pos": player_pos,
            }
        )

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


# Парсинг действий по улицам с гибким антидубликатором
def parse_actions(hand_lines, bb, strict_dedup=True):
    actions = []
    seen = set()
    current_street = "P"

    street_markers = {
        "*** FLOP ***": "F",
        "*** TURN ***": "T",
        "*** RIVER ***": "R",
        "*** SHOW DOWN ***": None,
        "*** SUMMARY ***": None,
    }

    for i, line in enumerate(hand_lines):
        for marker, street in street_markers.items():
            if line.startswith(marker):
                current_street = street
                break

        m = re.match(
            r"(.+?): (bets|calls|raises|checks|folds)( to)? ?\$?([\d\.]+)?", line
        )
        if not (m and current_street):
            continue

        player = m.group(1).strip()
        verb = m.group(2)
        amount = float(m.group(4)) if m.group(4) else 0.0

        action_map = {
            "bets": "bet",
            "calls": "call",
            "raises": "raise",
            "checks": "check",
            "folds": "fold",
        }

        action_name = action_map[verb]
        amount_bb = amount / bb if amount else 0.0

        # --- формируем ключ ---
        key = (current_street, player, action_name, amount_bb)
        if strict_dedup:
            if key in seen:
                continue  # дубликат — игнорим
            seen.add(key)
        # ----------------------

        actions.append(
            {
                "player_id": player,
                "action": action_name,
                "amount_bb": amount_bb,
                "street": current_street,
            }
        )

    return actions


# Парсинг board: flop, turn, river
def parse_board(hand_lines):
    flop_cards = [None, None, None]
    turn_card = None
    river_card = None
    for line in hand_lines:
        m = re.match(r"\*\*\* FLOP \*\*\* \[(\w\w) (\w\w) (\w\w)\]", line)
        if m:
            flop_cards = [m.group(1), m.group(2), m.group(3)]
        m = re.match(r"\*\*\* TURN \*\*\* \[\w\w \w\w \w\w\] \[(\w\w)\]", line)
        if m:
            turn_card = m.group(1)
        m = re.match(r"\*\*\* RIVER \*\*\* \[\w\w \w\w \w\w \w\w\] \[(\w\w)\]", line)
        if m:
            river_card = m.group(1)
    return flop_cards[0], flop_cards[1], flop_cards[2], turn_card, river_card


# -----------------------------


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
            hand_id_match = re.search(r"#(HD\d+):", joined)
            table_name_match = re.search(r"Table '(.+?)'", joined)
            timestamp_match = re.search(
                r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})", joined
            )
            stakes_match = re.search(r"\(\$(\d+\.\d+)/\$(\d+\.\d+)\)", joined)

            if not (
                hand_id_match and table_name_match and timestamp_match and stakes_match
            ):
                raise ValueError("Не удалось найти необходимые поля")

            hand_id = hand_id_match.group(1)
            # Пропускаем, если такая раздача уже есть в базе
            c.execute("SELECT 1 FROM hands WHERE hand_id = ?", (hand_id,))
            if c.fetchone():
                print(f"⏩ Пропущено: {hand_id} уже в базе")
                continue

            table_name = table_name_match.group(1)
            dt = datetime.strptime(timestamp_match.group(1), "%Y/%m/%d %H:%M:%S")
            timestamp = int(dt.timestamp())
            sb = float(stakes_match.group(1))
            bb = float(stakes_match.group(2))

            # Вставка в таблицу hands
            c.execute(
                "INSERT OR IGNORE INTO hands (hand_id, date_ts, table_name, sb, bb) VALUES (?, ?, ?, ?, ?)",
                (hand_id, timestamp, table_name, sb, bb),
            )

            # Парсим метаданные раздачи
            btn_seat, hero_seat, hero_pos, pot_total, pot_rake, winner_seat = (
                parse_hand_meta(hand)
            )

            # Обновляем hands этими полями
            c.execute(
                """
                UPDATE hands
                SET btn_seat = ?, hero_seat = ?, hero_pos = ?, pot_total = ?, pot_rake = ?, winner_seat = ?
                WHERE hand_id = ?
            """,
                (
                    btn_seat,
                    hero_seat,
                    hero_pos,
                    pot_total,
                    pot_rake,
                    winner_seat,
                    hand_id,
                ),
            )

            # Парсим игроков (передаём btn_seat!)
            players = parse_players(hand, btn_seat)

            if not players:
                raise ValueError("Игроки не найдены")

            for player in players:
                print(
                    f"[INSERT] {player['player_id']} | seat {player['seat']} → {player['player_pos']}"
                )
                c.execute(
                    """
                INSERT OR IGNORE INTO players
                        (hand_id, seat, player_id, start_stack_bb, player_pos)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        hand_id,
                        player["seat"],
                        player["player_id"],
                        player["start_stack_bb"] / bb,
                        player["player_pos"],
                    ),
                )

            # Парсим карманку Hero
            card1, card2, suited = parse_hero_cards(hand)
            if card1 and card2:
                c.execute(
                    """
                    INSERT OR IGNORE INTO hero_cards (hand_id, card1, card2, suited)
                    VALUES (?, ?, ?, ?)
                """,
                    (hand_id, card1, card2, suited),
                )

            # Парсим действия
            seat_map = {p["player_id"]: p["seat"] for p in players}
            parsed_actions = parse_actions(hand, bb, strict_dedup=True)

            for act in parsed_actions:
                seat = seat_map.get(act["player_id"])
                if seat is None:
                    continue
                c.execute(
                    """
                    INSERT INTO actions (hand_id, street, seat, action, amount_bb)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (hand_id, act["street"], seat, act["action"], act["amount_bb"]),
                )
                # --- вставляем board в таблицу ---
            flop1, flop2, flop3, turn_card, river_card = parse_board(hand)
            c.execute(
                """
                INSERT OR IGNORE INTO board
                    (hand_id, flop1, flop2, flop3, turn, river)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (hand_id, flop1, flop2, flop3, turn_card, river_card),
            )

            # Обновляем выигрыши
            seat_summary = parse_summary_winnings(hand, bb)
            for seat, (end_stack, won_bb) in seat_summary.items():
                c.execute(
                    """
                    UPDATE players
                    SET end_stack_bb = ?, won_bb = ?
                    WHERE hand_id = ? AND seat = ?
                """,
                    (end_stack, won_bb, hand_id, seat),
                )
            # Находим Hero seat
            hero_seat = next(
                (p["seat"] for p in players if "Hero" in p["player_id"]), None
            )
            hero_player = next((p for p in players if "Hero" in p["player_id"]), None)

            if hero_seat is not None and hero_player is not None:
                start_stack_bb = hero_player["start_stack_bb"] / bb
                won_bb = seat_summary.get(hero_seat, (None, 0.0))[1]
                invested_bb = sum(
                    a["amount_bb"]
                    for a in parsed_actions
                    if a["street"] == "P"
                    and seat_map.get(a["player_id"]) == hero_seat
                    and a["action"] in ("call", "bet", "raise")
                )
                first_action = next(
                    (
                        a["action"]
                        for a in parsed_actions
                        if a["street"] == "P"
                        and seat_map.get(a["player_id"]) == hero_seat
                    ),
                    None,
                )

                end_stack_bb = start_stack_bb - invested_bb + won_bb
                net_bb = won_bb - invested_bb

                c.execute(
                    """
                    UPDATE players
                    SET invested_bb   = ?,
                        net_bb        = ?,
                        preflop_action= ?,
                        end_stack_bb  = ?,
                        won_bb        = COALESCE(won_bb , 0)  -- если уже есть – не затираем
                    WHERE hand_id = ? AND seat = ?
                """,
                    (
                        invested_bb,
                        net_bb,
                        first_action,
                        end_stack_bb,
                        hand_id,
                        hero_seat,
                    ),
                )

        except Exception as e:
            print(f"❌ Ошибка в раздаче: {hand[:2]} — {e}")

    conn.commit()
    conn.close()
    print("✅ Все руки обработаны и добавлены в базу.")


def find_and_parse_all_txt_files(folder="data/raw"):
    txt_files = glob.glob(os.path.join(folder, "**", "*.txt"), recursive=True)
    print(f"📁 Найдено {len(txt_files)} текстовых файлов для обработки")

    for path in txt_files:
        print(f"🧾 Обрабатываем: {path}")
        try:
            parse_and_insert_hands(path)
            os.remove(path)
            print(f"🗑️ Удалён: {path}")
        except Exception as e:
            print(f"❌ Ошибка при обработке {path}: {e}")


if __name__ == "__main__":
    find_and_parse_all_txt_files("data/raw")

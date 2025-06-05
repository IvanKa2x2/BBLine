# bbline/parse/hand_parser.py
"""
GGPoker HH → dict по схемам BBLine.
▪ «site» намеренно жёстко = 'ggpoker'
▪ покрывает NLHE 6-max / 9-max, Hero-only, без мульти-бордов
▪ для скорости и простоты — чистые regex + state-machine

⚠️  MVP: hero_net считается по строкам «collected / won / lost» в SUMMARY
    • EV-diff, Uncalled bet, All-in не трекаются (ещё не реализовано)
"""

import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from pathlib import Path
import sqlite3


# ---------- компилируем часто используемые regex’ы ----------
RE_HAND_START = re.compile(
    r"^Poker Hand #(?P<hand_id>\w+): Hold'em No Limit "
    r"\(\$(?P<sb>\d+\.\d+)/\$(?P<bb>\d+\.\d+)\) - "
    r"(?P<date>\d{4}/\d{2}/\d{2}) (?P<time>\d{2}:\d{2}:\d{2})"
)

RE_TABLE_BUTTON = re.compile(r"Table '.*?' .*? Seat #(?P<button>\d+) is the button")
RE_SEAT = re.compile(
    r"Seat (?P<seat>\d+): (?P<player>.+?) " r"\(\$(?P<stack>\d+(\.\d+)?) in chips\)"
)

RE_POST_BLIND = re.compile(
    r"^(?P<player>.+?): posts (?P<blind>small|big) blind \$?(?P<amt>\d+\.\d+)"
)

RE_DEALT_HERO = re.compile(r"^Dealt to Hero \[(?P<card1>\w{2}) (?P<card2>\w{2})\]")

RE_STREET_BOARD = re.compile(
    r"^\*\*\* (?P<street>FLOP|TURN|RIVER) \*\*\* \[(?P<cards>[^\]]+)\](?: \[(?P<turnriver>[^\]]+)\])?"
)

RE_ACTION = re.compile(
    r"^(?P<player>[^:]+): "
    r"(?:(?P<posts>posts) (?P<blind_type>small|big) blind \$?(?P<post_amt>\d+\.\d+)"
    r"|(?P<bets>bets) \$?(?P<bet_amt>\d+\.\d+)"
    r"|(?P<raises>raises) \$?(?P<raise_from>\d+\.\d+) to \$?(?P<raise_to>\d+\.\d+)"
    r"|(?P<calls>calls) \$?(?P<call_amt>\d+\.\d+)"
    r"|(?P<folds>folds)"
    r"|(?P<checks>checks))"
)
RE_SUMMARY_SHOW = re.compile(
    r"^Seat\s+(?P<seat>\d+):\s+(?P<player>.+?)\s+.*?showed\s+\[(?P<card1>\w{2})\s+(?P<card2>\w{2})\]"
)

RE_UNCALLED = re.compile(r"Uncalled bet \(\$(?P<amt>\d+\.\d+)\) returned to (?P<player>.+)")
RE_COLLECTED = re.compile(r"^(?P<player>.+?) collected \$?(?P<amt>\d+\.\d+) from pot")
RE_WON = re.compile(r"^(?P<player>.+?) won \(\$(?P<amt>\d+\.\d+)\)")
RE_SHOWS_COLLECTED = re.compile(r"^Hero: shows .*? collected \$?(?P<amt>\d+\.\d+)")
RE_TOTAL_POT = re.compile(
    r"Total pot \$?(?P<total>\d+\.\d+) \| Rake \$?(?P<rake>\d+\.\d+).*?(?:Jackpot \$?(?P<jackpot>\d+\.\d+))?"
)
# «Seat 3: Hero (button) collected ($1.40)»
RE_SEAT_COLLECTED = re.compile(
    r"^Seat\s+(?P<seat>\d+):\s+(?P<player>[^(]+?)\s*(\([^)]+\))?\s*collected\s+\(\$(?P<amt>\d+\.\d+)\)"
)
RE_SEAT_WON = re.compile(r"^Seat\s+\d+:\s+(?P<player>.+?)\s+won\s+\(\$(?P<amt>\d+\.\d+)\)")


# ------------------------------------------------------------
def normalize_player_name(name: str) -> str:
    """Нормализует имя игрока: убирает пробелы, скобки и двоеточие."""
    name = name.strip()
    name = re.sub(r"\s*\(.*\)$", "", name)
    name = name.rstrip(":")
    return name


def split_raw_hands(text: str) -> List[str]:
    """Разделяет текст с историями раздач на отдельные раздачи."""
    out, buf = [], []
    for line in text.splitlines():
        if line.startswith("Poker Hand #") and buf:
            out.append("\n".join(buf))
            buf = [line]
        else:
            buf.append(line)
    if buf:
        out.append("\n".join(buf))
    return out


def parse_seat_block(
    lines: List[str],
) -> Tuple[Dict[str, int], List[Dict[str, Any]], Dict[int, str]]:
    """Парсит блок информации об игроках за столом."""
    seat_map_name_to_num: Dict[str, int] = {}
    seats: List[Dict[str, Any]] = []
    seat_map_num_to_name: Dict[int, str] = {}

    for ln in lines:
        m = RE_SEAT.match(ln)
        if m:
            seat_no = int(m.group("seat"))
            player = normalize_player_name(m.group("player"))
            stack = float(m.group("stack"))
            seat_map_name_to_num[player] = seat_no
            seat_map_num_to_name[seat_no] = player
            seats.append({"seat_no": seat_no, "player_id": player, "chips": stack})
    return seat_map_name_to_num, seats, seat_map_num_to_name


def utc_iso(date_str: str, time_str: str) -> str:
    """Преобразует дату и время из истории раздачи в формат ISO 8601 UTC."""
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
    return dt.replace(tzinfo=timezone.utc).isoformat(timespec="seconds")


def parse_actions(
    action_lines: List[str], seat_map: Dict[str, int], street: str, order_start: int
) -> Tuple[List[Dict[str, Any]], int]:
    """Парсит строки действий игроков на определенной улице."""
    actions: List[Dict[str, Any]] = []
    order_no = order_start
    street_commit = defaultdict(float)

    for ln in action_lines:
        m = RE_ACTION.match(ln)
        if not m:
            continue
        player = normalize_player_name(m.group("player"))
        act: str | None = None
        amount: float | None = None

        if m.group("posts"):
            act = "POST_" + m.group("blind_type").upper() + "_BLIND"
            amount = float(m.group("post_amt"))
            street_commit[player] += amount
        elif m.group("bets"):
            act = "BET"
            amount = float(m.group("bet_amt"))
            street_commit[player] += amount
        elif m.group("raises"):
            act = "RAISE"
            raise_to = float(m.group("raise_to"))
            amount = raise_to - street_commit[player]
            street_commit[player] = raise_to
        elif m.group("calls"):
            act = "CALL"
            amount = float(m.group("call_amt"))
            street_commit[player] += amount
        elif m.group("folds"):
            act = "FOLD"
        elif m.group("checks"):
            act = "CHECK"

        if act:
            actions.append(
                {
                    "street": street,
                    "order_no": order_no,
                    "seat_no": seat_map.get(player, -1),
                    "act": act,
                    "amount": amount,
                    "allin": 0,
                }
            )
            order_no += 1
    return actions, order_no


def calculate_invested_voluntarily(actions: list[dict], hero_seat: int) -> float:
    """
    Считает добровольно вложенные Hero деньги (CALL, BET, RAISE).
    Для поля hero_invested (без блайндов, как в H2N "Invested $").
    """
    invested = 0.0
    for a in actions:
        if a["seat_no"] == hero_seat and a["act"] in {"CALL", "BET", "RAISE"}:
            if a["amount"] is not None:
                invested += a["amount"]
    return round(invested, 2)


def calculate_total_actual_investment(actions: list[dict], hero_seat: int) -> float:
    """
    • CALL / BET / RAISE  — всегда
    • свой SB/BB/ANTE     — если Hero сделал ≥1 CALL/BET/RAISE в этой раздаче
    • Uncalled bet вычитаем позже в parse_hand
    """
    hero_has_voluntary = any(
        a["seat_no"] == hero_seat and a["act"] in {"CALL", "BET", "RAISE"} for a in actions
    )

    invested = 0.0
    for a in actions:
        if a["seat_no"] != hero_seat or a["amount"] is None:
            continue

        act = a["act"]
        amt = a["amount"]

        if act in {"CALL", "BET", "RAISE"}:
            invested += amt
        elif hero_has_voluntary and act in {"POST_SMALL_BLIND", "POST_BIG_BLIND", "POST_ANTE"}:
            invested += amt

    return round(invested, 2)


def parse_hand(raw: str) -> dict:
    """
    Парсит одну HH в словарь.
    hero_invested — добровольные вложения (без блайндов).
    hero_net — полный профит Hero (с учётом блайндов, для bb/100).
    """
    hero_uncalled = 0.0
    hero_collected = 0.0
    winners_total = 0.0
    winners_rows = []
    collected_set_total = set()  # пары (player, amount)
    collected_set_hero = set()  # чтобы дважды не добавить героя
    lines = [ln.rstrip() for ln in raw.splitlines() if ln.strip()]

    m_header = RE_HAND_START.match(lines[0])
    if not m_header:
        raise ValueError("Ошибка: некорректный заголовок истории раздачи.")
    hand_id = m_header.group("hand_id")
    bb = float(m_header.group("bb"))
    date_iso = utc_iso(m_header.group("date"), m_header.group("time"))

    m_btn_info = next((RE_TABLE_BUTTON.match(ln) for ln in lines if "button" in ln.lower()), None)
    button_seat = int(m_btn_info.group("button")) if m_btn_info else -1

    first_action_or_cards_idx = next(
        (i for i, ln in enumerate(lines) if RE_POST_BLIND.match(ln) or "*** HOLE CARDS ***" in ln),
        len(lines),
    )
    seat_block_lines = lines[2:first_action_or_cards_idx]
    seat_map_name_to_num, seats_info, seat_map_num_to_name = parse_seat_block(seat_block_lines)

    hero_player_key: str | None = None
    hero_seat = -1
    for s_entry in seats_info:
        if s_entry["player_id"] == "Hero":
            hero_player_key = "Hero"
            hero_seat = s_entry["seat_no"]
            break
    if hero_player_key is None:
        hero_player_key = "Hero"

    hero_cards_str: str | None = None
    for ln in lines:
        m_hero_cards = RE_DEALT_HERO.match(ln)
        if m_hero_cards:
            hero_cards_str = m_hero_cards.group("card1") + m_hero_cards.group("card2")
            break

    all_actions: List[Dict[str, Any]] = []
    showdown_entries: List[Dict[str, Any]] = []
    board_cards_by_street: Dict[str, List[str]] = {"FLOP": [], "TURN": [], "RIVER": []}
    current_street_state = "PREFLOP"
    action_order_no = 0
    current_street_lines: List[str] = []

    RE_SHOWDOWN_LINE = re.compile(
        r"(?:Seat\s+(?P<seat>\d+):\s+)?(?P<player>\S+).*?show(?:ed|s)\s+\[(?P<card1>\w{2})\s+(?P<card2>\w{2})\]"
    )

    for line_idx, ln in enumerate(lines):
        if ln.startswith("***") and "HOLE CARDS" not in ln:
            if current_street_lines:
                acts, action_order_no = parse_actions(
                    current_street_lines,
                    seat_map_name_to_num,
                    current_street_state,
                    action_order_no,
                )
                all_actions.extend(acts)
                current_street_lines = []

            m_board_line = RE_STREET_BOARD.match(ln)
            if m_board_line:
                current_street_state = m_board_line.group("street")
                parsed_cards = m_board_line.group("cards").split()
                board_cards_by_street[current_street_state] = parsed_cards
                if m_board_line.group("turnriver"):
                    board_cards_by_street[current_street_state].append(
                        m_board_line.group("turnriver")
                    )
                continue

        current_street_lines.append(ln)

        m_uncalled_bet = RE_UNCALLED.match(ln)
        if (
            m_uncalled_bet
            and normalize_player_name(m_uncalled_bet.group("player")) == hero_player_key
        ):
            hero_uncalled += float(m_uncalled_bet.group("amt"))

        m_showdown = RE_SHOWDOWN_LINE.search(ln)
        if m_showdown:
            player_name = normalize_player_name(m_showdown.group("player"))
            shown_cards = m_showdown.group("card1") + m_showdown.group("card2")
            player_seat = seat_map_name_to_num.get(player_name, -1)
            if player_seat == -1 and m_showdown.group("seat"):
                try:
                    player_seat = int(m_showdown.group("seat"))
                except ValueError:
                    player_seat = -1
            if player_seat != -1 and not any(
                s_entry["seat_no"] == player_seat for s_entry in showdown_entries
            ):
                showdown_entries.append({"seat_no": player_seat, "cards": shown_cards, "won": None})
            elif player_seat == -1:
                print(
                    f"[ПРЕДУПРЕЖДЕНИЕ] Шоудаун: не найден seat_no для игрока '{player_name}' (исходное: '{m_showdown.group('player')}') в раздаче {hand_id}."
                )

        m_collected_pot = RE_COLLECTED.match(ln)
        m_won_pot = RE_WON.match(ln)
        m_shows_collected = RE_SHOWS_COLLECTED.match(ln)
        m_seat_collected = RE_SEAT_COLLECTED.match(ln)
        m_seat_won = RE_SEAT_WON.match(ln)
        collected_amount = None
        winner_name = None

        if m_collected_pot:
            winner_name = normalize_player_name(m_collected_pot.group("player"))
            collected_amount = float(m_collected_pot.group("amt"))
        elif m_won_pot:
            winner_name = normalize_player_name(m_won_pot.group("player"))
            collected_amount = float(m_won_pot.group("amt"))
        elif m_shows_collected:
            winner_name = hero_player_key
            collected_amount = float(m_shows_collected.group("amt"))
        elif m_seat_collected:
            winner_name = normalize_player_name(m_seat_collected.group("player"))
            collected_amount = float(m_seat_collected.group("amt"))
        elif m_seat_won:
            winner_name = normalize_player_name(m_seat_won.group("player"))
            collected_amount = float(m_seat_won.group("amt"))
        else:
            collected_amount = None

        if collected_amount is not None:
            key = (winner_name, collected_amount)
            if key in collected_set_total:
                continue
            collected_set_total.add(key)
            winners_total += collected_amount
            seat_no = seat_map_name_to_num.get(winner_name, -1)
            if seat_no != -1:
                winners_rows.append((hand_id, seat_no, collected_amount))

            if winner_name == hero_player_key and key not in collected_set_hero:
                hero_collected += collected_amount
                collected_set_hero.add(key)

    if current_street_lines:
        acts, _ = parse_actions(
            current_street_lines, seat_map_name_to_num, current_street_state, action_order_no
        )
        all_actions.extend(acts)

    total_pot_val, rake_val, jackpot_val = None, 0.0, 0.0
    for ln in lines:
        m_total_pot_info = RE_TOTAL_POT.search(ln)
        if m_total_pot_info:
            total_pot_val = float(m_total_pot_info.group("total"))
            rake_val = float(m_total_pot_info.group("rake"))
            if m_total_pot_info.group("jackpot"):
                jackpot_val = float(m_total_pot_info.group("jackpot"))
            break

    flop_str = "".join(board_cards_by_street["FLOP"])
    turn_cards = board_cards_by_street["TURN"]
    river_cards = board_cards_by_street["RIVER"]

    turn_card_str = ""
    if len(turn_cards) > len(board_cards_by_street["FLOP"]):
        turn_card_str = turn_cards[-1]

    river_card_str = ""
    if len(river_cards) > len(turn_cards):
        river_card_str = river_cards[-1]
    elif not turn_card_str and len(river_cards) > len(board_cards_by_street["FLOP"]):
        river_card_str = river_cards[-1]

    board_string_representation = "|".join(filter(None, [flop_str, turn_card_str, river_card_str]))

    # 1. Добровольно вложенное (без блайндов)
    total_voluntary_sum_by_hero = calculate_invested_voluntarily(all_actions, hero_seat)
    hero_invested_display_value = round(total_voluntary_sum_by_hero - hero_uncalled, 2)
    # 2. Фактически вложено Hero (с учётом блайндов)
    hero_total_investment = calculate_total_actual_investment(all_actions, hero_seat)
    actual_hero_cost_for_hand = round(hero_total_investment - hero_uncalled, 2)
    # 3. Profit
    profit_for_hero = round(hero_collected - actual_hero_cost_for_hand, 2)
    # ------- HERO RAKE (доля от общего рейка) -------
    if winners_total > 0:
        hero_rake = round(rake_val * (hero_collected / winners_total), 4)
    else:
        hero_rake = 0.0

    hand_data_dict = {
        "hand_id": hand_id,
        "site": "ggpoker",
        "game_type": "NLHE",
        "limit_bb": bb,
        "datetime_utc": date_iso,
        "button_seat": button_seat,
        "hero_seat": hero_seat,
        "hero_name": hero_player_key,
        "hero_cards": hero_cards_str,
        "board": board_string_representation,
        "hero_invested": hero_invested_display_value,
        "hero_collected": hero_collected,
        "hero_rake": hero_rake,
        "rake": rake_val,
        "jackpot": jackpot_val,
        "final_pot": total_pot_val,
        "hero_net": profit_for_hero,  # Чистый профит Hero (рассчитан от ПОЛНЫХ затрат, для bb/100)
        "hero_showdown": int(any(s_entry["seat_no"] == hero_seat for s_entry in showdown_entries)),
        "seats": seats_info,
        "actions": all_actions,
        "showdowns": showdown_entries,
        "collected_rows": winners_rows,
    }
    return hand_data_dict


def parse_file(path: str) -> List[Dict[str, Any]]:
    """Парсит все раздачи из файла."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_text_content = f.read()
    except FileNotFoundError:
        print(f"Ошибка: Файл не найден по пути: {path}")
        return []
    except Exception as e:
        print(f"Ошибка при чтении файла {path}: {e}")
        return []

    raw_hand_histories = split_raw_hands(raw_text_content)
    parsed_hands = []
    for i, h_text in enumerate(raw_hand_histories):
        try:
            parsed_hands.append(parse_hand(h_text))
        except Exception as e:
            hand_id_match = RE_HAND_START.match(
                h_text.splitlines()[0] if h_text.splitlines() else ""
            )
            hand_id_str = (
                hand_id_match.group("hand_id")
                if hand_id_match
                else f"Неизвестный ID, раздача #{i+1}"
            )
            print(f"Ошибка при парсинге раздачи {hand_id_str}: {e}")
    return parsed_hands


def insert_hands_and_collected(parsed_hands, db_path):
    print(f"Пишу в БД: {db_path}")
    cx = sqlite3.connect(db_path)
    cur = cx.cursor()
    for h in parsed_hands:
        # Если у тебя есть отдельная логика записи рук в таблицу hands — вызывай её тут тоже!
        # cur.execute(...)   # <-- твоя вставка раздачи в hands, если надо
        # Сохраняем победителей в collected
        if h.get("collected_rows"):
            cur.executemany(
                """
                INSERT OR IGNORE INTO collected (hand_id, seat_no, amount)
                VALUES (?, ?, ?)
                """,
                h["collected_rows"],
            )
    cx.commit()
    cx.close()


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) > 1:
        FILE_PATH = sys.argv[1]
    else:
        FILE_PATH = "bbline/assets/test_session.txt"
        print(f"Путь к файлу не передан как аргумент, используется тестовый путь: {FILE_PATH}")
    DB_PATH = Path(__file__).resolve().parents[1] / "database" / "bbline.sqlite"
    parsed_hands_list = parse_file(FILE_PATH)
    insert_hands_and_collected(parsed_hands_list, str(DB_PATH))
    print("✅  winners_rows записаны в collected")
    if parsed_hands_list:
        for hand_dict_result in parsed_hands_list:
            print(json.dumps(hand_dict_result, indent=2))
            print(
                f"--- Hero Net для {hand_dict_result['hand_id']}: {hand_dict_result['hero_net']} ---"
            )
            print("-" * 80)

        total_net = sum(h["hero_net"] for h in parsed_hands_list if h.get("hero_net") is not None)
        num_hands = len(parsed_hands_list)
        bb_size = (
            parsed_hands_list[0]["limit_bb"]
            if num_hands > 0 and parsed_hands_list[0].get("limit_bb")
            else 0.02
        )

        if num_hands > 0 and bb_size > 0:
            bb_per_100 = (total_net / num_hands) * (100 / bb_size)
            print(f"\nОбщий hero_net: ${total_net:.2f}")
            print(f"Количество раздач: {num_hands}")
            print(f"Размер BB: ${bb_size:.2f}")
            print(f"Примерный bb/100: {bb_per_100:.2f}")
        else:
            print("\nНедостаточно данных для расчета bb/100.")

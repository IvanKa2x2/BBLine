# bbline/parse/hand_parser.py
"""
GGPoker HH → dict по схемам BBLine.
▪ «site» намеренно жёстко = 'ggpoker'
▪ покрывает NLHE 6-max / 9-max, Hero-only, без мульти-бордов
▪ для скорости и простоты — чистые regex + state-machine

⚠️  Это лишь каркас MVP:
    • hero_net считается только по строкам «collected / won / lost» в SUMMARY
    • EV-diff, Uncalled bet, All-in not tracked (сделаем позже в computed_pass#2)
"""

import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from collections import defaultdict


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
RE_SEAT_WON = re.compile(r"^Seat\s+\d+:\s+(?P<player>.+?)\s+won\s+\(\$(?P<amt>\d+\.\d+)\)")
RE_SHOWS_COLLECTED = re.compile(r"^Hero: shows .*? collected \$?(?P<amt>\d+\.\d+)")
RE_TOTAL_POT = re.compile(
    r"Total pot \$?(?P<total>\d+\.\d+) \| Rake \$?(?P<rake>\d+\.\d+).*?(?:Jackpot \$?(?P<jackpot>\d+\.\d+))?"
)


# ------------------------------------------------------------
def normalize_player_name(name):
    name = name.strip()
    name = re.sub(r"\s*\(.*\)$", "", name)
    name = name.rstrip(":")
    return name


def split_raw_hands(text: str) -> List[str]:
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
    seat_map_name_to_num, seats, seat_map_num_to_name = {}, [], {}
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
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
    return dt.replace(tzinfo=timezone.utc).isoformat(timespec="seconds")


def parse_actions(
    action_lines: List[str], seat_map: Dict[str, int], street: str, order_start: int
) -> Tuple[List[Dict[str, Any]], int]:
    actions = []
    order_no = order_start
    street_commit = defaultdict(float)
    for ln in action_lines:
        m = RE_ACTION.match(ln)
        if not m:
            continue
        player = normalize_player_name(m.group("player"))
        act, amount = None, None

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
                    "allin": 0,  # суффикс не используешь пока
                }
            )
            order_no += 1
    return actions, order_no


def calculate_invested(actions: list[dict], hero_seat: int) -> float:
    """
    Сколько реально ушло из-стека героя (H2N-логика):

    • POST_SB / POST_BB копятся в buffer
    • Как только встретили CALL / BET / RAISE —
      считаем ход добровольным → добавляем buffer + сам amount
    • Если добровольного действия так и не было, блайнды сгорают → invest = 0
    """
    posted_blinds = 0.0
    invested = 0.0
    voluntary = False

    for a in actions:
        if a["seat_no"] != hero_seat:
            continue
        if a["act"].startswith("POST_"):
            posted_blinds += a["amount"] or 0.0
        elif a["act"] in {"CALL", "BET", "RAISE"}:
            voluntary = True
            invested += a["amount"] or 0.0

    if voluntary:
        invested += posted_blinds  # прибавляем посты только если был экшен

    return round(invested, 2)


def parse_hand(raw: str) -> dict:
    """
    Парсит одну HH в dict. hero_net = win-loss, как в H2N.
    """
    hero_uncalled = 0.0
    hero_collected = 0.0  # ← собираем сумму забранную героем, потом вычтем затраты
    collected_set = set()
    lines = [ln.rstrip() for ln in raw.splitlines() if ln.strip()]

    m = RE_HAND_START.match(lines[0])
    if not m:
        raise ValueError("Bad HH header")
    hand_id = m.group("hand_id")
    bb = float(m.group("bb"))
    date_iso = utc_iso(m.group("date"), m.group("time"))

    m_btn = next((RE_TABLE_BUTTON.match(ln) for ln in lines if "button" in ln.lower()), None)
    button_seat = int(m_btn.group("button")) if m_btn else -1

    first_posts_idx = next((i for i, ln in enumerate(lines) if RE_POST_BLIND.match(ln)), len(lines))
    seat_block = lines[2:first_posts_idx]
    seat_map_name_to_num, seats, seat_map_num_to_name = parse_seat_block(seat_block)

    # -- ищем Hero --
    hero_player_key = None
    hero_seat = -1
    for s in seats:
        if "Hero" in normalize_player_name(s["player_id"]):
            hero_player_key = normalize_player_name(s["player_id"])
            hero_seat = s["seat_no"]
            break
    if not hero_player_key:
        hero_player_key = "Hero"

    hero_cards = None
    for ln in lines:
        m = RE_DEALT_HERO.match(ln)
        if m:
            hero_cards = m.group("card1") + m.group("card2")
            break

    actions, showdowns = [], []
    board_cards = {"FLOP": [], "TURN": [], "RIVER": []}
    street_state, order_no = "PREFLOP", 0
    street_lines: List[str] = []

    RE_SHOWDOWN = re.compile(
        r"(?:Seat\s+(?P<seat>\d+):\s+)?(?P<player>\S+).*?show(?:ed|s)\s+\[(?P<card1>\w{2})\s+(?P<card2>\w{2})\]"
    )

    for ln in lines:
        if ln.startswith("***"):
            if street_lines:
                acts, order_no = parse_actions(
                    street_lines, seat_map_name_to_num, street_state, order_no
                )
                actions.extend(acts)
                street_lines = []
            m_board = RE_STREET_BOARD.match(ln)
            if m_board:
                street_state = m_board.group("street")
                cards = m_board.group("cards").split()
                board_cards[street_state] = cards
                if m_board.group("turnriver"):
                    board_cards[street_state].append(m_board.group("turnriver"))
                continue

        m_uncalled = RE_UNCALLED.match(ln)
        if m_uncalled and normalize_player_name(m_uncalled.group("player")) == hero_player_key:
            hero_uncalled += float(m_uncalled.group("amt"))

        # --- шоудаун ---
        m_sd = RE_SHOWDOWN.search(ln)
        if m_sd:
            player = normalize_player_name(m_sd.group("player"))
            cards = m_sd.group("card1") + m_sd.group("card2")
            seat = seat_map_name_to_num.get(player, -1)
            if seat == -1 and m_sd.group("seat"):
                seat = int(m_sd.group("seat"))
            if seat == -1:
                print(
                    f"[WARN] Не найден seat_no для игрока '{player}' в руке {hand_id}, seat_map: {seat_map_name_to_num}"
                )
                continue
            if not any(s["seat_no"] == seat for s in showdowns):
                showdowns.append({"seat_no": seat, "cards": cards, "won": None})

        # --- hero_collected --- (а не hero_net!)
        m_coll = RE_COLLECTED.match(ln)
        m_won = RE_WON.match(ln)
        m_sc = RE_SHOWS_COLLECTED.match(ln)
        m_sw = RE_SEAT_WON.match(ln)

        amt = None
        if m_coll and normalize_player_name(m_coll.group("player")) == hero_player_key:
            amt = float(m_coll.group("amt"))
        elif m_won and normalize_player_name(m_won.group("player")) == hero_player_key:
            amt = float(m_won.group("amt"))
        elif m_sc:
            amt = float(m_sc.group("amt"))
        elif m_sw and normalize_player_name(m_sw.group("player")) == hero_player_key:
            amt = float(m_sw.group("amt"))

        if amt is not None and amt not in collected_set:
            hero_collected += amt
            collected_set.add(amt)

        street_lines.append(ln)

    if street_lines:
        acts, _ = parse_actions(street_lines, seat_map_name_to_num, street_state, order_no)
        actions.extend(acts)

    total_pot, rake, jackpot = None, 0.0, 0.0
    for ln in lines:
        m = RE_TOTAL_POT.search(ln)
        if m:
            total_pot = float(m.group("total"))
            rake = float(m.group("rake"))
            if m.group("jackpot"):
                jackpot = float(m.group("jackpot"))
            break

    flop = "".join(board_cards["FLOP"])
    turn = "".join(board_cards["TURN"][-1:])
    river = "".join(board_cards["RIVER"][-1:])
    board_str = "|".join(filter(None, [flop, turn, river]))

    hero_invested = calculate_invested(actions, hero_seat) - hero_uncalled

    profit = round(hero_collected - hero_invested, 2)  # ← вот тут чистый win/loss!

    hand_dict = {
        "hand_id": hand_id,
        "site": "ggpoker",
        "game_type": "NLHE",
        "limit_bb": bb,
        "datetime_utc": date_iso,
        "button_seat": button_seat,
        "hero_seat": hero_seat,
        "hero_name": hero_player_key,
        "hero_cards": hero_cards,
        "board": board_str,
        "hero_invested": hero_invested,
        "rake": rake,
        "jackpot": jackpot,
        "final_pot": total_pot,
        "hero_net": profit,  # <-- только это поле используется дальше для bb/100 и profit!
        "hero_showdown": int(any(s["seat_no"] == hero_seat for s in showdowns)),
        "seats": seats,
        "actions": actions,
        "showdowns": showdowns,
    }
    return hand_dict


def parse_file(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        raw_text = f.read()
    hands_raw = split_raw_hands(raw_text)
    return [parse_hand(h) for h in hands_raw]


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) > 1:
        PATH = sys.argv[1]
    else:
        PATH = "bbline/assets/test_session.txt"
    for hh in parse_file(PATH):
        print(json.dumps(hh, indent=2))
        print("-" * 80)

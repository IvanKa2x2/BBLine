import json
import os

INPUT_FILE  = "exports/hands_full.jsonl"
OUTPUT_FILE = "exports/hands_gpt.txt"
os.makedirs("exports", exist_ok=True)

def format_action(a, seat_pos_map, hero_seat):
    pos = seat_pos_map.get(a["seat"], f"seat {a['seat']}")
    actor = "Hero" if a["seat"] == hero_seat else pos
    amount = f" {round(a['amount_bb'], 1)}bb" if a["amount_bb"] > 0 else ""
    return f"{a['street']}: {actor} → {a['action']}{amount}"

def to_text(entry):
    hand = entry["hand"]
    hero = entry["hero"]
    flags = entry.get("flags", {})
    actions = entry["actions"]
    opponents = entry.get("opponents", [])
    board = entry.get("board", [])

    board_str = " ".join(card for card in board[:3] if card) + " | " + \
                (board[3] or "") + " | " + (board[4] or "") if board else ""

    hero_cards = f"{hero['card1']} {hero['card2']}" + (" (сuited)" if hero.get("suited") else " (разномастные)")

    fl = [k for k, v in flags.items() if v]
    flag_line = "❌ " + ", ❌ ".join(fl) if fl else "✅ Без флагов"

    # строим карту: seat → позиция
    seat_pos_map = {}
    for opp in opponents:
        seat_pos_map[opp.get("seat", -1)] = opp["player_pos"]

    # пробуем угадать Hero seat
    hero_seat = None
    for a in actions:
        if a["street"] == "P" and "Hero" in a.get("action", ""):
            hero_seat = a["seat"]
            break
        hero_seat = -1

    act_lines = [format_action(a, seat_pos_map, hero_seat) for a in actions]

    opp_lines = [f"- {opp['player_pos']} ({opp['stack_bb']}bb)" for opp in opponents]

    return f"""Раздача: {hand['hand_id']} ({hand['hero_pos']}), стек {hero['start_stack_bb']}bb → {hero['net_bb']}bb

Карманка: {hero_cards}  
Борд: {board_str}  
Префлоп: {hero.get('preflop_action', '?')}  
Флаги: {flag_line}

📜 Действия:
""" + "\n".join(act_lines) + """

Оппоненты:
""" + "\n".join(opp_lines) + f"""

Общий банк: {hand['pot_total']}bb | Рейк: {hand['rake']}bb  
---

🧠 Проанализируй раздачу: какие были ошибки? Что можно было сыграть лучше?
"""

def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        lines = f.readlines()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for line in lines:
            entry = json.loads(line)
            out.write(to_text(entry))
            out.write("\n" + "=" * 80 + "\n\n")

    print(f"✅ GPT-файл готов: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

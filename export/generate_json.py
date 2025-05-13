"""
Экспорт полного датасета раздач Hero → JSONL
Структура строго соответствует таблице из гайда.
"""

import os, json, sqlite3
from collections import defaultdict, Counter

DB_PATH   = "db/bbline.sqlite"
OUT_FILE  = "exports/hands_full.jsonl"
os.makedirs("exports", exist_ok=True)


def fetchall(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(query, params).fetchall()


def build_aggregates():
    """A‑ля HUD‑статы Hero на основе players/actions."""
    rows = fetchall("""
        SELECT player_pos, preflop_action
        FROM players
        WHERE player_id LIKE '%Hero%'
    """)
    cnt = Counter(r["preflop_action"] for r in rows)
    total = len(rows) or 1
    return {
        "VPIP": round((cnt["call"] + cnt["raise"]) / total * 100, 1),
        "PFR":  round(cnt["raise"] / total * 100, 1),
        # минимальный набор, остальное считаешь по желанию
    }


def main():
    # кеш: hand_id → базовые поля раздачи
    hand_base = {}
    for r in fetchall("""
        SELECT hand_id, date_ts, sb, bb,
               hero_pos, btn_seat,
               pot_total, pot_rake
        FROM hands
    """):
        stakes = f"{r['sb']}/{r['bb']}"
        hand_base[r["hand_id"]] = {
            "hand_id":  r["hand_id"],
            "date_ts":  r["date_ts"],
            "stakes":   stakes,
            "BTN_seat": r["btn_seat"],
            "hero_pos": r["hero_pos"],
            "pot_total": r["pot_total"],
            "rake":      r["pot_rake"],
        }

    # hero‑карты
    hero_cards = {r["hand_id"]: dict(r) for r in fetchall("SELECT * FROM hero_cards")}

    # действия: hand_id → список действий (упорядоченных)
    actions_by_hand = defaultdict(list)
    for r in fetchall("SELECT hand_id, street, seat, action, amount_bb FROM actions ORDER BY action_id"):
        actions_by_hand[r["hand_id"]].append(dict(r))

    # игроки
    players_by_hand = defaultdict(list)
    for r in fetchall("""
        SELECT hand_id, seat, player_pos, player_id,
               start_stack_bb, end_stack_bb
        FROM players
    """):
        players_by_hand[r["hand_id"]].append(dict(r))

    # агрегаты сразу
    aggregates = build_aggregates()

    with open(OUT_FILE, "w", encoding="utf-8") as f_out:
        for hand_id, base in hand_base.items():
            hero_info = next((p for p in players_by_hand[hand_id] if "Hero" in p["player_id"]), None)
            if not hero_info:   # пропускаем, если Hero нет
                continue

            # hero‑блок
            hero_block = {
                "card1": hero_cards.get(hand_id, {}).get("card1"),
                "card2": hero_cards.get(hand_id, {}).get("card2"),
                "suited": hero_cards.get(hand_id, {}).get("suited"),
                "start_stack_bb": hero_info["start_stack_bb"],
                "end_stack_bb":   hero_info.get("end_stack_bb"),
                "invested_bb":    hero_info.get("invested_bb"),
                "net_bb":         hero_info.get("net_bb"),
                "preflop_action": hero_info.get("preflop_action"),
            }

            # действия и pot‑size‑after
            pot = 0.0
            acts = []
            for a in actions_by_hand[hand_id]:
                pot += a["amount_bb"]
                acts.append({
                    "street": a["street"],
                    "seat":   a["seat"],
                    "action": a["action"],
                    "amount_bb": a["amount_bb"],
                    "pot_size_bb_after": round(pot, 2),
                })

            # оппоненты
            opps = [
                {
                    "player_pos": p["player_pos"],
                    "stack_bb":   p["start_stack_bb"],
                    # action sequence можно добавить, если нужно
                }
                for p in players_by_hand[hand_id] if "Hero" not in p["player_id"]
            ]

            out = {
                "hand":      base,
                "hero":      hero_block,
                "actions":   acts,
                "opponents": opps,
                "aggregates": aggregates,   # одинаковы для всех, можно вынести
                # "benchmark": {...}        # добавь, если есть сторонний файл GTO
            }
            f_out.write(json.dumps(out, ensure_ascii=False) + "\n")

    print(f"✅ Экспортировано: {len(hand_base)} рук → {OUT_FILE}")

if __name__ == "__main__":
    main()

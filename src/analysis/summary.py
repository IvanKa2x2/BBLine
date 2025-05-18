# analysis/summary.py единый отчет по Hero (винрейт, позиции, действия, динамика)
from analysis.utils import fetchall, print_table, validate_table


def summary():
    validate_table("players")
    stats = fetchall(
        """
        SELECT COUNT(DISTINCT hand_id) AS hands, SUM(net_bb) AS net_bb
        FROM players WHERE player_id LIKE '%Hero%'
    """
    )[0]
    if not stats or stats["hands"] == 0:
        print("❌ Нет данных по Hero")
        return
    hands, net_bb = stats["hands"], stats["net_bb"]
    winrate = (net_bb / hands) * 100 if hands else 0
    print(f"\n🧠 Hero сыграл {hands} рук\n📈 Итог: {net_bb:+.2f} BB | {winrate:+.2f} bb/100")


def get_hero_seat(hand_id):
    # Возвращает seat (номер места) для Hero в конкретной раздаче
    row = fetchall("SELECT seat FROM players WHERE hand_id = ? AND player_id = 'Hero'", (hand_id,))
    return row[0]["seat"] if row else None


def by_position():
    validate_table("players")
    validate_table("hands")
    rows = fetchall(
        """
        SELECT h.hero_pos, COUNT(*) AS hands, SUM(p.net_bb) AS net_bb,
               ROUND((SUM(p.net_bb)*100.0/COUNT()),2) AS bb100
        FROM players p
        JOIN hands h ON h.hand_id = p.hand_id
        WHERE p.player_id LIKE '%Hero%'
        GROUP BY h.hero_pos
    """
    )
    print_table(
        "Winrate по позициям",
        ["Позиция", "Руки", "BB", "bb/100"],
        [(r["hero_pos"], r["hands"], r["net_bb"], r["bb100"]) for r in rows],
    )


def by_action():
    validate_table("players")
    rows = fetchall(
        """
        SELECT preflop_action, COUNT(*) AS hands, SUM(net_bb) AS net_bb,
               ROUND((SUM(net_bb)*100.0/COUNT()),2) AS bb100
        FROM players
        WHERE player_id LIKE '%Hero%' AND preflop_action IS NOT NULL
        GROUP BY preflop_action
    """
    )
    print_table(
        "Net-BB по префлоп-действиям",
        ["Action", "Hands", "Net BB", "bb/100"],
        [(r["preflop_action"], r["hands"], r["net_bb"], r["bb100"]) for r in rows],
    )


def stack_timeline(limit=15):
    validate_table("players")
    validate_table("hands")
    rows = fetchall(
        """
        SELECT h.date_ts, p.hand_id, p.end_stack_bb
        FROM players p
        JOIN hands h ON h.hand_id = p.hand_id
        WHERE p.player_id LIKE '%Hero%'
        ORDER BY h.date_ts
    """
    )
    print_table(
        f"Динамика стека (последние {limit} рук)",
        ["Hand_id", "Stack_bb"],
        [(r["hand_id"], r["end_stack_bb"]) for r in rows[-limit:]],
    )


def top_losing_hands(limit=10):
    validate_table("players")
    validate_table("hands")
    rows = fetchall(
        """
        SELECT h.hand_id, p.net_bb, h.date_ts
        FROM players p
        JOIN hands h ON h.hand_id = p.hand_id
        WHERE p.player_id LIKE '%Hero%'
        ORDER BY p.net_bb ASC
        LIMIT ?
        """,
        (limit,),
    )
    print_table(
        f"Топ {limit} минусовых рук",
        ["Hand_id", "Net BB", "Date"],
        [(r["hand_id"], r["net_bb"], r["date_ts"]) for r in rows],
    )


def vpip_pfr():
    validate_table("players")
    validate_table("actions")
    row = fetchall(
        """
        SELECT 
          COUNT(DISTINCT p.hand_id) AS total_hands,
          COUNT(DISTINCT CASE WHEN a.action IN ('call','raise','bet') THEN p.hand_id END) AS vpip,
          COUNT(DISTINCT CASE WHEN a.action IN ('raise','bet') THEN p.hand_id END) AS pfr
        FROM players p
        JOIN actions a ON a.hand_id = p.hand_id AND a.seat = p.seat
        WHERE p.player_id LIKE '%Hero%'
          AND a.street = 'P'
        """
    )[0]
    if not row or row["total_hands"] == 0:
        print("❌ Нет данных по Hero для VPIP/PFR")
        return
    total = row["total_hands"]
    vpip = row["vpip"]
    pfr = row["pfr"]
    print(f"\nVPIP: {vpip} / {total} = {vpip/total*100:.1f}%")
    print(f"PFR : {pfr} / {total} = {pfr/total*100:.1f}%")


def calc_3bet():
    validate_table("actions")
    validate_table("players")
    hand_ids = [
        row["hand_id"]
        for row in fetchall("SELECT DISTINCT hand_id FROM actions WHERE street = 'P'")
    ]
    total_opp, made_3bet = 0, 0
    for hand_id in hand_ids:
        hero_row = fetchall(
            "SELECT seat FROM players WHERE hand_id = ? AND player_id = 'Hero'", (hand_id,)
        )
        if not hero_row:
            continue
        acts = fetchall(
            """
            SELECT a.seat, p.player_id, a.action
            FROM actions a
            JOIN players p ON a.hand_id = p.hand_id AND a.seat = p.seat
            WHERE a.hand_id = ? AND a.street = 'P'
            ORDER BY a.rowid
        """,
            (hand_id,),
        )
        # 1. Найти первого open-raiser'а (не Hero)
        first_raiser_idx = next(
            (
                i
                for i, act in enumerate(acts)
                if act["action"] == "raise" and act["player_id"] != "Hero"
            ),
            None,
        )
        if first_raiser_idx is None:
            continue  # не было open-raise чужого
        # 2. Найти Hero в списке экшенов ПОСЛЕ open-raise
        hero_action = next(
            (act for act in acts[first_raiser_idx + 1 :] if act["player_id"] == "Hero"), None
        )
        if not hero_action:
            continue
        # 3. Если Hero сделал RAISE в ответ — это 3Bet
        total_opp += 1
        if hero_action["action"] == "raise":
            made_3bet += 1
    percent = (made_3bet / total_opp * 100) if total_opp else 0
    print(f"3Bet%: {made_3bet} / {total_opp} = {percent:.1f}%")


def aggression_factor(street="F"):
    validate_table("actions")
    validate_table("players")
    rows = fetchall(
        """
        SELECT a.action
        FROM actions a
        JOIN players p ON a.hand_id = p.hand_id AND a.seat = p.seat
        WHERE p.player_id = 'Hero' AND a.street = ?
    """,
        (street,),
    )
    bets = sum(1 for r in rows if r["action"] in ("bet", "raise"))
    calls = sum(1 for r in rows if r["action"] == "call")
    if calls == 0:
        print(f"Aggression Factor {street}: нет коллов (делил бы на ноль)")
    else:
        print(f"Aggression Factor {street}: {(bets/calls):.2f}  ({bets} bet/raise, {calls} call)")


def wtsd_wsd():
    validate_table("players")
    validate_table("hands")
    # WTSD — руки, где Hero дошёл до SHOW DOWN
    wtsd_rows = fetchall(
        """
        SELECT p.hand_id, h.showdown, p.won_bb
        FROM players p
        JOIN hands h ON p.hand_id = h.hand_id
        WHERE p.player_id = 'Hero'
    """
    )
    total_hands = len(wtsd_rows)
    n_wtsd = sum(1 for row in wtsd_rows if row["showdown"])
    n_wsd = sum(1 for row in wtsd_rows if row["showdown"] and row["won_bb"] > 0)
    print(f"WTSD: {n_wtsd}/{total_hands} = {n_wtsd/total_hands*100:.1f}%")
    print(f"W$SD: {n_wsd}/{n_wtsd} = {(n_wsd/n_wtsd*100) if n_wtsd else 0:.1f}%")


def cbet_percent():
    validate_table("actions")
    validate_table("players")
    # Найти все руки, где Hero был префлоп-агрессором
    hands = fetchall(
        """
        SELECT hand_id FROM players WHERE player_id = 'Hero' AND preflop_action = 'raise'
    """
    )
    total = 0
    cbets = 0
    for row in hands:
        acts = fetchall(
            """
            SELECT seat, action FROM actions WHERE hand_id = ? AND street = 'F' ORDER BY rowid
        """,
            (row["hand_id"],),
        )
        if not acts:
            continue
        # Seat Hero
        hero_seat = fetchall(
            "SELECT seat FROM players WHERE hand_id = ? AND player_id = 'Hero'", (row["hand_id"],)
        )[0]["seat"]
        # Если первый bet на флопе сделал Hero
        for act in acts:
            if act["action"] == "bet":
                total += 1
                if act["seat"] == hero_seat:
                    cbets += 1
                break
    percent = (cbets / total * 100) if total else 0
    print(f"C-bet%: {cbets}/{total} = {percent:.1f}%")


if __name__ == "__main__":
    summary()
    by_position()
    by_action()
    stack_timeline()
    top_losing_hands()
    vpip_pfr()
    calc_3bet()
    aggression_factor("F")
    aggression_factor("T")
    aggression_factor("R")
    wtsd_wsd()
    cbet_percent()

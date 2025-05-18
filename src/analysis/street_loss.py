# analysis/street_loss.py потери по улицам
from analysis.utils import fetchall, validate_table, print_table


def main():
    validate_table("actions")
    validate_table("players")
    rows = fetchall(
        """
        SELECT a.street, a.action, a.amount_bb
        FROM actions a
        JOIN players p ON a.hand_id = p.hand_id AND a.seat = p.seat
        WHERE p.player_id = 'Hero'
    """
    )
    street_names = {"P": "Preflop", "F": "Flop", "T": "Turn", "R": "River"}
    totals = {code: 0.0 for code in street_names}
    for street, action, amount in rows:
        if action in ("call", "bet", "raise"):
            totals[street] += amount or 0.0
    rows = [(street_names[c], totals[c]) for c in "PFTR"]

    print_table("Потери по улицам", ["Street", "Invested BB"], rows)


if __name__ == "__main__":
    main()

from bbline.analysis.periodic import agg_stats_by_period, top_losing_hands, leaks_by_period


def print_stats(stats):
    print("\nСтатистика по периодам:")
    print("Период | Fold to 3B% | 3B% | C-bet% | Рук")
    print("-" * 50)
    for s in stats:
        print(
            f"{s['period']} | {s['fold_to_3b_pct']:>10.1f} | {s['threebet_pct']:>3.1f} | {s['cbet_flop_pct']:>6.1f} | {s['hands']}"
        )


def print_leaks(leaks):
    print("\nУтечки по периодам:")
    for leak in leaks:
        if leak["leaks"]:
            print(f"{leak['period']}: {', '.join(leak['leaks'])}")


def print_losing_hands(hands):
    print("\nТоп-5 убыточных рук по периодам:")
    for p in hands:
        print(f"\n{p['period']}:")
        for h in p["hands"]:
            print(f"  {h['hand_id']}: {h['hero_net']:.2f}$")


def main():
    # Проверяем по неделям
    print("=== Анализ по неделям ===")
    stats = agg_stats_by_period("week")
    print_stats(stats)
    print_leaks(leaks_by_period("week"))
    print_losing_hands(top_losing_hands("week", 5))

    # Проверяем по месяцам
    print("\n=== Анализ по месяцам ===")
    stats = agg_stats_by_period("month")
    print_stats(stats)
    print_leaks(leaks_by_period("month"))
    print_losing_hands(top_losing_hands("month", 5))


if __name__ == "__main__":
    main()

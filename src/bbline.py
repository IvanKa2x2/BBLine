# bbline.py

import typer
from analysis import summary, hands_stats, street_loss, strong_hands
from core import parser

app = typer.Typer(add_completion=False, help="BBLine CLI — импорт HH и отчёты по Hero.")

@app.command("import")
def import_raw(path: str = typer.Argument("data/raw", help="Папка с .txt для парса")):
    """Импортирует все .txt из папки (рекурсивно), дубликаты игнорятся."""
    parser.find_and_parse_all_txt_files(path)
    typer.echo("✅ Импорт завершён!")

@app.command("report")
def report(
    kind: str = typer.Argument("summary", help="summary | position | action | hands | streets | strong | top_loss"),
    limit: int = typer.Option(10, "--limit", "-l", help="Лимит для топ-отчётов (если нужно)"),
):
    """Быстрые текстовые отчёты прямо в консоль."""
    match kind:
        case "summary":
            summary.summary()
            summary.by_position()
            summary.by_action()
            summary.stack_timeline()
            summary.vpip_pfr()
        case "position":
            summary.by_position()
        case "action":
            summary.by_action()
        case "hands":
            hands_stats.main()
        case "streets":
            street_loss.main()
        case "strong":
            strong_hands.main()
        case "top_loss":
            summary.top_losing_hands(limit)
        case _:
            typer.echo("🤔 Неизвестный отчёт. Доступные: summary, position, action, hands, streets, strong, top_loss")

@app.command("reset")
def reset_db(confirm: bool = typer.Option(False, "--confirm", prompt="Удалить базу?")):
    """Удаляет базу bbline.sqlite (осторожно!)"""
    import os
    if confirm:
        try:
            os.remove("db/bbline.sqlite")
            typer.echo("🗑️ База удалена.")
        except FileNotFoundError:
            typer.echo("❌ База не найдена.")
    else:
        typer.echo("Отмена удаления.")

if __name__ == "__main__":
    app()

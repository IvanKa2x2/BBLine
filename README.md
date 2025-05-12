# BBLine 🧠💣

**BBLine** — твоя личная система анализа покера. Парсит выгрузки с GGPoker, сохраняет все раздачи в базу данных, находит ошибки, считает winrate, и помогает становиться плюсовым шаг за шагом.

## 📦 Возможности

- 🔎 Парсинг `.txt` истории раздач с GGPoker (Hero и оппоненты)
- 💾 Сохранение в SQLite с полной структурой: руки, действия, борд
- 📊 Анализ winrate по позициям, рукам, стеку, showdown %
- ❗️ Обнаружение ошибок: missed C‑bet, spew, bad call и т.п.
- 📈 Визуализация линий (BB-line, EV-line)
- 📤 Генерация Telegram/HTML-отчётов (опционально)

## ⚙️ Установка

```bash
git clone https://github.com/yourusername/BBLine.git
cd BBLine
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

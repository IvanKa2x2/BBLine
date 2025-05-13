🔥 Лови готовый `README.md` для твоего проекта **BBLine** — можно прям вставлять в файл и пушить в GitHub:

---

```markdown
# ♠️ BBLine — Личная GGPoker-база для анализа раздач

**BBLine** — это локальный парсер и аналитическая система, которая превращает твои текстовые истории с GGPoker в структурированную SQLite-базу для глубокой покерной аналитики.

---

## 📦 Возможности

- ✅ Парсинг всех раздач из текстовых логов GGPoker
- ✅ Выделение Hero, стеков, действий и карманок
- ✅ Вычисление позиций (UTG/MP/CO/BTN/SB/BB) для всех игроков
- ✅ Подсчёт `won_bb`, rake, pot, seat, экшенов
- ✅ Удобная структура данных для анализа (`players`, `actions`, `hero_cards`, `hands`)
- ✅ Поддержка кэш-игр 6-max с любым количеством игроков

---

## 📁 Структура проекта

```

BBLine/
├── data/
│   └── raw/                   # Истории сессий GGPoker
├── db/
│   └── bbline.sqlite          # База с разобранными раздачами
├── parser/
│   └── ggparser.py            # Основной парсер .txt-файлов
├── analysis/
│   └── hero\_stats.py          # Скрипты аналитики (winrate, позиции и т.д.)
├── utils/
│   └── db\_schema.py           # Создание структуры базы
├── .gitignore
└── README.md

````

---

## 🚀 Быстрый старт

1. Скопируй файлы .txt из GGPoker в `data/raw/`
2. Запусти парсинг:

```bash
python parser/ggparser.py
````

3. Посмотри winrate:

```bash
python analysis/hero_stats.py
```

---

## 🛠 Требования

* Python 3.9+
* SQLite (входит в Python)
* Библиотеки: `re`, `sqlite3`, `datetime`

---

## 🚫 Игнорируемое

```
venv/
__pycache__/
*.sqlite
*.log
```

(см. `.gitignore`)

---

## 📈 Дальше в планах

* [ ] Парсинг street-by-street инвестиций
* [ ] Экспорт CSV / Excel отчётов
* [ ] Telegram-бот с анализом сессий
* [ ] Визуализация графиков bb/100 и showdown %
* [ ] Топ-5 самых убыточных рук и ситуаций

---

## © Автор

👤 Ivan Kanunnikov
🧠 Telegram: [@ivank567](https://t.me/ivank567)
🎯 Ник в покере: `Ledonec22`

---

**BBLine — чтобы видеть свой покер как на ладони.**

````

---

### 📌 Что делать дальше?

- Сохрани как `README.md`
- Добавь и закоммить:
  
```bash
git add README.md
git commit -m "📘 Add full README"
git push
````

Хочешь ещё автогенерируемую таблицу `hero_cards` с отчётом по рукам — погнали к пункту 3?

Базовый roadmap уже изрядно расширился, теперь ты реально почти на уровне **Hero Hand2Note Lite**.
Вот **обновлённый roadmap для md** (чисто для вставки, учтены: фильтры, LeakFinder Lite с тегами и примерами, HandsTable, Replayer):

---

## BBLine Poker — Roadmap v0.2 (Hero‑Only Tracker)

---

### 0. **Что готово:**

* Импорт HH GGPoker (NLHE, 6-max, Hero-only)
* Парсинг, экстракция экшенов, showdown’ов, банк/стек/рейк, board/карты, позиции
* SQLite база: hands, computed\_stats, actions, showdowns, tags и др.
* Корректные покерные метрики (VPIP, PFR, 3bet, Fold to 3bet, WTSD, WSD, WWSF)
* Расчёт profit (USD, bb), hero\_rake, bb/100 — всё как в H2N/CC
* **Streamlit Dashboard Overall:** ключевые метрики, графики, быстрые фильтры по дате, лимиту, позиции
* **HandsTable:** интерактивная таблица всех рук с фильтрами (дата, лимит, позиция)
* **LeakFinder Lite:** автоматический поиск и тегирование ликов (overfold vs 3bet, low 3bet, over-cbet и др.), кнопка «показать примеры рук»
* **Тегирование в базе:** найденные лики сохраняются в таблицу tags, возможна фильтрация по типу лика
* **Replayer (replay\_one.py):** просмотр любой руки через CLI или Streamlit (по hand\_id), все экшены по улицам

---

### 1. **Следующие шаги (Roadmap — Next Steps)**

#### 1.1. **LeakFinder Pro**

* [ ] Добавить новые правила: Overcall 3bet OOP, Fold BB to Steal >70%, Under-CBet Turn <30%, Overfold River, и т.д.
* [ ] Визуализировать heat-map ликов по позициям и лимитам

#### 1.2. **Примеры рук/разбор**

* [ ] Кнопка "Открыть в реплеере" прямо из таблицы/LeakFinder
* [ ] Быстрый просмотр (min/max/рандом) по каждой категории/тегу

#### 1.3. **Postflop/Street Analytics**

* [ ] Метрики по street: CBet/Fold/Call/Check-Raise/Donk, WSD, WTSD, WWSF, Agg, AF по flop/turn/river
* [ ] Детализация по линиям розыгрыша и структурам борда

#### 1.4. **Экспорт и отчёты**

* [ ] PDF/CSV-отчёты по выбранным фильтрам, по ликам, по рукам
* [ ] Экспорт в Anki, Telegram-интеграция

#### 1.5. **GUI и UX**

* [ ] Вынести фильтры в отдельный блок/sidebar, интерактивный replayer, группировка по тегам/рукам
* [ ] Расширить визуал: типы рук, подсветка ликов, "маркеры" EV, equity

#### 1.6. **Автоматизация и бэкапы**

* [ ] Резервные копии базы, auto-import HH
* [ ] Автоматизация обновления и расчётов при появлении новых рук

---

### 2. **Текущие приоритеты**

* Проверять все метрики и фильтры на совпадение с Hand2Note/Poker Copilot (bb/100, WTSD, WWSF, т.д.)
* Дебажить edge-case раздачи (мультиборды, много showdown’ов, rare actions)
* Улучшить реплеер (добавить SVG-карточки, визу борда/экшенов, hotkeys)
* Упростить поддержку новых фильтров/метрик для будущих расширений

---

### 3. **Структура проекта (v0.2)**

```
bbline/
├── ingest/                  # импорт и парсинг HH
├── parse/                   # парсер hand_parser.py
├── database/
│   └── bbline.sqlite
├── analysis/                # анализ и агрегаты
├── export/                  # экспорт дампов, отчётов
├── replayer/
│   └── replay_one.py        # быстрый реплеер (CLI + Streamlit)
├── leakfinder.py            # LeakFinder Lite (+теги, примеры)
├── dashboard_data.py        # расчёт метрик для дашборда
├── hands_table.py           # таблица всех рук (для UI)
├── main.py                  # основной Streamlit-UI (Dashboard+)
└── requirements.txt
```

---

**Если хочешь — добавим подробные примеры запуска, код-сниппеты для каждой фичи, ссылки на демо-скрины. Готово для вставки в README.md/roadmap.md.**
Пиши, если что-то поменять/добавить!

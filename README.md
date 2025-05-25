# BBLine: Poker Hero-Only Hand Analyzer

**(MVP Hero Tracker — Roadmap Progress & Next Steps)**

---

## 1. Что уже реализовано

### 1.1. **Импорт раздач**

* Парсер HH с GGPoker (NLHE, 6-max, Hero-only, single-board).
* Чистая разбивка HH на отдельные руки.
* Выделение всех ключевых полей: `hand_id`, `datetime_utc`, позиции, карты, борд, стек, банк, рейк и т.д.
* Аккуратный разбор позиций/игроков — маппинг seat ↔ name.

### 1.2. **Сбор действий и шоудаунов**

* Экстракция действий в раздаче с деталями (street, order, act, amount, allin flag).
* Поддержка всех типов действий (BET/CALL/RAISE/POST/BLIND/FOLD/CHECK).
* Корректная привязка showdown’ов (showdown hands, победители).

### 1.3. **База данных SQLite**

* Схема: `hands`, `seats`, `actions`, `showdowns`, `computed_stats`.
* Поля по каждой раздаче:

  * `hero_net`, `final_pot`, `rake`, `jackpot`
  * **NEW:** `hero_invested`, `hero_rake`, `net_bb` (расчёт и хранение)
* Счётчики для покерных метрик: VPIP, PFR, 3Bet, Fold to 3Bet, CBet, WTSD, WSD, WWSF и т.д.

### 1.4. **Рассчёт профита и winrate**

* Пересчёт вложений: `hero_invested` (только добровольные вложения; принудительные блайнды можно исключать/включать как в H2N).
* Реализация расчёта доли рейка героя (`hero_rake`) по пропорции вложений.
* Автоматическое обновление поля `net_bb` (винрейт в блайндах).
* Скрипт для пересчёта агрегированных статов: **`rebuild_computed.py`**.

### 1.5. **Анализ по базе**

* SQL-агрегаты: винрейт bb/100, EV bb/100, total winnings, уплаченный рейк.

---

## 2. Куда двигаться дальше (Roadmap — Next Steps)

### 2.1. **Дообработка парсера**

* [ ] Full support для multi-board (если появится необходимость).
* [ ] Улучшить парсер для edge-case HH, экзотических действий, ошибок разметки.
* [ ] Дотащить разбор all-in EV и EV-diff (для EV bb/100 как в H2N/GTO+).

### 2.2. **Реализация фильтров и позиций**

* [ ] Фильтры по позициям (BTN, CO, MP и т.д.).
* [ ] Вынести базовую аналитику по позициям (RFI%, Steal%, Fold BB to Steal).
* [ ] Поддержка кастомных фильтров (по размеру пота, борду, экшену и т.д.).

### 2.3. **Графики и Dashboard**

* [ ] Реализация простого дашборда (графики winrate, winnings, рейк, EV bb/100).
* [ ] Export отчётов в PDF/CSV.

### 2.4. **LeakFinder Lite**

* [ ] Внедрить автоанализ ликов на основе сыгранных рук (минимум 3-5 правил: Overfold, Overcall, Low 3bet и пр.).

### 2.5. **Postflop Stats**

* [ ] Разбор и анализ постфлоп линий: Cbet/Fold/Call/Check-Raise, WSD, WTSD, WWSF.
* [ ] Статы для каждого street (флоп, терн, ривер).

### 2.6. **Backup/Auto-Update**

* [ ] Резервные копии базы.
* [ ] Автоматический импорт и обновление базы по новым HH.

### 2.7. **Экспорт и интеграция**

* [ ] Экспорт в Anki, PDF, для обучения.
* [ ] Готовность к интеграции с Telegram-ботом или веб-интерфейсом.

---

## 3. Текущие проблемы и приоритеты

* ⚠️ Важно: **Сравнивать каждую метрику с H2N и искать любые расхождения** (особенно bb/100, winrate, EV).
* Сравнить/отдебажить подсчёт вложений (`hero_invested`), убедиться, что всё как в H2N.
* Проверить обработку edge-case (руки с несколькими шоудаунами, необычные раздачи, ошибки в HH).

---

## 4. Запуск/использование

```bash
# Импортируем новые раздачи:
python -m bbline.ingest.ggpoker_import <путь_к_файлу>

# Пересчитываем стату и winrate:
python -m bbline.analysis.rebuild_computed

# Агрегаты по winrate/rake (через SQLite или готовый скрипт)
SELECT ROUND(SUM(net_bb)/COUNT(*)*100, 2) AS bb_per_100 FROM hands WHERE net_bb IS NOT NULL;
SELECT ROUND(SUM(hero_rake), 2) AS rake_paid FROM hands;
```

---

## 5. Краткая памятка по стилю кода

* Все действия — с комментами, минимум «магии» в расчётах.
* Любая бизнес-логика (особенно по winrate, рейку, вложениям) максимально прозрачна.
* Парсер легко дебажить: можно добавить print-лог, вывести dict любой руки.

---



Структура проекта:
bbline/
├── ingest/                  # загрузка и парсинг рук
│   └── ggpoker_import.py
├── parse/                   # выделение данных из рук
│   └── hand_parser.py
├── database/
│   └── bbline.sqlite
├── analysis/                # анализ раздач
│   └── analyzer.py
├── replayer/                # покерный реплеер (raw MVP)
│   └── replay_one.py
├── export/
│   └── generate_json.py     # экспорт дампа в JSONL
├── assets/                  # тестовые раздачи
│   └── test_hand_01.txt
├── main.py                  # точка входа
└── requirements.txt

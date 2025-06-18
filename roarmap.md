# **BBLine Poker — 24-Month Roadmap (Hero-Only Tracker)**

> *Сделал одну цельную, “боевую” дорожную карту. Всё готово к копипасту в `README.md` / `roadmap.md`. Завершённые пункты пометил **(done)**. Под-шаги разбиты логически — захватывай и гони код!*

---

## ⏱️ Легенда

| Шорт             | Значение                              |
| ---------------- | ------------------------------------- |
| **M**            | номер месяца с момента старта проекта |
| **vX.Y**         | версия приложения                     |
| **E1 / E2 / E3** | крупные этапы («Эпик-релизы»)         |
| ✔                | выполнено                             |

---

## M0 – M2 · **v0.1 MVP – Foundations** ✔

### Что сделано

* Импорт HH GGPoker (NLHE 6-max, Hero-only) **(done)**
* Полный парсинг: экшены, шоудауны, банк/стек/рейк, board/карты, позиции **(done)**
* **SQLite**: `hands`, `computed_stats`, `actions`, `showdowns`, `tags`, … **(done)**
* Базовые метрики (VPIP, PFR, 3-bet, WTSD, WSD, WWSF) **(done)**
* Profit (USD/bb), bb/100, hero rake **(done)**
* **Streamlit Dashboard Overall** + быстрая фильтрация **(done)**
* CLI/Streamlit **Replayer raw** **(done)**

### Шаги по шлифовке

1. **Парсер edge-cases** — мульти-борды, экзотические линии.
2. 80 %+ unit-test coverage (pytest + SQLite fixtures).

---

## M3 – M4 · **v0.2 – Visibility & Filters** *(текущая работа)*

### Главные цели

* Positions-движок (уже в парсере)
* **Filters v1** (дата · лимит · позиция)
* EV vs Real-Profit график
* Тёмная тема UI

### Под-шаги

#### 🔍 HandsTable

* [ ] Кнопки **“Replay”** и **“Export JSON”** для каждой руки.
* [ ] Карты-иконки вместо `3h6c`.
* [ ] Выравнивание колонок / стилей под H2N.

#### 🩹 LeakFinder Lite

* [ ] Теги: *Over-fold vs 3-bet*, *Low 3-bet*, *Over-cbet*, …
* [ ] Кнопка **“Показать примеры”** → фильтр по тегу.

#### 🎬 Replayer v2

* [ ] SVG-карты, борд, стеки, hotkeys.

#### ⚙️ DX & Quality

* [ ] Sidebar-фильтры.
* [ ] Сравнить метрики c Hand2Note / Poker Copilot.
* [ ] Авто-импорт новых HH + пересчёт стат.

---

## M5 – M6 · **v0.3 – LeakFinder Pro & Tilt-Detector**

* **LeakFinder Pro**

  * Новые правила: *Over-call 3-bet OOP*, *Fold BB to Steal > 70 %*, *Under-CBet Turn < 30 %*, *Over-fold River*, …
  * Heat-map ликов по позициям/лимитам.
* **Tilt-детектор** (стрим показателей, alert-триггеры).
* **Экспорт**

  * PDF/CSV по фильтрам и ликам.
  * Anki-карточки, Telegram-бот.

---

## M7 – M8 · **v0.4 – Postflop Lines & Heatmaps**

* Postflop Line классификация.
* Street-метрики: CBet/Fold/Call/CR/Donk, Agg, AF per street.
* Profit-Heatmap по бордам и линиям.
* **Auto-Backup** DB + HH.

---

## M9 · **v0.5 – Release E1 (full)**

* **Micro-drills** (генерация рук по ликам).
* Финальный Anki-экспорт.
* **Auto-Updater** (pip wheel + hash-check).
* Публичный **Beta-релиз**.

---

## M10 – M11 · **v0.6 – Service Skeleton**

* Docker-compose: `ingest-svc` ↔ `db-svc`.
* CI-pipeline (GitHub Actions).
* Remote Auto-Backup (S3/Backblaze).

---

## M12 · **v1.0 – E2 MVP**

* `analytics-svc` API + **ui-gateway** (FastAPI).
* **NATS** для событий.
* Vision-Capture POC (скрин-грабер live-сессии).

---

## M13 – M15 · **v1.1 – Equity GPU Engine & SDK**

* CUDA/OpenCL Equity-engine (batch sim).
* **Plugin SDK** (данные + виджеты).
* **Grafana** дашборды (Prometheus metrics).

---

## M16 · **v1.2 – GPT-svc + Redpanda**

* Локальный `gpt-svc` с облачным fallback.
* Переключение стрима на **Redpanda** (Kafka-compatible).

---

## M17 – M18 · **v1.5 – Release E2 (full)**

* Полный CI/CD (multi-svc).
* Локальный скейлинг до **100 k рук/с** ingest.

---

## M19 · **v1.6 – Edge-Agent Alpha**

* Edge-агент для live-cap HH.
* **S3 Data Lake** скелет (Iceberg/Delta).

---

## M20 · **v2.0 – E3 Beta (Cloud)**

* **Cloud DuckDB** хранилище.
* VectorDB GPT-портал (данные + chat).
* PWA Frontend (Next.js + TWA).

---

## M21 – M23 · **v2.1 – Marketplace & Multi-Tenant**

* Marketplace плагинов/дашбордов.
* Мульти-тенант SaaS-режим.
* Billing (Stripe / Paddle).

---

## M24 · **v2.2 – Public Launch**

* TradingView-style публичный релиз.
* Партнёрские интеграции и реклама.

---

### 🔄 Постоянные приоритеты (“always-on”)

* Паритет метрик с H2N.
* Автотесты > 85 % покрытие.
* Регулярные бэкапы и DR план.
* Docs + demo-скрины в wiki.

---

> **Погнали!** Если нужно детальнее расписать любой блок или добавить сниппеты запуска — пиши, сделаем.

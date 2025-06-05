"""
Создаёт структуру базы BBLine-MVP c упором на те же метрики, что Hand2Note даёт
в «Статистика / Отчёты / Сессии» (см. скрины).

▪ hero-only, но сохраняем все сиды ― пригодится для мульти-героя/оппов.
▪ всё в одной базе SQLite, поэтому сразу добавляем индексы для быстрой агрегации.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("bbline.sqlite")
DB_PATH.parent.mkdir(exist_ok=True, parents=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ---------- HAND LEVEL ----------
cur.executescript(
    """
PRAGMA foreign_keys = ON;

/* 1. hands — «шапка» раздачи */
CREATE TABLE IF NOT EXISTS hands (
    hand_id       TEXT    PRIMARY KEY,     -- HD2268701401
    site          TEXT    NOT NULL,        -- ggpoker / stars / etc
    game_type     TEXT    NOT NULL,        -- NLHE, PLO
    limit_bb      REAL    NOT NULL,        -- 0.02
    datetime_utc  TEXT    NOT NULL,        -- 2025-04-16T18:14:33Z
    button_seat   INTEGER NOT NULL,        -- чей BTN (1-6)
    hero_seat     INTEGER NOT NULL,        -- где сидит Hero
    hero_name     TEXT    NOT NULL,        -- “Hero”
    hero_cards    TEXT,                    -- ‘5s9s’
    board         TEXT,                    -- ‘6hQc8h|8c|3d’
    hero_invested REAL,
    hero_collected REAL,
    hero_rake     REAL,
    rake          REAL    DEFAULT 0,
    jackpot       REAL    DEFAULT 0,
    preflop_pot   REAL,                    -- pot size до флопа
    final_pot     REAL,                    -- pot size в summary
    hero_net      REAL,                    -- $ выиграл/проиграл
    net_bb        REAL, 
    hero_ev_diff  REAL,                    -- all-in EV – net (если есть)
    hero_won      INTEGER,                 -- 1/0 выиграл ли шоудаун
    hero_showdown INTEGER,                 -- 1/0 WTSD
    duration_ms   INTEGER                  -- заполним позже (vision-мод)
);

/* 2. seats — игроки и стеки в начале руки (1 строка = 1 сид) */
CREATE TABLE IF NOT EXISTS seats (
    hand_id   TEXT    NOT NULL REFERENCES hands(hand_id) ON DELETE CASCADE,
    seat_no   INTEGER NOT NULL,         -- 1-6
    player_id TEXT    NOT NULL,         -- «dd9638b4»
    chips     REAL    NOT NULL,         -- 2.24
    PRIMARY KEY (hand_id, seat_no)
);

/* 3. actions — все действия, чтобы потом вычислять VPIP/PFR/3Bet и пр. */
CREATE TABLE IF NOT EXISTS actions (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    hand_id   TEXT    NOT NULL REFERENCES hands(hand_id) ON DELETE CASCADE,
    street    TEXT    NOT NULL,         -- PREFLOP / FLOP / TURN / RIVER
    order_no  INTEGER NOT NULL,         -- порядок действия
    seat_no   INTEGER NOT NULL,         -- игрок-инициатор
    act       TEXT    NOT NULL,         -- FOLD / CALL / RAISE / BET / CHECK
    amount    REAL,                     -- $ размера действия
    allin     INTEGER DEFAULT 0         -- 1 если all-in
);

/* 4. showdowns — карты на вскрытии (для equity / runouts) */
CREATE TABLE IF NOT EXISTS showdowns (
    hand_id   TEXT    NOT NULL REFERENCES hands(hand_id) ON DELETE CASCADE,
    seat_no   INTEGER NOT NULL,
    cards     TEXT    NOT NULL,         -- 'AhKd'
    won       REAL,         
    PRIMARY KEY (hand_id, seat_no)
);

/* 5. sessions — агрегация за сидение (как в H2N "Сессии") */
CREATE TABLE IF NOT EXISTS sessions (
    session_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    start_utc      TEXT,
    end_utc        TEXT,
    hands_cnt      INTEGER DEFAULT 0,
    net_bb         REAL    DEFAULT 0,
    ev_bb          REAL    DEFAULT 0,
    tables_avg     REAL,               -- среднее кол-во столов
    duration_min   REAL
);

/* 6. hand_session_map — связывает каждую руку с сессией */
CREATE TABLE IF NOT EXISTS hand_session_map (
    hand_id    TEXT PRIMARY KEY REFERENCES hands(hand_id) ON DELETE CASCADE,
    session_id INTEGER NOT NULL REFERENCES sessions(session_id)
);

/* 7. tags — аналог H2N «Отмеченные руки» */
CREATE TABLE IF NOT EXISTS tags (
    hand_id TEXT NOT NULL REFERENCES hands(hand_id) ON DELETE CASCADE,
    tag     TEXT NOT NULL,
    note    TEXT,
    PRIMARY KEY (hand_id, tag)
);

/* 8. computed_stats — денорм. кеш, чтобы не жечь проц каждый запрос
      (заполняется batch-скриптом после импорта) */
CREATE TABLE IF NOT EXISTS computed_stats (
    hand_id      TEXT PRIMARY KEY REFERENCES hands(hand_id) ON DELETE CASCADE,
    vpip         INTEGER,   -- 1/0
    pfr          INTEGER,
    threebet     INTEGER,
    squeeze      INTEGER,
    steal        INTEGER,
    fold_to_3b   INTEGER,
    fold_to_cbet INTEGER,
    cbet_flop    INTEGER,
    wwsf         INTEGER,
    wt_sd        INTEGER,
    w_sd         INTEGER
);

/* 9. collected - таблица с победителями */
CREATE TABLE IF NOT EXISTS collected (
    hand_id  TEXT    NOT NULL,
    seat_no  INTEGER NOT NULL,
    amount   REAL    NOT NULL,
    PRIMARY KEY (hand_id, seat_no, amount)   -- ← добавил amount: игрок может собрать пару разных банков
);



/* --------- полезные индексы для скорости отчётов ---------- */
CREATE INDEX IF NOT EXISTS idx_actions_hand_street ON actions(hand_id, street);
CREATE INDEX IF NOT EXISTS idx_actions_seat ON actions(seat_no);
CREATE INDEX IF NOT EXISTS idx_hands_datetime ON hands(datetime_utc);
"""
)

conn.commit()
conn.close()

print(f"✅  База создана: {DB_PATH.resolve()}")

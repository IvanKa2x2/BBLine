import sqlite3
import os


def create_database(db_path="db/bbline.sqlite"):
    # Создание папки, если нет
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Таблица: hands
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS hands (
        hand_id TEXT PRIMARY KEY,
        date_ts INTEGER,
        table_name TEXT,
        sb REAL,
        bb REAL,
        btn_seat INTEGER,
        hero_seat INTEGER,
        hero_pos TEXT,
        pot_rake REAL,
        pot_total REAL,
        winner_seat INTEGER,
        showdown INTEGER DEFAULT 0
    )
    """
    )

    # Таблица: players
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS players (
        hand_id TEXT,
        seat INTEGER,
        player_pos TEXT,
        player_id TEXT,
        start_stack_bb REAL,
        end_stack_bb REAL,
        won_bb REAL,
        invested_bb REAL,
        net_bb REAL,
        preflop_action TEXT,
        PRIMARY KEY (hand_id, seat),
        FOREIGN KEY (hand_id) REFERENCES hands(hand_id)
    )
    """
    )

    # Таблица: actions
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS actions (
        action_id INTEGER PRIMARY KEY AUTOINCREMENT,
        hand_id TEXT,
        street TEXT CHECK(street IN ('P','F','T','R')),
        seat INTEGER,
        player_id TEXT,
        action TEXT CHECK(action IN ('fold','call','raise','check','bet','all-in','post')),
        amount_bb REAL,
        FOREIGN KEY (hand_id) REFERENCES hands(hand_id)
    )
    """
    )

    # Таблица: hero_cards
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS hero_cards (
        hand_id TEXT PRIMARY KEY,
        card1 TEXT,
        card2 TEXT,
        suited BOOLEAN,
        FOREIGN KEY (hand_id) REFERENCES hands(hand_id)
    )
    """
    )

    # Таблица: board
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS board (
        hand_id TEXT PRIMARY KEY,
        flop1 TEXT,
        flop2 TEXT,
        flop3 TEXT,
        turn TEXT,
        river TEXT,
        FOREIGN KEY (hand_id) REFERENCES hands(hand_id)
    )
    """
    )

    # Таблица: flags (опционально)
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS flags (
        hand_id TEXT PRIMARY KEY,
        missed_cbet BOOLEAN,
        lost_stack BOOLEAN,
        cooler BOOLEAN,
        tilt_tag BOOLEAN,
        FOREIGN KEY (hand_id) REFERENCES hands(hand_id)
    )
    """
    )

    # ---------- ИНДЕКСЫ ----------
    c.executescript(
        """
    CREATE INDEX IF NOT EXISTS idx_actions_hand_id     ON actions(hand_id);
    CREATE INDEX IF NOT EXISTS idx_players_hand_id     ON players(hand_id);
    CREATE INDEX IF NOT EXISTS idx_hero_cards_hand_id  ON hero_cards(hand_id);
    CREATE INDEX IF NOT EXISTS idx_board_hand_id       ON board(hand_id);
    CREATE INDEX IF NOT EXISTS idx_flags_hand_id       ON flags(hand_id);
    CREATE INDEX IF NOT EXISTS idx_hands_date_ts       ON hands(date_ts);
    CREATE INDEX IF NOT EXISTS idx_players_player_pos  ON players(player_pos);
    CREATE INDEX IF NOT EXISTS idx_players_player_id   ON players(player_id);

    -- Защита от дублей (если захочешь убрать дубликаты на уровне SQLite)
    CREATE UNIQUE INDEX IF NOT EXISTS uniq_actions ON actions(hand_id, street, seat, action, amount_bb);
    """
    )
    # --------------------------------

    conn.commit()
    conn.close()
    print("✅ База данных создана по структуре и проиндексирована.")


if __name__ == "__main__":
    create_database()

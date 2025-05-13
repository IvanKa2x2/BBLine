# utils/db_schema.py

import sqlite3
import os

def create_database(db_path='db/bbline.sqlite'):
    # Создание папки, если нет
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Таблица: hands
    c.execute("""
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
        winner_seat INTEGER
    )
    """)

    # Таблица: players
    c.execute("""
    CREATE TABLE IF NOT EXISTS players (
        hand_id TEXT,
        seat INTEGER,
        player_pos TEXT,
        player_id TEXT,
        start_stack_bb REAL,
        end_stack_bb REAL,
        won_bb REAL,
        PRIMARY KEY (hand_id, seat),
        FOREIGN KEY (hand_id) REFERENCES hands(hand_id)
    )
    """)

    # Таблица: actions
    c.execute("""
    CREATE TABLE IF NOT EXISTS actions (
        action_id INTEGER PRIMARY KEY AUTOINCREMENT,
        hand_id TEXT,
        street TEXT CHECK(street IN ('P','F','T','R')),
        seat INTEGER,
        action TEXT CHECK(action IN ('fold','call','raise','check','bet','all-in','post')),
        amount_bb REAL,
        FOREIGN KEY (hand_id) REFERENCES hands(hand_id)
    )
    """)

    # Таблица: hero_cards
    c.execute("""
    CREATE TABLE IF NOT EXISTS hero_cards (
        hand_id TEXT PRIMARY KEY,
        card1 TEXT,
        card2 TEXT,
        suited BOOLEAN,
        FOREIGN KEY (hand_id) REFERENCES hands(hand_id)
    )
    """)

    # Таблица: board
    c.execute("""
    CREATE TABLE IF NOT EXISTS board (
        hand_id TEXT PRIMARY KEY,
        flop1 TEXT,
        flop2 TEXT,
        flop3 TEXT,
        turn TEXT,
        river TEXT,
        FOREIGN KEY (hand_id) REFERENCES hands(hand_id)
    )
    """)

    # Таблица: flags (опционально)
    c.execute("""
    CREATE TABLE IF NOT EXISTS flags (
        hand_id TEXT PRIMARY KEY,
        missed_cbet BOOLEAN,
        lost_stack BOOLEAN,
        cooler BOOLEAN,
        tilt_tag BOOLEAN,
        FOREIGN KEY (hand_id) REFERENCES hands(hand_id)
    )
    """)

    conn.commit()
    conn.close()
    print("✅ База данных создана по структуре.")

if __name__ == "__main__":
    create_database()

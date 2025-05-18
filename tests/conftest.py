import sqlite3
import pytest


@pytest.fixture
def mini_db(tmp_path):
    db_path = tmp_path / "bbline.sqlite"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # --- Основные таблицы ---
    c.execute(
        """
    CREATE TABLE players (
        hand_id TEXT,
        player_id TEXT,
        seat INTEGER,
        net_bb REAL,
        end_stack_bb REAL,
        preflop_action TEXT
    )
    """
    )
    c.execute(
        """
    CREATE TABLE hands (
        hand_id TEXT,
        hero_pos TEXT,
        date_ts INTEGER
    )
    """
    )
    # --- Добавь эти таблицы ---
    c.execute(
        """
    CREATE TABLE hero_cards (
        hand_id TEXT,
        card1 TEXT,
        card2 TEXT,
        suited INTEGER
    )
    """
    )
    c.execute(
        """
    CREATE TABLE actions (
        hand_id TEXT,
        street TEXT,
        seat INTEGER,
        action TEXT,
        amount_bb REAL
    )
    """
    )
    # --- Вставь фиктивные данные ---
    c.executemany(
        """
    INSERT INTO hands (hand_id, hero_pos, date_ts) VALUES (?, ?, ?)
    """,
        [
            ("H1", "BTN", 1000),
            ("H2", "CO", 1001),
            ("H3", "SB", 1002),
        ],
    )
    c.executemany(
        """
    INSERT INTO players (hand_id, player_id, seat, net_bb, end_stack_bb, preflop_action)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
        [
            ("H1", "Hero", 1, 10, 110, "raise"),
            ("H2", "Hero", 1, -5, 95, "call"),
            ("H3", "Hero", 1, 0, 100, "fold"),
        ],
    )
    c.executemany(
        """
    INSERT INTO hero_cards (hand_id, card1, card2, suited)
    VALUES (?, ?, ?, ?)
    """,
        [
            ("H1", "A♠", "K♠", 1),
            ("H2", "T♦", "T♠", 0),
            ("H3", "A♠", "K♣", 0),
        ],
    )
    c.executemany(
        """
    INSERT INTO actions (hand_id, street, seat, action, amount_bb)
    VALUES (?, ?, ?, ?, ?)
    """,
        [
            ("H1", "P", 1, "raise", 3.0),
            ("H1", "P", 2, "call", 3.0),
            ("H2", "P", 1, "call", 2.0),
            ("H3", "P", 1, "fold", 0.0),
        ],
    )
    conn.commit()
    conn.close()
    return db_path

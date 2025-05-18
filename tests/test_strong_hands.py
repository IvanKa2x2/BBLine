import analysis.strong_hands as strong_hands
import pytest


@pytest.fixture
def patch_db(monkeypatch, mini_db):
    monkeypatch.setattr("analysis.utils.DB_PATH", mini_db)


def test_strong_hands_main(patch_db):
    strong_hands.main()

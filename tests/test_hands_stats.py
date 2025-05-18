import analysis.hands_stats as hands_stats
import pytest


@pytest.fixture
def patch_db(monkeypatch, mini_db):
    monkeypatch.setattr("analysis.utils.DB_PATH", mini_db)


def test_hands_stats_main(patch_db):
    hands_stats.main()

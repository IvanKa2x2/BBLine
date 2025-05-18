import analysis.summary as summary
import pytest


@pytest.fixture
def patch_db(monkeypatch, mini_db):
    monkeypatch.setattr("analysis.utils.DB_PATH", mini_db)


def test_summary_smoke(patch_db):
    summary.summary()


def test_by_position(patch_db):
    summary.by_position()


def test_by_action(patch_db):
    summary.by_action()


def test_stack_timeline(patch_db):
    summary.stack_timeline(limit=2)  # чтобы не было лишнего вывода


def test_top_losing_hands(patch_db):
    summary.top_losing_hands(limit=2)


def test_vpip_pfr(patch_db):
    summary.vpip_pfr()

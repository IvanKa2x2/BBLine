import analysis.street_loss as street_loss
import pytest


@pytest.fixture
def patch_db(monkeypatch, mini_db):
    monkeypatch.setattr("analysis.utils.DB_PATH", mini_db)


def test_street_loss_main(patch_db):
    street_loss.main()

from analysis.utils import normalize


def test_normalize():
    assert normalize("A♠", "K♠", True) == "AKs"
    assert normalize("A♠", "K♣", False) == "AKo"
    assert normalize("T♦", "T♠", False) == "TT"

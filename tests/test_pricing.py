import math
import pytest

from cosmicreseller import pricing


@pytest.mark.parametrize(
    "text, expected",
    [
        ("£1,234.50", 1234.50),
        ("1 234,50", 1234.50),
        ("€999.99", 999.99),
        ("$2,000", 2000.0),
        ("2000", 2000.0),
    ],
)
def test_to_float_happy(text, expected):
    assert pricing._to_float(text) == pytest.approx(expected)


@pytest.mark.parametrize("bad", ["N/A", "free", "—", "", "abc"])
def test_to_float_raises(bad):
    with pytest.raises(ValueError):
        core._to_float(bad)


def test_filter_cheap_items_threshold_0_8():
    items = [
        ("A", "£100", "u1"),
        ("B", "£200", "u2"),
        ("C", "£300", "u3"),
    ]
    avg, cheap = pricing.filter_cheap_items(items, threshold_ratio=0.8)
    # avg = 200, threshold=160 → only 100 is below
    assert avg == pytest.approx(200.0)
    assert cheap == [("A", 100.0, "u1")]


def test_filter_cheap_items_no_prices():
    items = [("A", "N/A", "u1"), ("B", "—", "u2")]
    avg, cheap = pricing.filter_cheap_items(items, threshold_ratio=0.8)
    assert avg == 0.0
    assert cheap == []

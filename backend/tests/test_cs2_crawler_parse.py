"""T2: Steam Market crawler 解析函数单测 — _parse_price / _parse_volume 边界"""
from app.crawlers.steam_market import _parse_price, _parse_volume


class TestParsePrice:
    def test_cny_with_symbol_and_comma(self):
        assert _parse_price("¥ 3,240.00") == 3240.0

    def test_cny_without_space(self):
        assert _parse_price("¥3240.00") == 3240.0

    def test_usd(self):
        assert _parse_price("$ 50.00") == 50.0

    def test_usd_large_with_comma(self):
        assert _parse_price("$12,345.67") == 12345.67

    def test_small_value_with_decimals(self):
        assert _parse_price("¥ 0.03") == 0.03

    def test_none_returns_none(self):
        assert _parse_price(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_price("") is None

    def test_whitespace_only_returns_none(self):
        assert _parse_price("   ") is None

    def test_invalid_string_returns_none(self):
        assert _parse_price("abc") is None

    def test_only_symbol_returns_none(self):
        assert _parse_price("¥") is None

    def test_multiple_commas(self):
        assert _parse_price("¥ 1,234,567.89") == 1234567.89

    def test_integer_no_decimals(self):
        assert _parse_price("¥ 100") == 100.0


class TestParseVolume:
    def test_plain_number(self):
        assert _parse_volume("1892") == 1892

    def test_with_comma(self):
        assert _parse_volume("1,892") == 1892

    def test_large_with_commas(self):
        assert _parse_volume("12,345,678") == 12345678

    def test_none_returns_zero(self):
        assert _parse_volume(None) == 0

    def test_empty_returns_zero(self):
        assert _parse_volume("") == 0

    def test_whitespace_returns_zero(self):
        assert _parse_volume("   ") == 0

    def test_invalid_string_returns_zero(self):
        assert _parse_volume("N/A") == 0

    def test_zero_string(self):
        assert _parse_volume("0") == 0

"""T3: CS2 Alert 触发逻辑单测 — above/below/None/边界"""
from app.agents.cs2_market.jobs import check_alert_hit


class TestCheckAlertHit:
    # ===== above direction =====
    def test_above_exact_hit(self):
        assert check_alert_hit("above", 100.0, 100.0) is True

    def test_above_exceeds_target(self):
        assert check_alert_hit("above", 150.0, 100.0) is True

    def test_above_below_target_not_hit(self):
        assert check_alert_hit("above", 99.99, 100.0) is False

    # ===== below direction =====
    def test_below_exact_hit(self):
        assert check_alert_hit("below", 100.0, 100.0) is True

    def test_below_under_target(self):
        assert check_alert_hit("below", 50.0, 100.0) is True

    def test_below_above_target_not_hit(self):
        assert check_alert_hit("below", 100.01, 100.0) is False

    # ===== None / edge cases =====
    def test_none_direction_returns_false(self):
        assert check_alert_hit(None, 100.0, 100.0) is False

    def test_none_target_returns_false(self):
        assert check_alert_hit("above", 100.0, None) is False

    def test_unknown_direction_returns_false(self):
        assert check_alert_hit("invalid", 100.0, 100.0) is False

    def test_empty_string_direction_returns_false(self):
        assert check_alert_hit("", 100.0, 100.0) is False

    # ===== 小数精度 =====
    def test_tiny_decimal_above(self):
        assert check_alert_hit("above", 0.02, 0.01) is True

    def test_tiny_decimal_below(self):
        assert check_alert_hit("below", 0.009, 0.01) is True

    # ===== 大数值 =====
    def test_large_numbers(self):
        assert check_alert_hit("above", 1_000_000.0, 999_999.0) is True
        assert check_alert_hit("below", 500.0, 1_000_000.0) is True

    # ===== 零目标价 =====
    def test_zero_target_above(self):
        assert check_alert_hit("above", 0.0, 0.0) is True
        assert check_alert_hit("above", 0.01, 0.0) is True

    def test_zero_target_below(self):
        assert check_alert_hit("below", 0.0, 0.0) is True
        assert check_alert_hit("below", -0.01, 0.0) is True

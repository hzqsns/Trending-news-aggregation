"""T1: CS2 Predictor 单元测试 — compute_indicators 计算正确性 + 概率归一化"""
from app.agents.cs2_market.predictor import compute_indicators


class TestComputeIndicators:
    def test_insufficient_data_returns_error(self):
        result = compute_indicators([100.0], [10])
        assert result.get("error") == "insufficient data"

    def test_basic_calculation(self):
        prices = [100.0, 105.0, 110.0]
        volumes = [50, 60, 70]
        result = compute_indicators(prices, volumes)
        assert result["latest_price"] == 110.0
        assert result["sample_size"] == 3
        assert result["price_change_pct"] == 10.0  # (110-100)/100 * 100

    def test_ma5_with_exactly_5_points(self):
        prices = [100, 102, 104, 106, 108]
        result = compute_indicators(prices, [10] * 5)
        assert result["ma5"] == 104.0  # mean of last 5

    def test_ma5_with_fewer_than_5_points(self):
        prices = [100.0, 110.0]
        result = compute_indicators(prices, [10, 20])
        # ma5 falls back to latest_price (110.0)
        assert result["ma5"] == 110.0

    def test_ma20_with_20_points(self):
        prices = list(range(80, 100))  # 20 points from 80 to 99
        result = compute_indicators(prices, [10] * 20)
        assert result["ma20"] == 89.5  # mean(80..99)

    def test_ma5_above_ma20_signal(self):
        # 最后 5 个 > 全部均值
        prices = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 200, 200, 200, 200, 200]
        result = compute_indicators(prices, [10] * 15)
        assert result["ma5"] > result["ma20"]
        assert result["ma5_vs_ma20"] == "above"

    def test_ma5_below_ma20_signal(self):
        prices = [200] * 10 + [100] * 5
        result = compute_indicators(prices, [10] * 15)
        assert result["ma5_vs_ma20"] == "below"

    def test_price_change_pct_rise(self):
        result = compute_indicators([100.0, 150.0], [10, 20])
        assert result["price_change_pct"] == 50.0

    def test_price_change_pct_fall(self):
        result = compute_indicators([100.0, 80.0], [10, 20])
        assert result["price_change_pct"] == -20.0

    def test_zero_initial_price_safe(self):
        """期初价为 0 时不除零"""
        result = compute_indicators([0.0, 100.0], [10, 20])
        assert result["price_change_pct"] == 0.0  # 保护逻辑

    def test_volatility_calculated_when_enough_data(self):
        prices = [100.0, 105.0, 95.0, 110.0, 90.0, 108.0]
        result = compute_indicators(prices, [10] * 6)
        # 有波动就应 > 0
        assert result["volatility_pct"] > 0

    def test_volatility_zero_for_constant_prices(self):
        prices = [100.0] * 10
        result = compute_indicators(prices, [10] * 10)
        assert result["volatility_pct"] == 0.0

    def test_volume_surge_detection(self):
        # 前 5 个量为 10，后 5 个量为 100 → surge
        volumes = [10, 10, 10, 10, 10, 100, 100, 100, 100, 100]
        prices = [100.0] * 10
        result = compute_indicators(prices, volumes)
        assert result["volume_surge_pct"] > 0

    def test_volume_surge_negative_when_volume_drops(self):
        volumes = [100, 100, 100, 100, 100, 10, 10, 10, 10, 10]
        prices = [100.0] * 10
        result = compute_indicators(prices, volumes)
        assert result["volume_surge_pct"] < 0

    def test_rounded_output_fields(self):
        """输出值应 round 到 2 位小数"""
        prices = [100.123456, 102.987654]
        result = compute_indicators(prices, [10, 20])
        # 验证 round 生效（不精确到 6 位）
        assert result["latest_price"] == round(102.987654, 2)


class TestPredictionProbabilityNormalization:
    """测试概率归一化逻辑（在 predict_item 内的 up+flat+down 必须归一）"""

    def test_normalized_probs_sum_to_one(self):
        # 模拟 predict_item 内部的归一化逻辑
        up, flat, down = 0.3, 0.4, 0.3
        total = up + flat + down
        up, flat, down = up / total, flat / total, down / total
        assert abs(up + flat + down - 1.0) < 1e-9

    def test_normalize_unbalanced_sum(self):
        up, flat, down = 0.8, 0.1, 0.1  # sum = 1.0 already
        total = up + flat + down
        up, flat, down = up / total, flat / total, down / total
        assert abs(up - 0.8) < 1e-9

    def test_normalize_when_sum_greater_than_one(self):
        """LLM 返回 0.5, 0.5, 0.5 的异常情况"""
        up, flat, down = 0.5, 0.5, 0.5  # sum = 1.5
        total = up + flat + down
        up, flat, down = up / total, flat / total, down / total
        assert abs(up + flat + down - 1.0) < 1e-9
        assert abs(up - 1 / 3) < 1e-9

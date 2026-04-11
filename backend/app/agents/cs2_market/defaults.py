BUILTIN_SKILLS = [
    {
        "name": "CS2 饰品趋势预测",
        "slug": "cs2_trend_predictor",
        "description": "基于技术指标 (MA/成交量/波动率) + 更新日志 + LLM 推理，预测饰品未来 7/14/30 天涨跌概率",
        "skill_type": "predictor",
        "config": {
            "indicators": ["MA5", "MA20", "volume_surge", "volatility"],
            "external_factors": ["patchnotes", "major_events"],
            "horizons": ["7d", "14d", "30d"],
            "top_n_items": 50,
        },
    },
    {
        "name": "CS2 价格提醒监控",
        "slug": "cs2_price_alert",
        "description": "监控用户自选饰品价格，到达目标价时触发通知推送",
        "skill_type": "monitor",
        "config": {
            "check_interval_minutes": 5,
            "notify_channels": ["telegram", "wechat", "qq"],
        },
    },
]

__all__ = ["BUILTIN_SKILLS"]

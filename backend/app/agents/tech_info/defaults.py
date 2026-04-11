CRAWLER_KEYS = ["github", "hackernews", "v2ex", "linux_do", "twitter"]

BUILTIN_SKILLS = [
    {
        "name": "技术趋势评分",
        "slug": "tech_trend_scorer",
        "description": "评估技术资讯的热度和价值（0-5分），分析技术领域和影响力",
        "skill_type": "scorer",
        "config": {
            "criteria": [
                {"condition": "开源项目获 1k+ stars 或重大版本发布", "score": 5},
                {"condition": "核心基础设施安全漏洞（CVE 高危）", "score": 5},
                {"condition": "大厂重要开源项目/API 变更", "score": 4},
                {"condition": "新兴技术趋势（AI/Rust/WebAssembly 等）", "score": 3},
                {"condition": "社区热门讨论（HN/V2EX 100+ 评论）", "score": 3},
                {"condition": "常规技术博文或教程", "score": 1},
            ],
        },
    },
    {
        "name": "每日技术摘要",
        "slug": "tech_daily_digest",
        "description": "每日自动生成技术趋势摘要，涵盖开源热门、社区讨论、安全动态",
        "skill_type": "generator",
        "config": {
            "morning_time": "08:00",
            "sections": ["GitHub Trending", "Hacker News Top", "社区热议", "安全动态"],
            "top_events_count": 10,
        },
    },
]

__all__ = ["CRAWLER_KEYS", "BUILTIN_SKILLS"]

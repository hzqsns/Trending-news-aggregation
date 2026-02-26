import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import chat_completion_json, chat_completion
from app.database import async_session
from app.models.article import Article
from app.models.alert import Alert
from app.models.report import DailyReport
from app.models.sentiment import SentimentSnapshot

logger = logging.getLogger(__name__)


async def score_article_importance(article: Article) -> dict | None:
    """Use AI to score an article's importance (0-5)."""
    messages = [
        {
            "role": "system",
            "content": """你是一个专业的财经新闻分析 Agent。请对以下新闻进行重要度评分。

评分标准：
- 5分：涉及央行政策重大变化、金融危机级别事件、市场单日暴涨暴跌(>5%)
- 4分：涉及重大地缘政治、Top 公司重大财报意外、重要宏观数据大幅偏离预期
- 3分：涉及重要行业政策、知名公司业绩发布、关键经济数据公布
- 2分：行业动态、一般公司新闻、市场评论
- 1分：一般性财经资讯
- 0分：与财经/投资无关

请以 JSON 格式返回：
{"importance": 数字0-5, "sentiment": "bullish/bearish/neutral", "tags": ["标签1","标签2"], "reason": "评分理由"}""",
        },
        {
            "role": "user",
            "content": f"标题: {article.title}\n来源: {article.source}\n分类: {article.category}\n摘要: {article.summary or '无'}",
        },
    ]
    return await chat_completion_json(messages, max_tokens=300)


async def run_importance_scoring():
    """Score all unscored articles from the last 24 hours."""
    async with async_session() as session:
        since = datetime.utcnow() - timedelta(hours=24)
        result = await session.execute(
            select(Article)
            .where(Article.fetched_at >= since)
            .where(Article.ai_analysis == None)  # noqa: E711
            .order_by(desc(Article.fetched_at))
            .limit(50)
        )
        articles = result.scalars().all()

        scored = 0
        for article in articles:
            analysis = await score_article_importance(article)
            if analysis:
                article.importance = analysis.get("importance", 0)
                article.sentiment = analysis.get("sentiment")
                article.ai_analysis = analysis
                article.tags = ",".join(analysis.get("tags", []))
                scored += 1

        if scored > 0:
            await session.commit()
        logger.info(f"Scored {scored} articles")


async def generate_daily_report(report_type: str = "morning"):
    """Generate a daily market report using AI."""
    async with async_session() as session:
        since = datetime.utcnow() - timedelta(hours=24 if report_type == "morning" else 12)
        result = await session.execute(
            select(Article)
            .where(Article.fetched_at >= since)
            .where(Article.importance >= 2)
            .order_by(desc(Article.importance), desc(Article.published_at))
            .limit(30)
        )
        articles = result.scalars().all()
        if not articles:
            logger.info("No articles to generate report from")
            return

        news_text = "\n".join(
            f"- [{a.source}] {a.title} (重要度:{a.importance}, 情绪:{a.sentiment or '未知'})"
            for a in articles
        )

        report_label = "早间市场日报" if report_type == "morning" else "晚间市场日报"
        messages = [
            {
                "role": "system",
                "content": f"""你是一个专业的投研分析 Agent。请基于以下新闻生成{report_label}。

要求：
1. 用 Markdown 格式输出
2. 包含以下部分：
   - ## 市场概览（1-2段总结今日/近期市场状况）
   - ## 重点事件（列出 Top 5-8 最重要的事件并简要分析其影响）
   - ## 市场情绪（整体多空判断）
   - ## 关注要点（今日/明日需要重点关注的事项）
3. 语言专业但易懂，适合投资者快速阅读
4. 用中文撰写""",
            },
            {"role": "user", "content": f"最近的重要新闻：\n{news_text}"},
        ]

        content = await chat_completion(messages, max_tokens=2000, temperature=0.4)
        if not content:
            return

        today = datetime.utcnow().date()
        existing = await session.execute(
            select(DailyReport)
            .where(DailyReport.report_type == report_type)
            .where(DailyReport.report_date == today)
        )
        if existing.scalar_one_or_none():
            logger.info(f"{report_type} report already exists for {today}")
            return

        report = DailyReport(
            report_type=report_type,
            report_date=today,
            title=f"{today.isoformat()} {report_label}",
            content=content,
            key_events=[a.to_dict() for a in articles[:8]],
        )
        session.add(report)
        await session.commit()
        logger.info(f"Generated {report_type} report for {today}")


async def run_anomaly_detection():
    """Check for anomalies based on recent high-importance news."""
    async with async_session() as session:
        since = datetime.utcnow() - timedelta(hours=1)
        result = await session.execute(
            select(Article)
            .where(Article.fetched_at >= since)
            .where(Article.importance >= 4)
        )
        critical_articles = result.scalars().all()

        if not critical_articles:
            return

        for article in critical_articles:
            existing = await session.execute(
                select(Alert).where(Alert.title == article.title).where(Alert.is_active == True)  # noqa: E712
            )
            if existing.scalar_one_or_none():
                continue

            level = "critical" if article.importance >= 5 else "high"
            alert = Alert(
                level=level,
                title=article.title,
                description=f"来源: {article.source}\n{article.summary or ''}",
                skill_name="anomaly_detector",
                suggestion=article.ai_analysis.get("reason") if article.ai_analysis else None,
            )
            session.add(alert)

        await session.commit()

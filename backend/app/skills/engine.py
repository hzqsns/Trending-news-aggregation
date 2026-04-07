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


_SCORING_SYSTEM_PROMPT = """你是一个专业的财经新闻分析 Agent。请对以下多条新闻分别进行重要度评分。

评分标准：
- 5分：涉及央行政策重大变化、金融危机级别事件、市场单日暴涨暴跌(>5%)
- 4分：涉及重大地缘政治、Top 公司重大财报意外、重要宏观数据大幅偏离预期
- 3分：涉及重要行业政策、知名公司业绩发布、关键经济数据公布
- 2分：行业动态、一般公司新闻、市场评论
- 1分：一般性财经资讯
- 0分：与财经/投资无关

返回 JSON，格式严格如下（results 数组长度必须等于输入文章数）：
{"results": [{"index": 1, "importance": 0-5, "sentiment": "bullish/bearish/neutral", "tags": ["标签"], "reason": "理由"}, ...]}"""

BATCH_SIZE = 10  # 每批文章数，可按需调整


async def _score_batch(articles: list[Article]) -> dict[int, dict]:
    """批量评分，一次 API 调用处理多篇文章，返回 {article.id: analysis_dict}。"""
    articles_text = "\n\n".join(
        f"[{i + 1}] 标题: {a.title}\n来源: {a.source}\n分类: {a.category}\n摘要: {a.summary or '无'}"
        for i, a in enumerate(articles)
    )
    messages = [
        {"role": "system", "content": _SCORING_SYSTEM_PROMPT},
        {"role": "user", "content": f"请评分以下 {len(articles)} 条新闻：\n\n{articles_text}"},
    ]
    # 每篇约 100 token 输出，留足余量
    result = await chat_completion_json(messages, max_tokens=120 * len(articles))
    if not result or not isinstance(result.get("results"), list):
        return {}

    out: dict[int, dict] = {}
    for item in result["results"]:
        idx = item.get("index")
        if not isinstance(idx, int) or not (1 <= idx <= len(articles)):
            continue
        out[articles[idx - 1].id] = item
    return out


async def run_importance_scoring(agent_key: str = "investment"):
    """批量评分最近 24h 内未评分的文章，每批 BATCH_SIZE 篇合并为一次 API 调用。"""
    async with async_session() as session:
        since = datetime.utcnow() - timedelta(hours=24)
        q = (
            select(Article)
            .where(Article.agent_key == agent_key)
            .where(Article.fetched_at >= since)
            .where(Article.ai_analysis == None)  # noqa: E711
            .order_by(desc(Article.fetched_at))
            .limit(50)
        )
        result = await session.execute(q)
        articles = result.scalars().all()
        if not articles:
            logger.info("No articles to score")
            return

        scored = 0
        # 分批处理
        for i in range(0, len(articles), BATCH_SIZE):
            batch = articles[i: i + BATCH_SIZE]
            try:
                analyses = await _score_batch(batch)
            except Exception as e:
                logger.error(f"Batch scoring failed (batch {i // BATCH_SIZE + 1}): {e}")
                analyses = {}

            for article in batch:
                analysis = analyses.get(article.id)
                if analysis:
                    article.importance = int(analysis.get("importance", 0))
                    article.sentiment = analysis.get("sentiment")
                    article.ai_analysis = analysis
                    article.tags = ",".join(analysis.get("tags", []))
                    scored += 1

        if scored > 0:
            await session.commit()
        logger.info(f"Scored {scored}/{len(articles)} articles in {-(-len(articles) // BATCH_SIZE)} batches")


async def generate_daily_report(report_type: str = "morning", agent_key: str = "investment"):
    """Generate a daily market report using AI."""
    async with async_session() as session:
        since = datetime.utcnow() - timedelta(hours=24 if report_type == "morning" else 12)
        result = await session.execute(
            select(Article)
            .where(Article.agent_key == agent_key)
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

        content = await chat_completion(messages, max_tokens=3000, temperature=0.4)
        if not content:
            return

        today = datetime.utcnow().date()
        existing = await session.execute(
            select(DailyReport)
            .where(DailyReport.agent_key == agent_key)
            .where(DailyReport.report_type == report_type)
            .where(DailyReport.report_date == today)
        )
        existing_report = existing.scalar_one_or_none()
        if existing_report:
            logger.info(f"{report_type} report already exists for {today}")
            return existing_report

        report = DailyReport(
            agent_key=agent_key,
            report_type=report_type,
            report_date=today,
            title=f"{today.isoformat()} {report_label}",
            content=content,
            key_events=[a.to_dict() for a in articles[:8]],
        )
        session.add(report)
        await session.commit()
        logger.info(f"Generated {report_type} report for {today}")


def _extract_handle(title: str) -> str:
    """从 '@handle: ...' 格式标题中提取 handle。"""
    if title.startswith("@") and ": " in title:
        return title.split(": ", 1)[0][1:]
    return "unknown"


async def generate_twitter_digest() -> bool:
    """生成 Twitter 博主观点日报，存入 daily_reports 表（report_type='twitter_digest'）。"""
    async with async_session() as session:
        since = datetime.utcnow() - timedelta(hours=24)
        result = await session.execute(
            select(Article)
            .where(Article.category == "twitter")
            .where(Article.published_at >= since)
            .order_by(desc(Article.published_at))
        )
        articles = result.scalars().all()

    if not articles:
        logger.info("Twitter digest: no tweets in last 24h, skipping")
        return False

    # 按 handle 分组（从 title "@handle: ..." 提取）
    handle_map: dict[str, list[str]] = {}
    for a in articles:
        handle = _extract_handle(a.title)
        content = a.content or a.summary or a.title
        handle_map.setdefault(handle, []).append(content)

    handles_text = ""
    for handle, tweets in handle_map.items():
        handles_text += f"\n### @{handle}\n"
        handles_text += "\n".join(f"- {t[:300]}" for t in tweets[:15])

    messages = [
        {
            "role": "system",
            "content": (
                "你是投研助手。请根据以下追踪博主的推文，生成结构化的观点日报。\n"
                "格式要求（严格按 Markdown）：\n"
                "- 每位博主用二级标题（## @handle），列出 3-5 条核心观点（bullet）\n"
                "- 最后加 ## 综合主题，总结所有博主的共同信号和分歧点\n"
                "- 语言：中文，简洁专业"
            ),
        },
        {"role": "user", "content": f"今日追踪博主推文（最近24小时）：\n{handles_text}"},
    ]

    content = await chat_completion(messages, max_tokens=2000, temperature=0.4)
    if not content:
        logger.warning("Twitter digest: AI returned empty content")
        return False

    today = datetime.utcnow().date()
    async with async_session() as session:
        existing = (await session.execute(
            select(DailyReport)
            .where(DailyReport.agent_key == "investment")
            .where(DailyReport.report_type == "twitter_digest")
            .where(DailyReport.report_date == today)
        )).scalar_one_or_none()

        if existing:
            existing.content = content
            existing.title = f"{today.isoformat()} 推特博主观点日报"
        else:
            report = DailyReport(
                agent_key="investment",
                report_type="twitter_digest",
                report_date=today,
                title=f"{today.isoformat()} 推特博主观点日报",
                content=content,
                key_events=[],
            )
            session.add(report)
        await session.commit()

    logger.info(f"Twitter digest generated: {len(handle_map)} handles, {len(articles)} tweets")
    return True


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

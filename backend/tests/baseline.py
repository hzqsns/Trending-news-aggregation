"""Phase 0 基线指标收集脚本。

用法：
    cd backend && python tests/baseline.py

输出 baseline_snapshot.json 到 tests/ 目录，内容为当前 DB 关键计数指标。
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import async_session  # noqa: E402
from app.models.alert import Alert  # noqa: E402
from app.models.article import Article  # noqa: E402
from app.models.report import DailyReport  # noqa: E402
from app.models.sentiment import SentimentSnapshot  # noqa: E402
from app.models.skill import Skill  # noqa: E402

OUTPUT_PATH = Path(__file__).parent / "baseline_snapshot.json"


async def collect_baseline() -> dict:
    async with async_session() as session:
        articles_total = (await session.execute(select(func.count(Article.id)))).scalar() or 0
        articles_with_ai = (
            await session.execute(
                select(func.count(Article.id)).where(Article.ai_analysis.is_not(None))
            )
        ).scalar() or 0
        alerts_total = (await session.execute(select(func.count(Alert.id)))).scalar() or 0
        reports_total = (await session.execute(select(func.count(DailyReport.id)))).scalar() or 0
        skills_total = (await session.execute(select(func.count(Skill.id)))).scalar() or 0
        snapshots_total = (await session.execute(select(func.count(SentimentSnapshot.id)))).scalar() or 0

    ai_ratio = round(articles_with_ai / articles_total, 4) if articles_total > 0 else 0.0

    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "articles_total": articles_total,
        "articles_with_ai_analysis": articles_with_ai,
        "ai_analysis_ratio": ai_ratio,
        "alerts_total": alerts_total,
        "reports_total": reports_total,
        "skills_total": skills_total,
        "sentiment_snapshots_total": snapshots_total,
    }


def main() -> None:
    snapshot = asyncio.run(collect_baseline())
    OUTPUT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

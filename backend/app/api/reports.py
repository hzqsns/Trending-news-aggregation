from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.report import DailyReport

router = APIRouter()


@router.get("/")
async def list_reports(
    report_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    query = select(DailyReport).order_by(desc(DailyReport.report_date), desc(DailyReport.created_at))
    if report_type:
        query = query.where(DailyReport.report_type == report_type)

    offset = (page - 1) * page_size
    result = await session.execute(query.offset(offset).limit(page_size))
    return [r.to_dict() for r in result.scalars().all()]


@router.get("/latest")
async def latest_report(
    report_type: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    query = select(DailyReport).order_by(desc(DailyReport.created_at)).limit(1)
    if report_type:
        query = query.where(DailyReport.report_type == report_type)
    result = await session.execute(query)
    report = result.scalar_one_or_none()
    return report.to_dict() if report else None


class GenerateRequest(BaseModel):
    report_type: str = "morning"  # morning | evening


@router.post("/generate")
async def generate_report(
    body: GenerateRequest,
    _=Depends(get_current_user),
):
    """手动触发生成 AI 日报"""
    if body.report_type not in ("morning", "evening"):
        raise HTTPException(status_code=400, detail="report_type 必须是 morning 或 evening")
    try:
        from app.skills.engine import generate_daily_report
        report = await generate_daily_report(body.report_type)
        if report:
            return report.to_dict()
        raise HTTPException(status_code=500, detail="日报生成失败，请检查 AI 配置和新闻数据是否充足")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-twitter-digest")
async def generate_twitter_digest_report(
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    """手动触发生成 Twitter 博主观点日报"""
    try:
        from app.skills.engine import generate_twitter_digest
        ok = await generate_twitter_digest()
        if not ok:
            raise HTTPException(status_code=400, detail="近24小时无推特数据，请先确保推特追踪已启用并有采集记录")
        from datetime import datetime as dt
        today = dt.utcnow().date()
        report = (await session.execute(
            select(DailyReport)
            .where(DailyReport.report_type == "twitter_digest")
            .where(DailyReport.report_date == today)
        )).scalar_one_or_none()
        return report.to_dict() if report else {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{report_id}")
async def get_report(
    report_id: int,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    result = await session.execute(select(DailyReport).where(DailyReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        return {"error": "Report not found"}
    return report.to_dict()

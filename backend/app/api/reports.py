from typing import Optional

from fastapi import APIRouter, Depends, Query
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

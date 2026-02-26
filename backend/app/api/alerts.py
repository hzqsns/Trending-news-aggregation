from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.alert import Alert

router = APIRouter()


@router.get("/")
async def list_alerts(
    level: Optional[str] = None,
    active_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    query = select(Alert).order_by(desc(Alert.created_at))
    if level:
        query = query.where(Alert.level == level)
    if active_only:
        query = query.where(Alert.is_active == True)  # noqa: E712

    offset = (page - 1) * page_size
    result = await session.execute(query.offset(offset).limit(page_size))
    return [a.to_dict() for a in result.scalars().all()]


@router.get("/active")
async def active_alerts(
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    result = await session.execute(
        select(Alert)
        .where(Alert.is_active == True)  # noqa: E712
        .order_by(desc(Alert.created_at))
    )
    return [a.to_dict() for a in result.scalars().all()]


@router.put("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    result = await session.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        return {"error": "Alert not found"}
    alert.is_active = False
    alert.resolved_at = datetime.utcnow()
    await session.commit()
    return alert.to_dict()

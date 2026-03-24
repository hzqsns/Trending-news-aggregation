import logging
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.calendar_event import CalendarEvent

router = APIRouter()
logger = logging.getLogger(__name__)

# 2026 年内置重要经济日历（UTC 日期，来源：美联储/BLS 官网）
_BUILTIN_EVENTS = [
    # FOMC 会议
    {"title": "FOMC 利率决议", "event_type": "economic", "event_date": "2026-01-29", "event_time": "19:00", "importance": "high", "source": "fed", "description": "美联储联邦公开市场委员会利率决议"},
    {"title": "FOMC 利率决议", "event_type": "economic", "event_date": "2026-03-19", "event_time": "19:00", "importance": "high", "source": "fed", "description": "美联储联邦公开市场委员会利率决议"},
    {"title": "FOMC 利率决议", "event_type": "economic", "event_date": "2026-05-07", "event_time": "19:00", "importance": "high", "source": "fed", "description": "美联储联邦公开市场委员会利率决议"},
    {"title": "FOMC 利率决议", "event_type": "economic", "event_date": "2026-06-18", "event_time": "19:00", "importance": "high", "source": "fed", "description": "美联储联邦公开市场委员会利率决议"},
    {"title": "FOMC 利率决议", "event_type": "economic", "event_date": "2026-07-30", "event_time": "19:00", "importance": "high", "source": "fed", "description": "美联储联邦公开市场委员会利率决议"},
    {"title": "FOMC 利率决议", "event_type": "economic", "event_date": "2026-09-17", "event_time": "19:00", "importance": "high", "source": "fed", "description": "美联储联邦公开市场委员会利率决议"},
    {"title": "FOMC 利率决议", "event_type": "economic", "event_date": "2026-11-05", "event_time": "19:00", "importance": "high", "source": "fed", "description": "美联储联邦公开市场委员会利率决议"},
    {"title": "FOMC 利率决议", "event_type": "economic", "event_date": "2026-12-17", "event_time": "19:00", "importance": "high", "source": "fed", "description": "美联储联邦公开市场委员会利率决议"},
    # CPI（每月第二个周三发布，以下为估算）
    {"title": "美国 CPI（通胀）", "event_type": "economic", "event_date": "2026-01-14", "event_time": "13:30", "importance": "high", "source": "bls", "description": "美国消费者价格指数月度报告"},
    {"title": "美国 CPI（通胀）", "event_type": "economic", "event_date": "2026-02-11", "event_time": "13:30", "importance": "high", "source": "bls", "description": "美国消费者价格指数月度报告"},
    {"title": "美国 CPI（通胀）", "event_type": "economic", "event_date": "2026-03-11", "event_time": "13:30", "importance": "high", "source": "bls", "description": "美国消费者价格指数月度报告"},
    {"title": "美国 CPI（通胀）", "event_type": "economic", "event_date": "2026-04-10", "event_time": "13:30", "importance": "high", "source": "bls", "description": "美国消费者价格指数月度报告"},
    {"title": "美国 CPI（通胀）", "event_type": "economic", "event_date": "2026-05-13", "event_time": "13:30", "importance": "high", "source": "bls", "description": "美国消费者价格指数月度报告"},
    {"title": "美国 CPI（通胀）", "event_type": "economic", "event_date": "2026-06-10", "event_time": "13:30", "importance": "high", "source": "bls", "description": "美国消费者价格指数月度报告"},
    # NFP（非农就业）
    {"title": "美国非农就业（NFP）", "event_type": "economic", "event_date": "2026-01-09", "event_time": "13:30", "importance": "high", "source": "bls", "description": "美国非农就业人口报告"},
    {"title": "美国非农就业（NFP）", "event_type": "economic", "event_date": "2026-02-06", "event_time": "13:30", "importance": "high", "source": "bls", "description": "美国非农就业人口报告"},
    {"title": "美国非农就业（NFP）", "event_type": "economic", "event_date": "2026-03-06", "event_time": "13:30", "importance": "high", "source": "bls", "description": "美国非农就业人口报告"},
    {"title": "美国非农就业（NFP）", "event_type": "economic", "event_date": "2026-04-03", "event_time": "13:30", "importance": "high", "source": "bls", "description": "美国非农就业人口报告"},
    {"title": "美国非农就业（NFP）", "event_type": "economic", "event_date": "2026-05-08", "event_time": "13:30", "importance": "high", "source": "bls", "description": "美国非农就业人口报告"},
    {"title": "美国非农就业（NFP）", "event_type": "economic", "event_date": "2026-06-05", "event_time": "13:30", "importance": "high", "source": "bls", "description": "美国非农就业人口报告"},
]


class EventCreate(BaseModel):
    title: str = Field(..., max_length=200)
    event_type: str = Field(default="custom")
    event_date: str  # YYYY-MM-DD
    event_time: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = None
    importance: str = Field(default="medium")
    meta: Optional[dict] = None


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    description: Optional[str] = None
    importance: Optional[str] = None
    meta: Optional[dict] = None


def _parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"日期格式错误：{s}，应为 YYYY-MM-DD")


@router.get("/")
async def list_events(
    start: Optional[str] = None,
    end: Optional[str] = None,
    event_type: Optional[str] = None,
    days: int = Query(90, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    """列出日历事件。默认返回今天起未来 90 天内的事件。"""
    start_date = _parse_date(start) if start else date.today()
    end_date = _parse_date(end) if end else start_date + timedelta(days=days)

    query = (
        select(CalendarEvent)
        .where(CalendarEvent.event_date >= start_date)
        .where(CalendarEvent.event_date <= end_date)
        .order_by(asc(CalendarEvent.event_date), asc(CalendarEvent.event_time))
    )
    if event_type:
        query = query.where(CalendarEvent.event_type == event_type)

    result = await session.execute(query)
    return [e.to_dict() for e in result.scalars().all()]


@router.post("/", status_code=201)
async def create_event(
    body: EventCreate,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    event_date = _parse_date(body.event_date)
    if body.event_type not in ("economic", "earnings", "custom"):
        raise HTTPException(status_code=400, detail="event_type 必须是 economic / earnings / custom")
    if body.importance not in ("high", "medium", "low"):
        raise HTTPException(status_code=400, detail="importance 必须是 high / medium / low")

    ev = CalendarEvent(
        title=body.title,
        event_type=body.event_type,
        event_date=event_date,
        event_time=body.event_time,
        description=body.description,
        importance=body.importance,
        source="manual",
        meta=body.meta,
    )
    session.add(ev)
    await session.commit()
    await session.refresh(ev)
    return ev.to_dict()


@router.put("/{event_id}")
async def update_event(
    event_id: int,
    body: EventUpdate,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    ev = (await session.execute(
        select(CalendarEvent).where(CalendarEvent.id == event_id)
    )).scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="事件不存在")

    if body.title is not None:
        ev.title = body.title
    if body.event_date is not None:
        ev.event_date = _parse_date(body.event_date)
    if body.event_time is not None:
        ev.event_time = body.event_time
    if body.description is not None:
        ev.description = body.description
    if body.importance is not None:
        ev.importance = body.importance
    if body.meta is not None:
        ev.meta = body.meta

    await session.commit()
    return ev.to_dict()


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: int,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    ev = (await session.execute(
        select(CalendarEvent).where(CalendarEvent.id == event_id)
    )).scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="事件不存在")
    await session.delete(ev)
    await session.commit()


@router.post("/seed")
async def seed_builtin_events(
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    """导入内置的2026年重要经济日历（重复跳过）。"""
    added = 0
    for item in _BUILTIN_EVENTS:
        ev_date = date.fromisoformat(item["event_date"])
        existing = (await session.execute(
            select(CalendarEvent)
            .where(CalendarEvent.title == item["title"])
            .where(CalendarEvent.event_date == ev_date)
            .where(CalendarEvent.source == item["source"])
        )).scalar_one_or_none()
        if existing:
            continue
        ev = CalendarEvent(
            title=item["title"],
            event_type=item["event_type"],
            event_date=ev_date,
            event_time=item.get("event_time"),
            description=item.get("description"),
            importance=item["importance"],
            source=item["source"],
        )
        session.add(ev)
        added += 1
    await session.commit()
    return {"added": added, "total_builtin": len(_BUILTIN_EVENTS)}

import csv
import io
import logging
from datetime import date, datetime

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.macro_indicator import MacroDataPoint

router = APIRouter()
logger = logging.getLogger(__name__)

FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="

FRED_SERIES = {
    "M2SL":     {"label": "M2 货币供应量",   "unit": "十亿美元", "freq": "monthly"},
    "FEDFUNDS": {"label": "联邦基金利率",     "unit": "%",       "freq": "monthly"},
    "CPIAUCSL": {"label": "CPI（同比）",      "unit": "%",       "freq": "monthly"},
    "DGS10":    {"label": "10年期美债收益率", "unit": "%",       "freq": "daily"},
    "UNRATE":   {"label": "失业率",           "unit": "%",       "freq": "monthly"},
}


async def _fetch_and_store_series(series_id: str, session: AsyncSession) -> int:
    url = f"{FRED_BASE}{series_id}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)[1:]  # skip header

    parsed: list[tuple[date, float]] = []
    for row in rows:
        if len(row) < 2:
            continue
        date_str, val_str = row[0].strip(), row[1].strip()
        if val_str == ".":
            continue
        try:
            parsed.append((date.fromisoformat(date_str), float(val_str)))
        except (ValueError, TypeError):
            continue

    if not parsed:
        return 0

    date_to_val = {d: v for d, v in parsed}
    count = 0

    for i, (d, v) in enumerate(parsed):
        mom = round(v - parsed[i - 1][1], 4) if i > 0 else None

        yoy = None
        if series_id == "CPIAUCSL":
            prev_year = d.replace(year=d.year - 1)
            if prev_year in date_to_val:
                yoy = round((v / date_to_val[prev_year] - 1) * 100, 2)

        try:
            point = MacroDataPoint(
                series_id=series_id,
                data_date=d,
                value=round(v, 4),
                yoy=yoy,
                mom=mom,
                fetched_at=datetime.utcnow(),
            )
            session.add(point)
            await session.flush()
            count += 1
        except IntegrityError:
            await session.rollback()
            # Update existing
            existing = await session.scalar(
                select(MacroDataPoint).where(
                    MacroDataPoint.series_id == series_id,
                    MacroDataPoint.data_date == d,
                )
            )
            if existing:
                existing.value = round(v, 4)
                existing.yoy = yoy
                existing.mom = mom
                existing.fetched_at = datetime.utcnow()
                count += 1

    await session.commit()
    return count


@router.get("/indicators", dependencies=[Depends(get_current_user)])
async def get_indicators(session: AsyncSession = Depends(get_session)):
    result = []
    for series_id, meta in FRED_SERIES.items():
        rows = (await session.scalars(
            select(MacroDataPoint)
            .where(MacroDataPoint.series_id == series_id)
            .order_by(MacroDataPoint.data_date.asc())
        )).all()

        if not rows:
            result.append({
                "series_id": series_id,
                "label": meta["label"],
                "unit": meta["unit"],
                "latest_value": None,
                "latest_date": None,
                "mom": None,
                "yoy": None,
                "trend": "flat",
                "history": [],
            })
            continue

        latest = rows[-1]
        prev = rows[-2] if len(rows) >= 2 else None

        if prev and latest.value is not None and prev.value is not None:
            delta = latest.value - prev.value
            trend = "up" if delta > 0.01 else ("down" if delta < -0.01 else "flat")
        else:
            trend = "flat"

        history = [{"data_date": r.data_date.isoformat(), "value": r.value}
                   for r in rows if r.value is not None]

        result.append({
            "series_id": series_id,
            "label": meta["label"],
            "unit": meta["unit"],
            "latest_value": latest.value,
            "latest_date": latest.data_date.isoformat() if latest.data_date else None,
            "mom": latest.mom,
            "yoy": latest.yoy,
            "trend": trend,
            "history": history,
        })

    return result


@router.post("/refresh", dependencies=[Depends(get_current_user)])
async def refresh_indicators(session: AsyncSession = Depends(get_session)):
    totals: dict[str, int] = {}
    for series_id in FRED_SERIES:
        try:
            count = await _fetch_and_store_series(series_id, session)
            totals[series_id] = count
        except Exception as e:
            logger.error(f"FRED fetch failed for {series_id}: {e}")
            totals[series_id] = 0

    return {"updated": sum(totals.values()), "series": totals}

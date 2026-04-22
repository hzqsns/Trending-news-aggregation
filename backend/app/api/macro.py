import csv
import io
import logging
from datetime import date, datetime, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import chat_completion_json
from app.auth import get_current_user
from app.database import get_session
from app.models.macro_indicator import MacroDataPoint

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory cache: (result_dict, expires_at)
_analysis_cache: tuple[Optional[dict], Optional[datetime]] = (None, None)

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

    # Wipe existing data for this series and re-insert cleanly
    from sqlalchemy import delete as sa_delete
    await session.execute(sa_delete(MacroDataPoint).where(MacroDataPoint.series_id == series_id))

    date_to_val = {d: v for d, v in parsed}
    count = 0

    for i, (d, v) in enumerate(parsed):
        mom = round(v - parsed[i - 1][1], 4) if i > 0 else None

        yoy = None
        if series_id == "CPIAUCSL":
            prev_year = d.replace(year=d.year - 1)
            if prev_year in date_to_val:
                yoy = round((v / date_to_val[prev_year] - 1) * 100, 2)

        session.add(MacroDataPoint(
            series_id=series_id,
            data_date=d,
            value=round(v, 4),
            yoy=yoy,
            mom=mom,
            fetched_at=datetime.now(),
        ))
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


_ANALYSIS_PROMPT = """你是专业的宏观经济分析师。根据以下最新美国宏观指标数据，生成投资分析。

当前指标：
{indicators_text}

请以 JSON 格式返回分析结果，严格遵循以下结构（不要添加任何额外字段）：
{{
  "environment": "宽松" | "中性" | "偏紧" | "紧缩",
  "summary": "2-3句话概括当前宏观环境及主要驱动因素",
  "impacts": [
    {{"asset": "美股", "direction": "bullish" | "bearish" | "neutral", "reason": "一句话说明原因"}},
    {{"asset": "美债", "direction": "bullish" | "bearish" | "neutral", "reason": "一句话说明原因"}},
    {{"asset": "黄金", "direction": "bullish" | "bearish" | "neutral", "reason": "一句话说明原因"}},
    {{"asset": "加密货币", "direction": "bullish" | "bearish" | "neutral", "reason": "一句话说明原因"}},
    {{"asset": "美元", "direction": "bullish" | "bearish" | "neutral", "reason": "一句话说明原因"}}
  ]
}}"""


@router.get("/analysis", dependencies=[Depends(get_current_user)])
async def get_analysis(force: bool = False, session: AsyncSession = Depends(get_session)):
    global _analysis_cache
    cached_result, expires_at = _analysis_cache

    if not force and cached_result and expires_at and datetime.now() < expires_at:
        return {**cached_result, "cached": True}

    # Gather latest values from DB
    lines = []
    for series_id, meta in FRED_SERIES.items():
        row = await session.scalar(
            select(MacroDataPoint)
            .where(MacroDataPoint.series_id == series_id)
            .order_by(MacroDataPoint.data_date.desc())
            .limit(1)
        )
        if row and row.value is not None:
            date_str = row.data_date.isoformat() if row.data_date else "N/A"
            mom_str = f", MoM {row.mom:+.2f}{meta['unit']}" if row.mom is not None else ""
            lines.append(f"- {meta['label']}（{series_id}）: {row.value}{meta['unit']} [{date_str}]{mom_str}")

    if not lines:
        return {"error": "暂无宏观数据，请先刷新数据", "cached": False}

    indicators_text = "\n".join(lines)
    prompt = _ANALYSIS_PROMPT.format(indicators_text=indicators_text)

    # Check AI config before calling
    from app.ai.client import _get_ai_config
    config = await _get_ai_config()
    if not config.get("enabled") or not config.get("api_key"):
        return {"error": "AI 未配置或未启用，请前往「系统设置」配置 AI 服务商和 API Key", "cached": False}

    try:
        result = await chat_completion_json(
            [{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.3,
        )
        if not result:
            return {"error": "AI 调用失败或返回空响应，请检查 API Key 是否有效、模型是否支持 JSON 输出", "cached": False}
        if "impacts" not in result:
            logger.warning(f"Macro analysis missing 'impacts' key: {result}")
            return {"error": f"AI 返回格式异常（缺少 impacts 字段），原始响应已记录到日志", "cached": False}

        result["generated_at"] = datetime.now().isoformat()
        _analysis_cache = (result, datetime.now() + timedelta(hours=6))
        return {**result, "cached": False}
    except Exception as e:
        logger.error(f"Macro analysis failed: {e}", exc_info=True)
        return {"error": f"AI 分析异常: {str(e)}", "cached": False}

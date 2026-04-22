"""CS2 饰品市场 API 路由 — 15 个端点"""
import math
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.cs2_item import CS2Item
from app.models.cs2_price import CS2PriceSnapshot
from app.models.cs2_prediction import CS2Prediction
from app.models.cs2_watchlist import CS2Watchlist
from app.models.user import User

router = APIRouter(prefix="/api/cs2", tags=["cs2"])


# ======================== Market Overview ========================

@router.get("/market/overview")
async def market_overview(
    period: str = "24h",
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """Dashboard 总览：总市值、成交量、情绪、走势"""
    hours = {"24h": 24, "7d": 24 * 7, "30d": 24 * 30}.get(period, 24)
    since = datetime.now() - timedelta(hours=hours)

    total_items = (await session.execute(
        select(func.count(CS2Item.id)).where(CS2Item.is_tracked == True)  # noqa: E712
    )).scalar() or 0

    # 取每个 item 最新价 (子查询)
    latest_sub = (
        select(
            CS2PriceSnapshot.item_id,
            func.max(CS2PriceSnapshot.snapshot_time).label("max_time"),
        )
        .group_by(CS2PriceSnapshot.item_id)
        .subquery()
    )
    latest_prices = (await session.execute(
        select(CS2PriceSnapshot)
        .join(latest_sub, and_(
            CS2PriceSnapshot.item_id == latest_sub.c.item_id,
            CS2PriceSnapshot.snapshot_time == latest_sub.c.max_time,
        ))
    )).scalars().all()

    total_market_cap = sum(s.price for s in latest_prices if s.price)
    total_volume = sum(s.volume for s in latest_prices)

    # 涨跌家数（需要对比期初价格）
    gainers = losers = 0
    for s in latest_prices:
        earliest = (await session.execute(
            select(CS2PriceSnapshot)
            .where(CS2PriceSnapshot.item_id == s.item_id)
            .where(CS2PriceSnapshot.snapshot_time >= since)
            .order_by(CS2PriceSnapshot.snapshot_time.asc())
            .limit(1)
        )).scalar_one_or_none()
        if earliest and earliest.price > 0:
            if s.price > earliest.price:
                gainers += 1
            elif s.price < earliest.price:
                losers += 1

    sentiment_index = 50
    if gainers + losers > 0:
        sentiment_index = int(gainers / (gainers + losers) * 100)

    return {
        "period": period,
        "total_items": total_items,
        "total_market_cap": round(total_market_cap, 2),
        "total_volume": total_volume,
        "gainers": gainers,
        "losers": losers,
        "sentiment_index": sentiment_index,
        "tracked_platform_count": 1,  # 目前仅 Steam
    }


@router.post("/market/refresh")
async def market_refresh(
    _user: User = Depends(get_current_user),
):
    """手动触发价格采集"""
    from app.agents.cs2_market.jobs import job_fetch_prices
    try:
        await job_fetch_prices()
        return {"ok": True, "message": "价格采集已完成"}
    except Exception as e:
        raise HTTPException(500, f"采集失败: {e}")


@router.post("/market/daily-report")
async def generate_daily_report(
    _user: User = Depends(get_current_user),
):
    """手动触发 CS2 日报生成"""
    from app.agents.cs2_market.jobs import job_cs2_daily_report
    try:
        await job_cs2_daily_report()
        return {"ok": True, "message": "日报生成完成"}
    except Exception as e:
        raise HTTPException(500, f"日报生成失败: {e}")


@router.post("/predictions/generate-all")
async def generate_all_predictions(
    period: str = "7d",
    limit: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """批量为 Top 热门饰品生成预测"""
    from app.agents.cs2_market.predictor import predict_item
    items = (await session.execute(
        select(CS2Item).where(CS2Item.is_tracked == True).limit(limit)  # noqa: E712
    )).scalars().all()

    generated = 0
    failed = 0
    for item in items:
        try:
            result = await predict_item(item.id, period)
            if result:
                generated += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    return {"ok": True, "generated": generated, "failed": failed, "period": period}


@router.get("/market/hot-items")
async def hot_items(
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """按近 24h 成交量降序取 Top N 饰品"""
    since = datetime.now() - timedelta(hours=24)
    sub = (
        select(
            CS2PriceSnapshot.item_id,
            func.sum(CS2PriceSnapshot.volume).label("vol_sum"),
            func.max(CS2PriceSnapshot.price).label("last_price"),
        )
        .where(CS2PriceSnapshot.snapshot_time >= since)
        .group_by(CS2PriceSnapshot.item_id)
        .order_by(desc("vol_sum"))
        .limit(limit)
    )
    rows = (await session.execute(sub)).all()
    item_ids = [r.item_id for r in rows]

    items_map = {}
    if item_ids:
        items = (await session.execute(
            select(CS2Item).where(CS2Item.id.in_(item_ids))
        )).scalars().all()
        items_map = {i.id: i for i in items}

    return {
        "items": [
            {
                **(items_map[r.item_id].to_dict() if r.item_id in items_map else {}),
                "volume_24h": r.vol_sum or 0,
                "current_price": r.last_price or 0,
            }
            for r in rows
        ],
    }


# ======================== Rankings ========================

@router.get("/rankings")
async def rankings(
    period: str = "24h",
    direction: str = "gainers",  # gainers/losers
    category: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """涨跌榜 — 按周期对比期初/当前价"""
    hours = {"24h": 24, "7d": 24 * 7, "30d": 24 * 30}.get(period, 24)
    since = datetime.now() - timedelta(hours=hours)

    # 拉所有 tracked 饰品 + 最新价 + 期初价
    q = select(CS2Item).where(CS2Item.is_tracked == True)  # noqa: E712
    if category:
        q = q.where(CS2Item.category == category)
    if search:
        q = q.where(CS2Item.display_name.contains(search))
    items = (await session.execute(q)).scalars().all()

    ranked: list[dict] = []
    for item in items:
        latest = (await session.execute(
            select(CS2PriceSnapshot)
            .where(CS2PriceSnapshot.item_id == item.id)
            .order_by(desc(CS2PriceSnapshot.snapshot_time))
            .limit(1)
        )).scalar_one_or_none()
        earliest = (await session.execute(
            select(CS2PriceSnapshot)
            .where(CS2PriceSnapshot.item_id == item.id)
            .where(CS2PriceSnapshot.snapshot_time >= since)
            .order_by(CS2PriceSnapshot.snapshot_time.asc())
            .limit(1)
        )).scalar_one_or_none()

        if not latest or not earliest or earliest.price <= 0:
            continue

        change_pct = (latest.price - earliest.price) / earliest.price * 100
        ranked.append({
            "id": item.id,
            "name": item.display_name,
            "market_hash_name": item.market_hash_name,
            "image_url": item.image_url,
            "category": item.category,
            "rarity": item.rarity,
            "current_price": latest.price,
            "change_pct": round(change_pct, 2),
            "change_value": round(latest.price - earliest.price, 2),
            "volume": latest.volume,
        })

    # 排序
    reverse = direction == "gainers"
    ranked.sort(key=lambda x: x["change_pct"], reverse=reverse)

    total = len(ranked)
    offset = (page - 1) * page_size
    page_items = ranked[offset:offset + page_size]

    return {
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }


# ======================== Categories ========================

@router.get("/categories")
async def categories(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """所有品类 + 市值 + 涨跌"""
    rows = (await session.execute(
        select(CS2Item.category, func.count(CS2Item.id).label("item_count"))
        .where(CS2Item.is_tracked == True)  # noqa: E712
        .group_by(CS2Item.category)
    )).all()

    return {
        "categories": [
            {"id": r.category, "name": r.category, "item_count": r.item_count}
            for r in rows
        ],
    }


@router.get("/categories/{category_id}/trend")
async def category_trend(
    category_id: str,
    period: str = "7d",
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    hours = {"24h": 24, "7d": 24 * 7, "30d": 24 * 30}.get(period, 24 * 7)
    since = datetime.now() - timedelta(hours=hours)
    items = (await session.execute(
        select(CS2Item.id).where(CS2Item.category == category_id)
    )).scalars().all()
    if not items:
        return {"category": category_id, "points": []}

    snapshots = (await session.execute(
        select(CS2PriceSnapshot.snapshot_time, func.avg(CS2PriceSnapshot.price))
        .where(CS2PriceSnapshot.item_id.in_(items))
        .where(CS2PriceSnapshot.snapshot_time >= since)
        .group_by(func.strftime("%Y-%m-%d %H", CS2PriceSnapshot.snapshot_time))
        .order_by(CS2PriceSnapshot.snapshot_time.asc())
    )).all()

    return {
        "category": category_id,
        "period": period,
        "points": [
            {"time": t.isoformat() if hasattr(t, "isoformat") else str(t), "avg_price": round(p or 0, 2)}
            for t, p in snapshots
        ],
    }


@router.get("/categories/{category_id}/top-items")
async def category_top_items(
    category_id: str,
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    items = (await session.execute(
        select(CS2Item).where(CS2Item.category == category_id).limit(limit)
    )).scalars().all()
    return {"items": [i.to_dict() for i in items]}


# ======================== Item Detail ========================

@router.get("/items/{item_id}")
async def item_detail(
    item_id: int,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    item = (await session.execute(
        select(CS2Item).where(CS2Item.id == item_id)
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item not found")

    latest = (await session.execute(
        select(CS2PriceSnapshot)
        .where(CS2PriceSnapshot.item_id == item_id)
        .order_by(desc(CS2PriceSnapshot.snapshot_time))
        .limit(1)
    )).scalar_one_or_none()

    # 最近预测
    prediction = (await session.execute(
        select(CS2Prediction)
        .where(CS2Prediction.item_id == item_id)
        .where(CS2Prediction.period == "7d")
        .order_by(desc(CS2Prediction.generated_at))
        .limit(1)
    )).scalar_one_or_none()

    return {
        **item.to_dict(),
        "current_price": latest.price if latest else None,
        "volume_24h": latest.volume if latest else 0,
        "prediction": prediction.to_dict() if prediction else None,
    }


@router.get("/items/{item_id}/kline")
async def item_kline(
    item_id: int,
    period: str = "7d",
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    hours = {"1d": 24, "7d": 24 * 7, "30d": 24 * 30, "90d": 24 * 90, "1y": 24 * 365}.get(period, 24 * 7)
    since = datetime.now() - timedelta(hours=hours)

    snapshots = (await session.execute(
        select(CS2PriceSnapshot)
        .where(CS2PriceSnapshot.item_id == item_id)
        .where(CS2PriceSnapshot.snapshot_time >= since)
        .order_by(CS2PriceSnapshot.snapshot_time.asc())
    )).scalars().all()

    return {
        "period": period,
        "points": [
            {
                "time": s.snapshot_time.isoformat() if s.snapshot_time else None,
                "price": s.price,
                "volume": s.volume,
            }
            for s in snapshots
        ],
    }


# ======================== Predictions ========================

@router.get("/predictions")
async def list_predictions(
    period: str = "7d",
    direction: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    q = select(CS2Prediction).where(CS2Prediction.period == period)
    if direction and direction != "all":
        q = q.where(CS2Prediction.direction == direction)
    q = q.order_by(desc(CS2Prediction.generated_at))

    # 最新版本：每个 item_id 只取最新的一条
    seen_items = set()
    all_preds = (await session.execute(q.limit(500))).scalars().all()
    dedup: list[CS2Prediction] = []
    for p in all_preds:
        if p.item_id in seen_items:
            continue
        seen_items.add(p.item_id)
        dedup.append(p)

    total = len(dedup)
    offset = (page - 1) * page_size
    page_preds = dedup[offset:offset + page_size]

    item_ids = [p.item_id for p in page_preds]
    items_map: dict[int, CS2Item] = {}
    if item_ids:
        items = (await session.execute(
            select(CS2Item).where(CS2Item.id.in_(item_ids))
        )).scalars().all()
        items_map = {i.id: i for i in items}

    return {
        "period": period,
        "items": [
            {
                **p.to_dict(),
                "item_name": items_map.get(p.item_id).display_name if p.item_id in items_map else "",
                "item_category": items_map.get(p.item_id).category if p.item_id in items_map else "",
            }
            for p in page_preds
        ],
        "total": total,
        "page": page,
        "pages": math.ceil(total / page_size) if total else 0,
    }


@router.post("/predictions/regenerate")
async def regenerate_prediction(
    item_id: int,
    period: str = "7d",
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    from app.agents.cs2_market.predictor import predict_item
    try:
        prediction = await predict_item(item_id, period)
        if not prediction:
            raise HTTPException(400, "Prediction failed (insufficient data or LLM error)")
        return prediction.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Regeneration error: {e}")


# ======================== Watchlist ========================

@router.get("/watchlist")
async def list_watchlist(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    watches = (await session.execute(
        select(CS2Watchlist).where(CS2Watchlist.user_id == current_user.id)
    )).scalars().all()

    item_ids = [w.item_id for w in watches]
    items_map: dict[int, CS2Item] = {}
    if item_ids:
        items = (await session.execute(
            select(CS2Item).where(CS2Item.id.in_(item_ids))
        )).scalars().all()
        items_map = {i.id: i for i in items}

    result = []
    for w in watches:
        item = items_map.get(w.item_id)
        latest = (await session.execute(
            select(CS2PriceSnapshot)
            .where(CS2PriceSnapshot.item_id == w.item_id)
            .order_by(desc(CS2PriceSnapshot.snapshot_time))
            .limit(1)
        )).scalar_one_or_none()

        result.append({
            **w.to_dict(),
            "item_name": item.display_name if item else "",
            "image_url": item.image_url if item else None,
            "current_price": latest.price if latest else None,
        })

    return {"items": result}


@router.post("/watchlist")
async def add_watchlist(
    item_id: int,
    target_price: float | None = None,
    alert_direction: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # 检查 item 存在
    item = (await session.execute(
        select(CS2Item).where(CS2Item.id == item_id)
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item not found")

    # 检查重复
    existing = (await session.execute(
        select(CS2Watchlist).where(
            CS2Watchlist.user_id == current_user.id,
            CS2Watchlist.item_id == item_id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Already in watchlist")

    watch = CS2Watchlist(
        user_id=current_user.id,
        item_id=item_id,
        target_price=target_price,
        alert_direction=alert_direction,
    )
    session.add(watch)
    await session.commit()
    await session.refresh(watch)
    return watch.to_dict()


@router.put("/watchlist/{watch_id}")
async def update_watchlist(
    watch_id: int,
    target_price: float | None = None,
    alert_direction: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    watch = (await session.execute(
        select(CS2Watchlist).where(
            CS2Watchlist.id == watch_id,
            CS2Watchlist.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not watch:
        raise HTTPException(404, "Watch not found")

    if target_price is not None:
        watch.target_price = target_price
    if alert_direction is not None:
        watch.alert_direction = alert_direction
    watch.triggered = False
    watch.triggered_at = None
    await session.commit()
    return watch.to_dict()


@router.delete("/watchlist/{watch_id}")
async def delete_watchlist(
    watch_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    watch = (await session.execute(
        select(CS2Watchlist).where(
            CS2Watchlist.id == watch_id,
            CS2Watchlist.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not watch:
        raise HTTPException(404, "Watch not found")

    await session.delete(watch)
    await session.commit()
    return {"ok": True}


@router.get("/watchlist/alerts")
async def watchlist_alerts(
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    triggered = (await session.execute(
        select(CS2Watchlist)
        .where(CS2Watchlist.user_id == current_user.id)
        .where(CS2Watchlist.triggered == True)  # noqa: E712
        .order_by(desc(CS2Watchlist.triggered_at))
        .limit(limit)
    )).scalars().all()

    item_ids = [t.item_id for t in triggered]
    items_map: dict[int, CS2Item] = {}
    if item_ids:
        items = (await session.execute(
            select(CS2Item).where(CS2Item.id.in_(item_ids))
        )).scalars().all()
        items_map = {i.id: i for i in items}

    return {
        "alerts": [
            {
                **t.to_dict(),
                "item_name": items_map.get(t.item_id).display_name if t.item_id in items_map else "",
            }
            for t in triggered
        ],
    }

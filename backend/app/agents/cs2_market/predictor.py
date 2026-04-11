"""CS2 预测引擎 — 技术指标计算 + LLM 推理"""
import logging
from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import Optional

from sqlalchemy import select, desc

from app.ai.client import chat_completion_json
from app.database import async_session
from app.models.cs2_item import CS2Item
from app.models.cs2_prediction import CS2Prediction
from app.models.cs2_price import CS2PriceSnapshot

logger = logging.getLogger(__name__)


def compute_indicators(prices: list[float], volumes: list[int]) -> dict:
    """计算 MA5/MA20/波动率/成交量变化等技术指标"""
    if len(prices) < 2:
        return {"error": "insufficient data"}

    latest_price = prices[-1]
    ma5 = mean(prices[-5:]) if len(prices) >= 5 else latest_price
    ma20 = mean(prices[-20:]) if len(prices) >= 20 else mean(prices)

    price_change_pct = 0.0
    if len(prices) >= 2 and prices[0] > 0:
        price_change_pct = (latest_price - prices[0]) / prices[0] * 100

    volatility = 0.0
    if len(prices) >= 5:
        try:
            volatility = stdev(prices[-20:] if len(prices) >= 20 else prices) / mean(prices) * 100
        except Exception:
            volatility = 0.0

    volume_surge = 0.0
    if len(volumes) >= 5:
        recent_avg = mean(volumes[-5:])
        earlier_avg = mean(volumes[:-5]) if len(volumes) > 5 else recent_avg
        if earlier_avg > 0:
            volume_surge = (recent_avg - earlier_avg) / earlier_avg * 100

    return {
        "latest_price": round(latest_price, 2),
        "ma5": round(ma5, 2),
        "ma20": round(ma20, 2),
        "price_change_pct": round(price_change_pct, 2),
        "volatility_pct": round(volatility, 2),
        "volume_surge_pct": round(volume_surge, 2),
        "ma5_vs_ma20": "above" if ma5 > ma20 else "below",
        "sample_size": len(prices),
    }


def _build_prompt(item: CS2Item, indicators: dict, period: str) -> list[dict]:
    system = (
        "你是 CS2 饰品市场分析专家。根据给定的饰品技术指标，预测未来 "
        f"{period} 的涨跌概率。严格返回 JSON，不要任何额外说明。\n\n"
        "JSON 格式（字段名必须完全匹配）：\n"
        '{"direction":"bullish|bearish|neutral",'
        '"up_prob":0.0-1.0,'
        '"flat_prob":0.0-1.0,'
        '"down_prob":0.0-1.0,'
        '"confidence":0.0-1.0,'
        '"predicted_price":number,'
        '"reasoning":"中文简短推理",'
        '"factors":["因素1","因素2"]}\n\n'
        "三个概率 up+flat+down 之和必须等于 1.0。"
    )
    user = f"""饰品：{item.display_name}
品类：{item.category} / {item.subcategory or ''}
稀有度：{item.rarity or '未知'}

当前指标：
- 最新价格：¥{indicators.get('latest_price')}
- MA5：¥{indicators.get('ma5')}
- MA20：¥{indicators.get('ma20')}
- MA5 vs MA20：{indicators.get('ma5_vs_ma20')}
- 近期涨跌：{indicators.get('price_change_pct')}%
- 波动率：{indicators.get('volatility_pct')}%
- 成交量变化：{indicators.get('volume_surge_pct')}%
- 数据点数：{indicators.get('sample_size')}

请预测未来 {period} 的涨跌概率和价格。"""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


async def predict_item(item_id: int, period: str = "7d") -> Optional[CS2Prediction]:
    """对单个饰品进行 LLM 预测，结果写入 cs2_predictions 表"""
    async with async_session() as session:
        item = (await session.execute(
            select(CS2Item).where(CS2Item.id == item_id)
        )).scalar_one_or_none()
        if not item:
            logger.warning(f"Item {item_id} not found")
            return None

        since = datetime.utcnow() - timedelta(days=30)
        snapshots = (await session.execute(
            select(CS2PriceSnapshot)
            .where(CS2PriceSnapshot.item_id == item_id)
            .where(CS2PriceSnapshot.snapshot_time >= since)
            .order_by(CS2PriceSnapshot.snapshot_time.asc())
        )).scalars().all()

    if len(snapshots) < 2:
        logger.debug(f"Item {item_id} has insufficient price history ({len(snapshots)})")
        return None

    prices = [s.price for s in snapshots]
    volumes = [s.volume for s in snapshots]
    indicators = compute_indicators(prices, volumes)

    if indicators.get("error"):
        return None

    messages = _build_prompt(item, indicators, period)

    try:
        result = await chat_completion_json(messages, max_tokens=600)
    except Exception as e:
        logger.error(f"LLM call failed for item {item_id}: {e}")
        return None

    if not result or not isinstance(result, dict):
        logger.warning(f"Invalid LLM result for item {item_id}")
        return None

    try:
        direction = result.get("direction", "neutral")
        up = float(result.get("up_prob", 0.33))
        flat = float(result.get("flat_prob", 0.34))
        down = float(result.get("down_prob", 0.33))
        total = up + flat + down
        if total > 0:
            up, flat, down = up / total, flat / total, down / total
        confidence = float(result.get("confidence", 0.5))
        predicted_price = result.get("predicted_price")
        reasoning = str(result.get("reasoning", ""))[:2000]
        factors = result.get("factors", [])
        if not isinstance(factors, list):
            factors = []
    except (ValueError, TypeError) as e:
        logger.warning(f"Parse LLM result failed for item {item_id}: {e}")
        return None

    async with async_session() as session:
        prediction = CS2Prediction(
            item_id=item_id,
            period=period,
            direction=direction,
            up_prob=up,
            flat_prob=flat,
            down_prob=down,
            confidence=confidence,
            predicted_price=float(predicted_price) if predicted_price else None,
            reasoning=reasoning,
            factors=factors,
        )
        session.add(prediction)
        await session.commit()
        await session.refresh(prediction)

    return prediction

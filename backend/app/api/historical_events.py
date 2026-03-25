import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.historical_event import HistoricalEvent

router = APIRouter()
logger = logging.getLogger(__name__)

VALID_CATEGORIES = {"financial_crisis", "monetary_policy", "pandemic", "tech_bubble", "geopolitics"}
VALID_IMPACTS = {"bullish", "bearish", "mixed"}

_BUILTIN_EVENTS = [
    {
        "title": "2008全球金融危机",
        "category": "financial_crisis",
        "date_range": "2008-09 ~ 2009-06",
        "market_impact": "bearish",
        "description": "次贷危机引发全球性经济衰退，雷曼兄弟破产，全球股市暴跌，美联储实施量化宽松救市。",
        "key_metrics": [
            {"label": "标普500最大跌幅", "value": "-56.8%"},
            {"label": "持续时间", "value": "约17个月"},
            {"label": "美国GDP跌幅", "value": "-4.3%"},
        ],
    },
    {
        "title": "2020 COVID市场崩盘",
        "category": "pandemic",
        "date_range": "2020-02 ~ 2020-04",
        "market_impact": "bearish",
        "description": "新冠疫情全球蔓延，各国封锁措施引发经济停摆，历史上最快的熊市崩盘之一，随后大规模刺激带来V型反弹。",
        "key_metrics": [
            {"label": "标普500最大跌幅", "value": "-34%"},
            {"label": "崩盘速度", "value": "33天"},
            {"label": "美联储降息幅度", "value": "-150bp"},
        ],
    },
    {
        "title": "2000科技泡沫破裂",
        "category": "tech_bubble",
        "date_range": "2000-03 ~ 2002-10",
        "market_impact": "bearish",
        "description": "互联网泡沫破裂，纳斯达克指数从峰值暴跌近80%，大量科技公司倒闭，标志着互联网第一轮泡沫终结。",
        "key_metrics": [
            {"label": "纳斯达克最大跌幅", "value": "-78%"},
            {"label": "持续时间", "value": "约30个月"},
            {"label": "标普500跌幅", "value": "-49%"},
        ],
    },
    {
        "title": "1997亚洲金融危机",
        "category": "financial_crisis",
        "date_range": "1997-07 ~ 1998-12",
        "market_impact": "bearish",
        "description": "泰铢贬值引发连锁反应，韩国、印尼、马来西亚等东南亚经济体相继遭受货币危机，IMF紧急救助。",
        "key_metrics": [
            {"label": "泰铢贬值幅度", "value": "-50%"},
            {"label": "韩元贬值幅度", "value": "-55%"},
            {"label": "IMF救助金额", "value": "约1180亿美元"},
        ],
    },
    {
        "title": "2022美联储激进加息",
        "category": "monetary_policy",
        "date_range": "2022-03 ~ 2023-07",
        "market_impact": "bearish",
        "description": "为应对40年最高通胀，美联储在16个月内加息525bp至5.25-5.5%，引发全球股债双杀。",
        "key_metrics": [
            {"label": "加息幅度", "value": "+525bp"},
            {"label": "标普500跌幅", "value": "-25%"},
            {"label": "美债10年期峰值", "value": "5.0%"},
        ],
    },
    {
        "title": "2020大规模量化宽松",
        "category": "monetary_policy",
        "date_range": "2020-03 ~ 2022-03",
        "market_impact": "bullish",
        "description": "新冠疫情下美联储实施无限量化宽松，资产负债表从4万亿扩张至9万亿，推动股市V型反弹至历史新高。",
        "key_metrics": [
            {"label": "美联储资产负债表扩张", "value": "+5万亿美元"},
            {"label": "标普500涨幅", "value": "+114%"},
            {"label": "基准利率", "value": "0~0.25%"},
        ],
    },
    {
        "title": "2010欧元区债务危机",
        "category": "financial_crisis",
        "date_range": "2010-04 ~ 2012-07",
        "market_impact": "bearish",
        "description": "希腊、爱尔兰、葡萄牙等国主权债务危机，欧元区存亡威胁，ECB德拉吉「不惜一切代价」讲话平息危机。",
        "key_metrics": [
            {"label": "希腊GDP跌幅", "value": "-25%"},
            {"label": "希腊10年债收益率峰值", "value": "37%"},
            {"label": "欧元兑美元跌幅", "value": "-25%"},
        ],
    },
    {
        "title": "2022俄乌冲突",
        "category": "geopolitics",
        "date_range": "2022-02 ~ 2022-12",
        "market_impact": "mixed",
        "description": "俄罗斯入侵乌克兰引发能源危机，原油天然气价格飙升，欧洲通胀加剧，全球供应链再次受冲击。",
        "key_metrics": [
            {"label": "布伦特原油峰值", "value": "$139/桶"},
            {"label": "欧洲天然气价格峰值", "value": "+600%"},
            {"label": "俄罗斯卢布最大跌幅", "value": "-50%"},
        ],
    },
    {
        "title": "2023美国银行业危机",
        "category": "financial_crisis",
        "date_range": "2023-03 ~ 2023-05",
        "market_impact": "bearish",
        "description": "硅谷银行、签名银行相继倒闭，引发市场对美国地区性银行体系的恐慌，美联储紧急推出BTFP救助计划。",
        "key_metrics": [
            {"label": "SVB资产规模", "value": "2090亿美元"},
            {"label": "KBW银行指数跌幅", "value": "-28%"},
            {"label": "BTFP规模", "value": "250亿美元"},
        ],
    },
    {
        "title": "2023~2024 AI科技牛市",
        "category": "tech_bubble",
        "date_range": "2023-01 ~ 2024-12",
        "market_impact": "bullish",
        "description": "ChatGPT引爆AI热潮，英伟达、微软等科技巨头市值暴涨，纳斯达克创历史新高，AI基础设施投资狂潮。",
        "key_metrics": [
            {"label": "英伟达涨幅(2023)", "value": "+239%"},
            {"label": "纳斯达克年涨幅(2023)", "value": "+43%"},
            {"label": "标普500年涨幅(2023)", "value": "+24%"},
        ],
    },
]


class CreateEventPayload(BaseModel):
    title: str
    category: str
    date_range: str
    market_impact: str = "mixed"
    description: Optional[str] = None
    key_metrics: Optional[list] = None


@router.get("/", dependencies=[Depends(get_current_user)])
async def list_events(
    category: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(HistoricalEvent).order_by(HistoricalEvent.date_range.asc())
    if category:
        stmt = stmt.where(HistoricalEvent.category == category)
    if search:
        stmt = stmt.where(
            or_(
                HistoricalEvent.title.ilike(f"%{search}%"),
                HistoricalEvent.description.ilike(f"%{search}%"),
            )
        )
    rows = (await session.scalars(stmt)).all()
    return [r.to_dict() for r in rows]


@router.post("/", dependencies=[Depends(get_current_user)])
async def create_event(
    payload: CreateEventPayload,
    session: AsyncSession = Depends(get_session),
):
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(400, f"Invalid category. Must be one of: {VALID_CATEGORIES}")
    if payload.market_impact not in VALID_IMPACTS:
        raise HTTPException(400, f"Invalid market_impact. Must be one of: {VALID_IMPACTS}")

    event = HistoricalEvent(
        title=payload.title,
        category=payload.category,
        date_range=payload.date_range,
        market_impact=payload.market_impact,
        description=payload.description,
        key_metrics=payload.key_metrics or [],
        is_builtin=False,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event.to_dict()


@router.delete("/{event_id}", dependencies=[Depends(get_current_user)])
async def delete_event(event_id: int, session: AsyncSession = Depends(get_session)):
    event = await session.get(HistoricalEvent, event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    if event.is_builtin:
        raise HTTPException(403, "Cannot delete builtin event")
    await session.delete(event)
    await session.commit()
    return Response(status_code=204)


@router.post("/seed", dependencies=[Depends(get_current_user)])
async def seed_events(session: AsyncSession = Depends(get_session)):
    added = 0
    skipped = 0
    for data in _BUILTIN_EVENTS:
        existing = await session.scalar(
            select(HistoricalEvent).where(
                HistoricalEvent.title == data["title"],
                HistoricalEvent.is_builtin.is_(True),
            )
        )
        if existing:
            skipped += 1
            continue
        event = HistoricalEvent(
            **data,
            is_builtin=True,
            created_at=datetime.utcnow(),
        )
        session.add(event)
        added += 1
    await session.commit()
    return {"added": added, "skipped": skipped}

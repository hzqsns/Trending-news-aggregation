import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.auth import hash_password
from app.database import init_db, async_session
from app.models.user import User
from app.models.setting import SystemSetting, DEFAULT_SETTINGS
from app.models.skill import Skill
from app.api.router import api_router
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BUILTIN_SKILLS = [
    {
        "name": "新闻重要度评分",
        "slug": "news_importance_scorer",
        "description": "AI 自动评估新闻的重要度（0-5分），并进行情绪分析和标签分类",
        "skill_type": "scorer",
        "config": {
            "criteria": [
                {"condition": "涉及央行政策重大变化", "score": 5},
                {"condition": "涉及重大地缘政治事件", "score": 4},
                {"condition": "Top 公司重大财报意外", "score": 4},
                {"condition": "重要宏观数据大幅偏离预期", "score": 3},
                {"condition": "市场异常波动(>3%)", "score": 4},
                {"condition": "行业政策变化", "score": 3},
                {"condition": "一般行业新闻", "score": 1},
            ],
        },
    },
    {
        "name": "异常预警检测",
        "slug": "anomaly_detector",
        "description": "监控高重要度新闻并自动生成预警信号",
        "skill_type": "monitor",
        "config": {
            "threshold": 4,
            "alert_levels": {"5": "critical", "4": "high"},
        },
    },
    {
        "name": "每日市场报告",
        "slug": "daily_report_generator",
        "description": "每日早晚自动生成市场摘要和策略建议",
        "skill_type": "generator",
        "config": {
            "morning_time": "07:30",
            "evening_time": "22:00",
            "top_events_count": 8,
        },
    },
    {
        "name": "市场情绪监控",
        "slug": "market_sentiment_monitor",
        "description": "综合分析市场情绪指标，输出情绪评级和仓位建议。参考 NAAIM、机构配置、散户资金流、远期 PE 等",
        "skill_type": "monitor",
        "config": {
            "indicators": [
                {"name": "NAAIM暴露指数", "warning_threshold": 80, "description": "活跃投资经理股票持仓比例，> 80 预警"},
                {"name": "散户净买入额", "warning_threshold": 85, "description": "日均买入量 > 85% 历史水平 → 过热"},
                {"name": "标普500远期PE", "warning_threshold": 22, "description": "接近历史估值峰值 → 背离信号"},
                {"name": "对冲基金杠杆率", "warning_threshold": "历史高位", "description": "高杠杆 → 波动放大器"},
            ],
            "trigger_rules": {
                "3+预警": "减仓信号",
                "全部预警": "大幅减仓或对冲",
            },
            "output": "情绪评级(极度贪婪/贪婪/中性/恐慌) + 仓位建议",
        },
    },
    {
        "name": "宏观流动性监控",
        "slug": "macro_liquidity_monitor",
        "description": "监控全球流动性关键指标，判断资金面松紧程度。当多指标同时预警时触发减仓信号",
        "skill_type": "monitor",
        "config": {
            "indicators": [
                {"name": "净流动性", "formula": "美联储总资产 - TGA - ON RRP", "warning": "单周下降>5%"},
                {"name": "SOFR(隔夜融资利率)", "warning": "突破5.5% → 减仓"},
                {"name": "MOVE指数(美债波动率)", "warning": ">130 → 风险资产止损"},
                {"name": "USDJPY + US2Y-JP2Y利差", "warning": "利差大幅收窄 → 套利交易平仓风险"},
            ],
            "output": "流动性评级(宽松/中性/紧张/危险) + 操作建议",
        },
    },
    {
        "name": "价值投资框架",
        "slug": "value_investment_scorer",
        "description": "基于基本面指标评估公司的投资价值，输出投资评级。适用于美股/港股/A股",
        "skill_type": "scorer",
        "config": {
            "criteria": [
                {"indicator": "ROE", "condition": "> 15%（持续3年以上）", "weight": 25},
                {"indicator": "负债率", "condition": "< 50%", "weight": 20},
                {"indicator": "自由现金流", "condition": "> 净利润的80%", "weight": 25},
                {"indicator": "护城河", "condition": "品牌/网络效应/成本优势/转换成本", "weight": 30},
            ],
            "output": "投资评级(A/B/C/D) + 理由",
        },
    },
    {
        "name": "加密货币抄底模型",
        "slug": "crypto_bottom_detector",
        "description": "综合多维度链上和市场指标，识别加密货币超跌抄底机会",
        "skill_type": "analyzer",
        "config": {
            "indicators": [
                {"name": "RSI", "condition": "< 30 且周线级别超跌"},
                {"name": "成交量", "condition": "恐慌抛售后萎缩(低于30日均量)"},
                {"name": "MVRV比率", "condition": "< 1.0 (市值低于实现市值)"},
                {"name": "社交媒体恐慌指数", "condition": "> 75"},
                {"name": "矿机关机价", "condition": "现价接近或低于主流矿机关机价"},
                {"name": "LTH供应占比", "condition": "上升(长期持有者增持)"},
            ],
            "trigger_rules": {
                "4+指标满足": "分批建仓信号",
                "5+指标满足": "重仓抄底信号",
            },
            "output": "抄底评级(强/中/弱) + 建议仓位比例",
        },
    },
]


async def _init_admin_user():
    async with async_session() as session:
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is None:
            admin = User(
                username=settings.DEFAULT_ADMIN_USER,
                hashed_password=hash_password(settings.DEFAULT_ADMIN_PASS),
            )
            session.add(admin)
            await session.commit()
            logger.info(f"👤 已创建默认管理员账号: {settings.DEFAULT_ADMIN_USER} / {settings.DEFAULT_ADMIN_PASS}")
            logger.info("   ⚠️ 请登录后尽快修改密码！")


async def _init_settings():
    async with async_session() as session:
        for item in DEFAULT_SETTINGS:
            existing = await session.execute(
                select(SystemSetting).where(SystemSetting.key == item["key"])
            )
            if not existing.scalar_one_or_none():
                setting = SystemSetting(**item)
                session.add(setting)

        env_mapping = {
            "ai_api_key": settings.AI_API_KEY,
            "ai_api_base": settings.AI_API_BASE,
            "ai_model": settings.AI_MODEL,
            "telegram_bot_token": settings.TELEGRAM_BOT_TOKEN,
            "telegram_chat_id": settings.TELEGRAM_CHAT_ID,
            "pushplus_token": settings.PUSHPLUS_TOKEN,
            "qmsg_key": settings.QMSG_KEY,
        }
        for key, env_val in env_mapping.items():
            if env_val:
                result = await session.execute(
                    select(SystemSetting).where(SystemSetting.key == key)
                )
                s = result.scalar_one_or_none()
                if s and not s.value:
                    s.value = env_val

        await session.commit()


async def _init_builtin_skills():
    async with async_session() as session:
        for skill_data in BUILTIN_SKILLS:
            existing = await session.execute(
                select(Skill).where(Skill.slug == skill_data["slug"])
            )
            if not existing.scalar_one_or_none():
                skill = Skill(is_builtin=True, **skill_data)
                session.add(skill)
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting News Agent...")
    await init_db()
    await _init_admin_user()
    await _init_settings()
    await _init_builtin_skills()
    start_scheduler()
    logger.info("✅ News Agent is ready")
    yield
    stop_scheduler()
    logger.info("👋 News Agent stopped")


app = FastAPI(
    title="投研 Agent API",
    version="2.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}

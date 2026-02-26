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

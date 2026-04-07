import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.agents.investment import register_investment_agent
from app.agents.investment.defaults import BUILTIN_SKILLS
from app.agents.tech_info import register_tech_info_agent
from app.agents.tech_info.defaults import BUILTIN_SKILLS as TECH_BUILTIN_SKILLS
from app.config import settings
from app.auth import hash_password
from app.database import init_db, async_session
from app.models.user import User
from app.models.setting import SystemSetting, DEFAULT_SETTINGS
from app.models.skill import Skill
from app.models.bookmark import ArticleBookmark  # noqa: F401
from app.models.calendar_event import CalendarEvent  # noqa: F401
from app.models.macro_indicator import MacroDataPoint  # noqa: F401
from app.models.historical_event import HistoricalEvent  # noqa: F401
from app.api.historical_events import _BUILTIN_EVENTS
from app.api.router import api_router
from app.platform.registry import agent_registry
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


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
            "twitter_grok_api_base": settings.TWITTER_GROK_API_BASE,
            "twitter_grok_api_key": settings.TWITTER_GROK_API_KEY,
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
                select(Skill).where(Skill.agent_key == "investment", Skill.slug == skill_data["slug"])
            )
            if not existing.scalar_one_or_none():
                skill = Skill(agent_key="investment", is_builtin=True, **skill_data)
                session.add(skill)
        for skill_data in TECH_BUILTIN_SKILLS:
            existing = await session.execute(
                select(Skill).where(Skill.agent_key == "tech_info", Skill.slug == skill_data["slug"])
            )
            if not existing.scalar_one_or_none():
                skill = Skill(agent_key="tech_info", is_builtin=True, **skill_data)
                session.add(skill)
        await session.commit()


async def _init_historical_events():
    from datetime import datetime
    async with async_session() as session:
        for data in _BUILTIN_EVENTS:
            existing = await session.scalar(
                select(HistoricalEvent).where(
                    HistoricalEvent.title == data["title"],
                    HistoricalEvent.is_builtin.is_(True),
                )
            )
            if not existing:
                session.add(HistoricalEvent(**data, is_builtin=True, created_at=datetime.utcnow()))
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting News Agent...")
    register_investment_agent(agent_registry)
    register_tech_info_agent(agent_registry)
    await init_db()
    await _init_admin_user()
    await _init_settings()
    await _init_builtin_skills()
    await _init_historical_events()
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

"""T5: 多 Agent 数据隔离回归测试

防止 Bug #1/#2/#6/#7/#11/#12 再次出现：
- _save_items 跨 agent 去重
- articles 查询按 agent_key 过滤
- reports/alerts/skills 创建时设置 agent_key
"""
import pytest
from datetime import datetime
from sqlalchemy import select, func

from app.models.article import Article
from app.models.alert import Alert
from app.models.report import DailyReport
from app.models.skill import Skill
from app.sources.base import NewsItem
from app.sources.manager import _save_items


class TestArticleAgentIsolation:
    @pytest.mark.asyncio
    async def test_save_items_defaults_to_investment(self, db_session):
        items = [NewsItem(title="T1", url="https://a.com/1", source="test")]
        saved, _ = await _save_items(db_session, items)
        assert saved == 1

        result = (await db_session.execute(select(Article))).scalars().first()
        assert result.agent_key == "investment"

    @pytest.mark.asyncio
    async def test_save_items_respects_custom_agent_key(self, db_session):
        items = [NewsItem(title="Tech", url="https://t.com/1", source="gh")]
        saved, _ = await _save_items(db_session, items, agent_key="tech_info")
        assert saved == 1

        result = (await db_session.execute(select(Article))).scalars().first()
        assert result.agent_key == "tech_info"

    @pytest.mark.asyncio
    async def test_cross_agent_same_url_no_false_dedup(self, db_session):
        """Bug #1: 同 URL 在不同 agent 下不应触发去重"""
        url = "https://shared.com/article"
        items = [NewsItem(title="Original", url=url, source="s")]

        # investment agent 先插入
        saved_a, _ = await _save_items(db_session, items, agent_key="investment")
        assert saved_a == 1

        # tech_info agent 应该能插入同 URL
        saved_b, _ = await _save_items(db_session, items, agent_key="tech_info")
        assert saved_b == 1

        count = (await db_session.execute(select(func.count(Article.id)))).scalar()
        assert count == 2

    @pytest.mark.asyncio
    async def test_same_agent_same_url_deduped(self, db_session):
        """同 agent 同 URL 仍然去重"""
        items = [NewsItem(title="Dup", url="https://dup.com/1", source="s")]
        saved1, _ = await _save_items(db_session, items, agent_key="investment")
        saved2, _ = await _save_items(db_session, items, agent_key="investment")
        assert saved1 == 1
        assert saved2 == 0

    @pytest.mark.asyncio
    async def test_articles_query_isolation(self, db_session):
        """Bug #6: /api/articles 应按 agent_key 过滤，防止跨 agent 泄漏"""
        db_session.add_all([
            Article(agent_key="investment", title="Inv1", url="u1", source="s", fetched_at=datetime.utcnow()),
            Article(agent_key="investment", title="Inv2", url="u2", source="s", fetched_at=datetime.utcnow()),
            Article(agent_key="tech_info", title="Tech1", url="u3", source="s", fetched_at=datetime.utcnow()),
            Article(agent_key="cs2_market", title="Cs2", url="u4", source="s", fetched_at=datetime.utcnow()),
        ])
        await db_session.commit()

        invest_count = (await db_session.execute(
            select(func.count(Article.id)).where(Article.agent_key == "investment")
        )).scalar()
        tech_count = (await db_session.execute(
            select(func.count(Article.id)).where(Article.agent_key == "tech_info")
        )).scalar()
        cs2_count = (await db_session.execute(
            select(func.count(Article.id)).where(Article.agent_key == "cs2_market")
        )).scalar()

        assert invest_count == 2
        assert tech_count == 1
        assert cs2_count == 1


class TestReportAgentIsolation:
    @pytest.mark.asyncio
    async def test_reports_with_same_type_date_different_agent(self, db_session):
        """Bug #11: reports unique constraint 现在是 (agent_key, report_type, report_date)"""
        from datetime import date
        today = date.today()

        db_session.add_all([
            DailyReport(agent_key="investment", report_type="morning", report_date=today, content="c1"),
            DailyReport(agent_key="tech_info", report_type="morning", report_date=today, content="c2"),
        ])
        await db_session.commit()

        count = (await db_session.execute(select(func.count(DailyReport.id)))).scalar()
        assert count == 2  # 两个 agent 各一份

    @pytest.mark.asyncio
    async def test_same_agent_same_type_date_conflict(self, db_session):
        """同 agent + 同 type + 同 date 应冲突"""
        from datetime import date
        from sqlalchemy.exc import IntegrityError
        today = date.today()

        db_session.add(DailyReport(
            agent_key="investment", report_type="morning", report_date=today, content="c1"
        ))
        await db_session.commit()

        db_session.add(DailyReport(
            agent_key="investment", report_type="morning", report_date=today, content="c2"
        ))
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestSkillAgentIsolation:
    @pytest.mark.asyncio
    async def test_same_slug_different_agent_allowed(self, db_session):
        """skills.slug 不再全局唯一，改为 (agent_key, slug) 唯一"""
        db_session.add_all([
            Skill(agent_key="investment", slug="scorer", name="投研评分",
                  skill_type="scorer", config={}, is_builtin=True),
            Skill(agent_key="tech_info", slug="scorer", name="技术评分",
                  skill_type="scorer", config={}, is_builtin=True),
            Skill(agent_key="cs2_market", slug="scorer", name="CS2 评分",
                  skill_type="scorer", config={}, is_builtin=True),
        ])
        await db_session.commit()

        count = (await db_session.execute(select(func.count(Skill.id)))).scalar()
        assert count == 3

    @pytest.mark.asyncio
    async def test_same_agent_same_slug_conflict(self, db_session):
        from sqlalchemy.exc import IntegrityError
        db_session.add(Skill(
            agent_key="investment", slug="dup", name="n1",
            skill_type="scorer", config={}, is_builtin=True,
        ))
        await db_session.commit()

        db_session.add(Skill(
            agent_key="investment", slug="dup", name="n2",
            skill_type="monitor", config={}, is_builtin=True,
        ))
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestAlertAgentIsolation:
    @pytest.mark.asyncio
    async def test_alerts_filtered_by_agent_key(self, db_session):
        db_session.add_all([
            Alert(agent_key="investment", level="high", title="Inv alert", description="d"),
            Alert(agent_key="tech_info", level="medium", title="Tech alert", description="d"),
        ])
        await db_session.commit()

        invest_alerts = (await db_session.execute(
            select(Alert).where(Alert.agent_key == "investment")
        )).scalars().all()
        tech_alerts = (await db_session.execute(
            select(Alert).where(Alert.agent_key == "tech_info")
        )).scalars().all()

        assert len(invest_alerts) == 1
        assert len(tech_alerts) == 1
        assert invest_alerts[0].title == "Inv alert"
        assert tech_alerts[0].title == "Tech alert"


class TestAgentRegistry:
    def test_three_agents_registered_idempotent(self):
        """多次调用 register_* 不产生副作用"""
        from app.platform.registry import AgentRegistry
        from app.agents.investment import register_investment_agent
        from app.agents.tech_info import register_tech_info_agent
        from app.agents.cs2_market import register_cs2_market_agent

        reg = AgentRegistry()
        register_investment_agent(reg)
        register_tech_info_agent(reg)
        register_cs2_market_agent(reg)

        # 再注册一次（lifespan 重复启动场景）
        register_investment_agent(reg)
        register_tech_info_agent(reg)
        register_cs2_market_agent(reg)

        agents = reg.list_agents()
        assert len(agents) == 3
        keys = {a.key for a in agents}
        assert keys == {"investment", "tech_info", "cs2_market"}

    def test_registry_get_by_key(self):
        from app.platform.registry import AgentRegistry
        from app.agents.cs2_market import register_cs2_market_agent

        reg = AgentRegistry()
        register_cs2_market_agent(reg)
        manifest = reg.get("cs2_market")
        assert manifest.name == "CS2 饰品市场"
        assert len(manifest.builtin_skills) == 2

    def test_registry_get_missing_raises(self):
        from app.platform.registry import AgentRegistry
        reg = AgentRegistry()
        with pytest.raises(KeyError):
            reg.get("nonexistent_agent")

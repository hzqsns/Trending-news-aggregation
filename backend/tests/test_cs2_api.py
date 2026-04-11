"""T11: CS2 API 集成测试 — httpx AsyncClient + FastAPI ASGI"""
import pytest
import pytest_asyncio
from datetime import datetime
from httpx import AsyncClient, ASGITransport

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database import Base, get_session
from app.models.user import User
from app.models.cs2_item import CS2Item
from app.models.cs2_price import CS2PriceSnapshot
from app.auth import hash_password, create_access_token


# 使用独立的测试 engine，避免影响全局
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_app():
    """创建隔离的 FastAPI app + 内存 DB"""
    # 导入所有 model 确保 Base.metadata 完整
    from app.models.article import Article  # noqa: F401
    from app.models.alert import Alert  # noqa: F401
    from app.models.report import DailyReport  # noqa: F401
    from app.models.skill import Skill  # noqa: F401
    from app.models.sentiment import SentimentSnapshot  # noqa: F401
    from app.models.setting import SystemSetting  # noqa: F401
    from app.models.bookmark import ArticleBookmark  # noqa: F401
    from app.models.calendar_event import CalendarEvent  # noqa: F401
    from app.models.macro_indicator import MacroDataPoint  # noqa: F401
    from app.models.historical_event import HistoricalEvent  # noqa: F401
    from app.models.cs2_prediction import CS2Prediction  # noqa: F401
    from app.models.cs2_watchlist import CS2Watchlist  # noqa: F401

    engine = create_async_engine(TEST_DB_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 用 override 替换 get_session 依赖
    async def override_get_session():
        async with session_factory() as session:
            yield session

    # 构造一个最小 FastAPI app，只挂载 CS2 router
    from fastapi import FastAPI
    from app.agents.cs2_market.routes import router as cs2_router
    app = FastAPI()
    app.include_router(cs2_router)
    app.dependency_overrides[get_session] = override_get_session

    yield app, session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def auth_token(test_app):
    """创建测试用户并返回 JWT token"""
    _app, session_factory = test_app
    async with session_factory() as session:
        user = User(username="testuser", hashed_password=hash_password("testpass"))
        session.add(user)
        await session.commit()

    token = create_access_token("testuser")
    return token


@pytest_asyncio.fixture
async def client(test_app, auth_token):
    app, _ = test_app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {auth_token}"
        yield ac


@pytest_asyncio.fixture
async def sample_items(test_app):
    _app, session_factory = test_app
    async with session_factory() as session:
        items = [
            CS2Item(
                market_hash_name="AK-47 | Redline (FT)",
                display_name="AK-47 红线",
                category="rifle",
                subcategory="ak47",
                rarity="classified",
                is_tracked=True,
            ),
            CS2Item(
                market_hash_name="AWP | Dragon Lore (FN)",
                display_name="AWP 龙狙",
                category="rifle",
                subcategory="awp",
                rarity="covert",
                is_tracked=True,
            ),
            CS2Item(
                market_hash_name="★ Karambit | Fade (FN)",
                display_name="爪子刀 渐变",
                category="knife",
                subcategory="karambit",
                rarity="covert",
                is_tracked=True,
            ),
        ]
        session.add_all(items)
        await session.commit()
        for item in items:
            await session.refresh(item)
        return items


# =============================== TESTS ===============================

class TestAuth:
    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, test_app):
        app, _ = test_app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/cs2/market/overview")
            assert response.status_code == 401


class TestMarketOverview:
    @pytest.mark.asyncio
    async def test_empty_db_returns_safe_defaults(self, client):
        response = await client.get("/api/cs2/market/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] == 0
        assert data["total_market_cap"] == 0
        assert data["total_volume"] == 0
        assert data["gainers"] == 0
        assert data["losers"] == 0
        assert data["sentiment_index"] == 50  # 中性默认

    @pytest.mark.asyncio
    async def test_with_items_counts(self, client, sample_items):
        response = await client.get("/api/cs2/market/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] == 3


class TestHotItems:
    @pytest.mark.asyncio
    async def test_empty_returns_empty_list(self, client):
        response = await client.get("/api/cs2/market/hot-items")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_limit_param(self, client):
        response = await client.get("/api/cs2/market/hot-items?limit=5")
        assert response.status_code == 200


class TestRankings:
    @pytest.mark.asyncio
    async def test_empty_returns_zero_total(self, client):
        response = await client.get("/api/cs2/rankings")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_with_items_but_no_snapshots_returns_empty(self, client, sample_items):
        """有 items 但没有价格快照时，排行榜为空（需至少 2 个快照对比涨跌）"""
        response = await client.get("/api/cs2/rankings?period=24h&direction=gainers")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_rankings_with_snapshots(self, client, sample_items, test_app):
        """创建两个时间点的快照，验证排序"""
        _app, session_factory = test_app
        now = datetime.utcnow()
        from datetime import timedelta
        earlier = now - timedelta(hours=12)

        async with session_factory() as session:
            session.add_all([
                CS2PriceSnapshot(item_id=sample_items[0].id, price=100.0, snapshot_time=earlier),
                CS2PriceSnapshot(item_id=sample_items[0].id, price=110.0, snapshot_time=now),  # +10%
                CS2PriceSnapshot(item_id=sample_items[1].id, price=200.0, snapshot_time=earlier),
                CS2PriceSnapshot(item_id=sample_items[1].id, price=180.0, snapshot_time=now),  # -10%
            ])
            await session.commit()

        # 涨幅榜
        response = await client.get("/api/cs2/rankings?period=24h&direction=gainers")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # 两个都有涨跌数据
        # 第一条应是 AK-47（+10%）
        assert data["items"][0]["change_pct"] > 0

        # 跌幅榜
        response = await client.get("/api/cs2/rankings?period=24h&direction=losers")
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["change_pct"] < 0

    @pytest.mark.asyncio
    async def test_rankings_category_filter(self, client, sample_items):
        response = await client.get("/api/cs2/rankings?category=knife")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rankings_pagination(self, client):
        response = await client.get("/api/cs2/rankings?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert "page" in data
        assert "page_size" in data


class TestCategories:
    @pytest.mark.asyncio
    async def test_categories_empty(self, client):
        response = await client.get("/api/cs2/categories")
        assert response.status_code == 200
        assert response.json()["categories"] == []

    @pytest.mark.asyncio
    async def test_categories_groups_by_category(self, client, sample_items):
        response = await client.get("/api/cs2/categories")
        assert response.status_code == 200
        data = response.json()
        # 应有 rifle 和 knife 两个品类
        cat_ids = {c["id"] for c in data["categories"]}
        assert "rifle" in cat_ids
        assert "knife" in cat_ids

        # 验证 count
        rifle = next(c for c in data["categories"] if c["id"] == "rifle")
        assert rifle["item_count"] == 2  # AK + AWP


class TestItemDetail:
    @pytest.mark.asyncio
    async def test_item_not_found_returns_404(self, client):
        response = await client.get("/api/cs2/items/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_item_detail_returns_full_data(self, client, sample_items):
        item_id = sample_items[0].id
        response = await client.get(f"/api/cs2/items/{item_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "AK-47 红线"
        assert data["category"] == "rifle"
        assert data["current_price"] is None  # 无快照
        assert data["prediction"] is None


class TestItemKline:
    @pytest.mark.asyncio
    async def test_kline_empty(self, client, sample_items):
        response = await client.get(f"/api/cs2/items/{sample_items[0].id}/kline")
        assert response.status_code == 200
        data = response.json()
        assert data["points"] == []

    @pytest.mark.asyncio
    async def test_kline_with_snapshots(self, client, sample_items, test_app):
        _app, session_factory = test_app
        async with session_factory() as session:
            session.add_all([
                CS2PriceSnapshot(item_id=sample_items[0].id, price=100.0),
                CS2PriceSnapshot(item_id=sample_items[0].id, price=105.0),
                CS2PriceSnapshot(item_id=sample_items[0].id, price=110.0),
            ])
            await session.commit()

        response = await client.get(f"/api/cs2/items/{sample_items[0].id}/kline?period=7d")
        assert response.status_code == 200
        data = response.json()
        assert len(data["points"]) == 3
        assert data["points"][0]["price"] == 100.0


class TestWatchlistCRUD:
    @pytest.mark.asyncio
    async def test_add_watchlist(self, client, sample_items):
        item_id = sample_items[0].id
        response = await client.post(
            f"/api/cs2/watchlist?item_id={item_id}&target_price=100&alert_direction=above"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["item_id"] == item_id
        assert data["target_price"] == 100

    @pytest.mark.asyncio
    async def test_add_watchlist_nonexistent_item_returns_404(self, client):
        response = await client.post("/api/cs2/watchlist?item_id=99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_duplicate_returns_409(self, client, sample_items):
        item_id = sample_items[0].id
        r1 = await client.post(f"/api/cs2/watchlist?item_id={item_id}")
        assert r1.status_code == 200

        r2 = await client.post(f"/api/cs2/watchlist?item_id={item_id}")
        assert r2.status_code == 409

    @pytest.mark.asyncio
    async def test_list_watchlist(self, client, sample_items):
        item_id = sample_items[0].id
        await client.post(f"/api/cs2/watchlist?item_id={item_id}&target_price=100")

        response = await client.get("/api/cs2/watchlist")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["item_id"] == item_id

    @pytest.mark.asyncio
    async def test_update_watchlist(self, client, sample_items):
        item_id = sample_items[0].id
        add_resp = await client.post(f"/api/cs2/watchlist?item_id={item_id}&target_price=100")
        watch_id = add_resp.json()["id"]

        update_resp = await client.put(
            f"/api/cs2/watchlist/{watch_id}?target_price=200&alert_direction=below"
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["target_price"] == 200

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_404(self, client):
        response = await client.put("/api/cs2/watchlist/99999?target_price=100")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_watchlist(self, client, sample_items):
        item_id = sample_items[0].id
        add_resp = await client.post(f"/api/cs2/watchlist?item_id={item_id}")
        watch_id = add_resp.json()["id"]

        del_resp = await client.delete(f"/api/cs2/watchlist/{watch_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["ok"] is True

        # 再次查询为空
        list_resp = await client.get("/api/cs2/watchlist")
        assert list_resp.json()["items"] == []

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, client):
        response = await client.delete("/api/cs2/watchlist/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_watchlist_alerts_history(self, client):
        response = await client.get("/api/cs2/watchlist/alerts")
        assert response.status_code == 200
        assert response.json()["alerts"] == []


class TestPredictions:
    @pytest.mark.asyncio
    async def test_list_predictions_empty(self, client):
        response = await client.get("/api/cs2/predictions")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_regenerate_returns_400_when_predict_returns_none(self, client, sample_items):
        """mock predict_item 返回 None 时，路由应返回 400"""
        from unittest.mock import patch, AsyncMock
        with patch(
            "app.agents.cs2_market.predictor.predict_item",
            new=AsyncMock(return_value=None),
        ):
            response = await client.post(
                f"/api/cs2/predictions/regenerate?item_id={sample_items[0].id}&period=7d"
            )
        assert response.status_code == 400

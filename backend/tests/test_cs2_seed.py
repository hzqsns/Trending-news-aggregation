"""T10: CS2 种子清单幂等性测试"""
from unittest.mock import patch
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select, func

from app.agents.cs2_market import items_catalog
from app.agents.cs2_market.items_catalog import seed_initial_items, SEED_ITEMS
from app.models.cs2_item import CS2Item


@pytest.mark.asyncio
async def test_seed_items_structure():
    """验证种子清单结构合法"""
    assert len(SEED_ITEMS) > 0
    for item_tuple in SEED_ITEMS:
        assert len(item_tuple) == 5
        mhn, display, cat, sub, rarity = item_tuple
        assert isinstance(mhn, str) and mhn
        assert isinstance(display, str) and display
        assert isinstance(cat, str) and cat
        # sub 可以是 None
        assert sub is None or isinstance(sub, str)
        # rarity 可以是 None
        assert rarity is None or isinstance(rarity, str)


@pytest.mark.asyncio
async def test_seed_items_market_hash_name_unique():
    """种子清单里不应有重复的 market_hash_name"""
    names = [item[0] for item in SEED_ITEMS]
    assert len(names) == len(set(names)), "发现重复的 market_hash_name"


@pytest.mark.asyncio
async def test_seed_inserts_all_items_on_first_run(db_session):
    """首次运行应插入所有种子"""
    @asynccontextmanager
    async def fake_session_cm():
        yield db_session

    # Patch async_session 以使用测试 session
    with patch.object(items_catalog, "async_session", fake_session_cm):
        inserted = await seed_initial_items()

    assert inserted == len(SEED_ITEMS)

    count = (await db_session.execute(select(func.count(CS2Item.id)))).scalar()
    assert count == len(SEED_ITEMS)


@pytest.mark.asyncio
async def test_seed_idempotent_on_second_run(db_session):
    """已有数据时重复调用应返回 0 且不重复插入"""
    @asynccontextmanager
    async def fake_session_cm():
        yield db_session

    with patch.object(items_catalog, "async_session", fake_session_cm):
        # 第一次
        inserted1 = await seed_initial_items()
        # 第二次
        inserted2 = await seed_initial_items()
        # 第三次
        inserted3 = await seed_initial_items()

    assert inserted1 == len(SEED_ITEMS)
    assert inserted2 == 0
    assert inserted3 == 0

    # 数据库中 items 数量不变
    count = (await db_session.execute(select(func.count(CS2Item.id)))).scalar()
    assert count == len(SEED_ITEMS)


@pytest.mark.asyncio
async def test_seed_items_are_tracked_by_default(db_session):
    @asynccontextmanager
    async def fake_session_cm():
        yield db_session

    with patch.object(items_catalog, "async_session", fake_session_cm):
        await seed_initial_items()

    items = (await db_session.execute(select(CS2Item))).scalars().all()
    assert all(item.is_tracked for item in items)


@pytest.mark.asyncio
async def test_seed_covers_main_categories(db_session):
    """种子清单应覆盖主要品类"""
    @asynccontextmanager
    async def fake_session_cm():
        yield db_session

    with patch.object(items_catalog, "async_session", fake_session_cm):
        await seed_initial_items()

    categories = set(
        (await db_session.execute(select(CS2Item.category).distinct())).scalars().all()
    )
    # 必须包含核心品类
    required = {"knife", "gloves", "rifle", "pistol"}
    assert required.issubset(categories), f"缺少核心品类: {required - categories}"

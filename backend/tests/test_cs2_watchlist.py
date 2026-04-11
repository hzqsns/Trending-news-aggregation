"""T4: CS2 Watchlist 权限隔离 + 409 冲突 — 集成测试"""
import pytest

from app.models.cs2_item import CS2Item
from app.models.cs2_watchlist import CS2Watchlist
from app.models.user import User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_watchlist_unique_constraint_prevents_duplicate(db_session):
    """同 user + 同 item 不能重复添加（UniqueConstraint uq_cs2_watch_user_item）"""
    user = User(username="u1", hashed_password="hash")
    item = CS2Item(
        market_hash_name="AK-47 | Redline",
        display_name="AK-47 红线",
        category="rifle",
        is_tracked=True,
    )
    db_session.add_all([user, item])
    await db_session.commit()

    w1 = CS2Watchlist(user_id=user.id, item_id=item.id, target_price=100.0, alert_direction="above")
    db_session.add(w1)
    await db_session.commit()

    # 第二次相同组合应触发 IntegrityError
    from sqlalchemy.exc import IntegrityError
    w2 = CS2Watchlist(user_id=user.id, item_id=item.id, target_price=200.0, alert_direction="below")
    db_session.add(w2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_watchlist_different_users_same_item_allowed(db_session):
    """两个不同用户可以收藏同一饰品"""
    user_a = User(username="userA", hashed_password="hash")
    user_b = User(username="userB", hashed_password="hash")
    item = CS2Item(
        market_hash_name="AWP | Dragon Lore",
        display_name="AWP 龙狙",
        category="rifle",
        is_tracked=True,
    )
    db_session.add_all([user_a, user_b, item])
    await db_session.commit()

    wa = CS2Watchlist(user_id=user_a.id, item_id=item.id, target_price=10000.0, alert_direction="below")
    wb = CS2Watchlist(user_id=user_b.id, item_id=item.id, target_price=15000.0, alert_direction="above")
    db_session.add_all([wa, wb])
    await db_session.commit()

    result = await db_session.execute(select(CS2Watchlist))
    watches = result.scalars().all()
    assert len(watches) == 2
    assert {w.user_id for w in watches} == {user_a.id, user_b.id}


@pytest.mark.asyncio
async def test_watchlist_user_isolation_query(db_session):
    """查询只能看到自己的 watchlist（模拟 routes.py 的 WHERE user_id 过滤）"""
    user_a = User(username="alice", hashed_password="h")
    user_b = User(username="bob", hashed_password="h")
    item1 = CS2Item(market_hash_name="item1", display_name="I1", category="rifle", is_tracked=True)
    item2 = CS2Item(market_hash_name="item2", display_name="I2", category="pistol", is_tracked=True)
    db_session.add_all([user_a, user_b, item1, item2])
    await db_session.commit()

    db_session.add_all([
        CS2Watchlist(user_id=user_a.id, item_id=item1.id),
        CS2Watchlist(user_id=user_a.id, item_id=item2.id),
        CS2Watchlist(user_id=user_b.id, item_id=item1.id),
    ])
    await db_session.commit()

    alice_watches = (await db_session.execute(
        select(CS2Watchlist).where(CS2Watchlist.user_id == user_a.id)
    )).scalars().all()
    bob_watches = (await db_session.execute(
        select(CS2Watchlist).where(CS2Watchlist.user_id == user_b.id)
    )).scalars().all()

    assert len(alice_watches) == 2
    assert len(bob_watches) == 1
    # 确保 bob 看不到 alice 的
    assert all(w.user_id == user_a.id for w in alice_watches)
    assert all(w.user_id == user_b.id for w in bob_watches)


@pytest.mark.asyncio
async def test_watchlist_default_not_triggered(db_session):
    """新建 watch 默认未触发"""
    user = User(username="u", hashed_password="h")
    item = CS2Item(market_hash_name="mhn", display_name="n", category="rifle", is_tracked=True)
    db_session.add_all([user, item])
    await db_session.commit()

    w = CS2Watchlist(user_id=user.id, item_id=item.id, target_price=50.0, alert_direction="above")
    db_session.add(w)
    await db_session.commit()
    await db_session.refresh(w)

    assert w.triggered is False
    assert w.triggered_at is None


@pytest.mark.asyncio
async def test_watchlist_to_dict_shape(db_session):
    """to_dict() 返回正确字段结构"""
    user = User(username="u", hashed_password="h")
    item = CS2Item(market_hash_name="mhn", display_name="n", category="rifle", is_tracked=True)
    db_session.add_all([user, item])
    await db_session.commit()

    w = CS2Watchlist(
        user_id=user.id,
        item_id=item.id,
        target_price=100.5,
        alert_direction="below",
    )
    db_session.add(w)
    await db_session.commit()
    await db_session.refresh(w)

    d = w.to_dict()
    assert d["user_id"] == user.id
    assert d["item_id"] == item.id
    assert d["target_price"] == 100.5
    assert d["alert_direction"] == "below"
    assert d["triggered"] is False
    assert "created_at" in d

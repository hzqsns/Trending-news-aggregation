"""Tests for historical events — CRUD, seed, validation."""
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.historical_event import HistoricalEvent
from app.api.historical_events import (
    _BUILTIN_EVENTS, VALID_CATEGORIES, VALID_IMPACTS,
)


# ---------------------------------------------------------------------------
# Builtin events data integrity
# ---------------------------------------------------------------------------

def test_builtin_events_count():
    """There should be 10 builtin events."""
    assert len(_BUILTIN_EVENTS) == 10


def test_builtin_events_have_valid_categories():
    for ev in _BUILTIN_EVENTS:
        assert ev["category"] in VALID_CATEGORIES, f"'{ev['title']}' has invalid category '{ev['category']}'"


def test_builtin_events_have_valid_impacts():
    for ev in _BUILTIN_EVENTS:
        assert ev["market_impact"] in VALID_IMPACTS, f"'{ev['title']}' has invalid impact '{ev['market_impact']}'"


def test_builtin_events_titles_are_unique():
    titles = [ev["title"] for ev in _BUILTIN_EVENTS]
    assert len(titles) == len(set(titles)), "Duplicate titles in builtin events"


def test_builtin_events_all_have_key_metrics():
    for ev in _BUILTIN_EVENTS:
        assert "key_metrics" in ev, f"'{ev['title']}' missing key_metrics"
        assert isinstance(ev["key_metrics"], list)
        assert len(ev["key_metrics"]) >= 2, f"'{ev['title']}' should have at least 2 key metrics"
        for m in ev["key_metrics"]:
            assert "label" in m and "value" in m


# ---------------------------------------------------------------------------
# DB operations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_event(db_session):
    event = HistoricalEvent(
        title="Test Crisis",
        category="financial_crisis",
        date_range="2025-01 ~ 2025-06",
        market_impact="bearish",
        description="A test event",
        key_metrics=[{"label": "Drop", "value": "-50%"}],
        is_builtin=False,
        created_at=datetime.utcnow(),
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    assert event.id is not None
    assert event.title == "Test Crisis"
    assert event.is_builtin is False


@pytest.mark.asyncio
async def test_create_and_query_event(db_session):
    event = HistoricalEvent(
        title="Pandemic Shock",
        category="pandemic",
        date_range="2020-02 ~ 2020-04",
        market_impact="bearish",
        is_builtin=False,
        created_at=datetime.utcnow(),
    )
    db_session.add(event)
    await db_session.commit()

    rows = (await db_session.scalars(
        select(HistoricalEvent).where(HistoricalEvent.category == "pandemic")
    )).all()
    assert len(rows) == 1
    assert rows[0].title == "Pandemic Shock"


@pytest.mark.asyncio
async def test_to_dict(db_session):
    event = HistoricalEvent(
        title="Dict Test",
        category="monetary_policy",
        date_range="2023-01 ~ 2023-12",
        market_impact="bullish",
        key_metrics=[{"label": "Rate", "value": "0.25%"}],
        is_builtin=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    d = event.to_dict()
    assert d["title"] == "Dict Test"
    assert d["category"] == "monetary_policy"
    assert d["is_builtin"] is True
    assert isinstance(d["key_metrics"], list)
    assert d["key_metrics"][0]["label"] == "Rate"


@pytest.mark.asyncio
async def test_seed_idempotent(db_session):
    """Seeding builtin events twice should not create duplicates."""
    for data in _BUILTIN_EVENTS[:3]:
        db_session.add(HistoricalEvent(**data, is_builtin=True, created_at=datetime.utcnow()))
    await db_session.commit()

    # Seed again — should skip existing
    added = 0
    for data in _BUILTIN_EVENTS[:3]:
        existing = await db_session.scalar(
            select(HistoricalEvent).where(
                HistoricalEvent.title == data["title"],
                HistoricalEvent.is_builtin.is_(True),
            )
        )
        if not existing:
            db_session.add(HistoricalEvent(**data, is_builtin=True, created_at=datetime.utcnow()))
            added += 1
    await db_session.commit()

    assert added == 0

    rows = (await db_session.scalars(select(HistoricalEvent))).all()
    assert len(rows) == 3


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_valid_categories_set():
    expected = {"financial_crisis", "monetary_policy", "pandemic", "tech_bubble", "geopolitics"}
    assert VALID_CATEGORIES == expected


def test_valid_impacts_set():
    expected = {"bullish", "bearish", "mixed"}
    assert VALID_IMPACTS == expected

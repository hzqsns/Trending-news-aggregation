"""Tests for macro indicators — FRED parsing, DB storage, analysis prompt."""
import csv
import io
from datetime import date, datetime
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.macro_indicator import MacroDataPoint
from app.api.macro import _fetch_and_store_series, FRED_SERIES, _ANALYSIS_PROMPT


# ---------------------------------------------------------------------------
# FRED CSV parsing + storage
# ---------------------------------------------------------------------------

SAMPLE_CSV = """DATE,VALUE
2024-01-01,21500.5
2024-02-01,21600.3
2024-03-01,.
2024-04-01,21750.0
"""


@pytest.mark.asyncio
async def test_fetch_and_store_parses_csv_and_inserts(db_session):
    """Normal flow: FRED CSV is fetched, parsed, and stored with MoM computed."""
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_CSV
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.macro.httpx.AsyncClient", return_value=mock_client):
        count = await _fetch_and_store_series("M2SL", db_session)

    # "." row is skipped → 3 rows inserted
    assert count == 3

    rows = (await db_session.scalars(
        select(MacroDataPoint)
        .where(MacroDataPoint.series_id == "M2SL")
        .order_by(MacroDataPoint.data_date.asc())
    )).all()
    assert len(rows) == 3
    assert rows[0].data_date == date(2024, 1, 1)
    assert rows[0].value == 21500.5
    assert rows[0].mom is None  # first row has no predecessor
    assert rows[1].mom is not None  # second row should have MoM
    assert round(rows[1].mom, 4) == round(21600.3 - 21500.5, 4)


@pytest.mark.asyncio
async def test_fetch_and_store_replaces_on_refresh(db_session):
    """Running fetch twice should DELETE+INSERT cleanly (no duplicates)."""
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_CSV
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.macro.httpx.AsyncClient", return_value=mock_client):
        await _fetch_and_store_series("FEDFUNDS", db_session)
        count2 = await _fetch_and_store_series("FEDFUNDS", db_session)

    assert count2 == 3
    rows = (await db_session.scalars(
        select(MacroDataPoint).where(MacroDataPoint.series_id == "FEDFUNDS")
    )).all()
    assert len(rows) == 3  # no duplicates


@pytest.mark.asyncio
async def test_fetch_empty_csv_returns_zero(db_session):
    """CSV with only header returns 0 and inserts nothing."""
    mock_resp = MagicMock()
    mock_resp.text = "DATE,VALUE\n"
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.macro.httpx.AsyncClient", return_value=mock_client):
        count = await _fetch_and_store_series("UNRATE", db_session)

    assert count == 0


# ---------------------------------------------------------------------------
# CPI YoY calculation
# ---------------------------------------------------------------------------

CPI_CSV = """DATE,VALUE
2023-01-01,300.0
2024-01-01,312.0
"""


@pytest.mark.asyncio
async def test_cpi_yoy_computed(db_session):
    """CPIAUCSL series should compute YoY inflation rate."""
    mock_resp = MagicMock()
    mock_resp.text = CPI_CSV
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.macro.httpx.AsyncClient", return_value=mock_client):
        await _fetch_and_store_series("CPIAUCSL", db_session)

    rows = (await db_session.scalars(
        select(MacroDataPoint)
        .where(MacroDataPoint.series_id == "CPIAUCSL")
        .order_by(MacroDataPoint.data_date.asc())
    )).all()
    assert rows[0].yoy is None  # 2023-01 has no prior year
    assert rows[1].yoy == pytest.approx(4.0, abs=0.01)  # (312/300-1)*100 = 4.0%


# ---------------------------------------------------------------------------
# FRED_SERIES config
# ---------------------------------------------------------------------------

def test_fred_series_has_required_keys():
    """All FRED_SERIES entries should have label, unit, and freq."""
    for series_id, meta in FRED_SERIES.items():
        assert "label" in meta, f"{series_id} missing label"
        assert "unit" in meta, f"{series_id} missing unit"
        assert "freq" in meta, f"{series_id} missing freq"


# ---------------------------------------------------------------------------
# Analysis prompt
# ---------------------------------------------------------------------------

def test_analysis_prompt_format():
    """The prompt template should format without errors."""
    result = _ANALYSIS_PROMPT.format(indicators_text="- Test: 100%")
    assert "Test: 100%" in result
    assert '"environment"' in result  # escaped braces should produce literal JSON
    assert '"impacts"' in result

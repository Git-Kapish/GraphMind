"""Unit tests for Scale Ingestion, Dry-Run, and Checkpoint Recovery (PRD §5.7, FR-1.6, M9)."""

import pytest
from unittest.mock import MagicMock, patch

from kgrag.ingest import (
    DEV_TICKERS,
    EXPANDED_TICKERS,
    FULL_TICKERS,
    get_latest_checkpoint_status,
    get_tickers_for_subset,
    record_checkpoint,
    reset_failed_checkpoints,
)


def test_get_tickers_for_subset():
    assert get_tickers_for_subset("dev") == DEV_TICKERS
    assert get_tickers_for_subset("expanded") == EXPANDED_TICKERS
    assert get_tickers_for_subset("full") == FULL_TICKERS
    assert get_tickers_for_subset("qcom,aapl") == ["QCOM", "AAPL"]

    with pytest.raises(ValueError):
        get_tickers_for_subset("   ")


def test_checkpoint_journal_lifecycle():
    test_run_id = "test_run_unit_001"
    test_ticker = "TEST_TICKER"

    # Record started checkpoint
    record_checkpoint(
        run_id=test_run_id,
        ticker=test_ticker,
        stage="chunking",
        status="started",
        records_processed=0,
    )
    assert get_latest_checkpoint_status(test_ticker, "chunking") == "started"

    # Record completed checkpoint
    record_checkpoint(
        run_id=test_run_id,
        ticker=test_ticker,
        stage="chunking",
        status="completed",
        records_processed=42,
        elapsed_seconds=1.23,
        metadata={"sections": ["item1", "item1a"]},
    )
    assert get_latest_checkpoint_status(test_ticker, "chunking") == "completed"

    # Non-existent stage returns None
    assert get_latest_checkpoint_status(test_ticker, "non_existent_stage") is None


def test_reset_failed_checkpoints():
    test_run_id = "test_run_unit_failed"
    test_ticker = "TEST_FAIL"

    record_checkpoint(
        run_id=test_run_id,
        ticker=test_ticker,
        stage="llm_extraction",
        status="failed",
        metadata={"error": "timeout"},
    )
    assert get_latest_checkpoint_status(test_ticker, "llm_extraction") == "failed"

    cleared = reset_failed_checkpoints()
    assert cleared >= 1
    # After reset, the failed record is deleted
    assert get_latest_checkpoint_status(test_ticker, "llm_extraction") is None

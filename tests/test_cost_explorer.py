"""Testes unitários para scripts/aws/cost_explorer.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scripts.aws.cost_explorer import (
    CostRecord,
    CostReport,
    fetch_costs,
    get_date_range,
    save_json,
)


def test_get_date_range_returns_correct_format() -> None:
    start, end = get_date_range(30)
    assert len(start) == 10
    assert len(end) == 10
    assert start < end


def test_cost_report_total() -> None:
    report = CostReport(period_start="2024-01-01", period_end="2024-01-31", group_by="SERVICE")
    report.records = [
        CostRecord(dimension="EC2", amount=100.0),
        CostRecord(dimension="RDS", amount=50.5),
        CostRecord(dimension="S3", amount=10.25),
    ]
    assert report.total == 160.75


def test_cost_report_top_n() -> None:
    report = CostReport(period_start="2024-01-01", period_end="2024-01-31", group_by="SERVICE")
    report.records = [
        CostRecord(dimension="EC2", amount=500.0),
        CostRecord(dimension="RDS", amount=200.0),
        CostRecord(dimension="S3", amount=50.0),
        CostRecord(dimension="Lambda", amount=10.0),
    ]
    top2 = report.top_n(2)
    assert len(top2) == 2
    assert top2[0].dimension == "EC2"
    assert top2[1].dimension == "RDS"


def test_fetch_costs_raises_on_tag_without_key() -> None:
    with pytest.raises(ValueError, match="tag_key é obrigatório"):
        fetch_costs(days=7, group_by="TAG", tag_key=None)


@patch("scripts.aws.cost_explorer.boto3.client")
def test_fetch_costs_success(mock_boto: MagicMock) -> None:
    mock_ce = MagicMock()
    mock_boto.return_value = mock_ce
    mock_ce.get_cost_and_usage.return_value = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2024-01-01", "End": "2024-01-31"},
                "Groups": [
                    {
                        "Keys": ["Amazon EC2"],
                        "Metrics": {"UnblendedCost": {"Amount": "1234.56", "Unit": "USD"}},
                    }
                ],
            }
        ]
    }

    report = fetch_costs(days=30, group_by="SERVICE")
    assert len(report.records) == 1
    assert report.records[0].dimension == "Amazon EC2"
    assert report.records[0].amount == 1234.56
    assert report.total == 1234.56


def test_save_json(tmp_path: "Path") -> None:
    report = CostReport(period_start="2024-01-01", period_end="2024-01-31", group_by="SERVICE")
    report.records = [CostRecord(dimension="EC2", amount=100.0, period_start="2024-01-01", period_end="2024-01-31")]

    output = tmp_path / "test_output.json"
    save_json(report, str(output))

    assert output.exists()
    import json
    data = json.loads(output.read_text())
    assert data["total_usd"] == 100.0
    assert len(data["records"]) == 1

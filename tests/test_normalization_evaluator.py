from __future__ import annotations

import json
from pathlib import Path

from app.normalization_evaluator import evaluate_expectation_directory


def test_evaluator_passes_repository_fixture_corpus() -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    expectation_dir = fixture_dir / "normalization_expectations"

    report = evaluate_expectation_directory(fixture_dir=fixture_dir, expectation_dir=expectation_dir)

    assert report["total_fixtures"] == 2
    assert report["failed"] == 0
    assert report["passed"] == 2


def test_evaluator_reports_missing_fixture_as_failure(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir(parents=True)
    expectation_dir = tmp_path / "expectations"
    expectation_dir.mkdir(parents=True)

    expectation_path = expectation_dir / "missing_fixture.json"
    expectation_path.write_text(
        json.dumps(
            {
                "fixture": "does-not-exist.eml",
                "checks": {
                    "preferred_message_source": "text/plain",
                },
            }
        ),
        encoding="utf-8",
    )

    report = evaluate_expectation_directory(fixture_dir=fixture_dir, expectation_dir=expectation_dir)

    assert report["total_fixtures"] == 1
    assert report["failed"] == 1
    assert report["results"][0]["checks"][0]["name"] == "fixture.exists"
    assert report["results"][0]["checks"][0]["passed"] is False

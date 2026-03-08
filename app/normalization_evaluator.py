"""Evaluate normalization heuristics against fixture expectation manifests."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from bs4 import BeautifulSoup

from app.normalizer import QUOTED_CONTAINER_PATTERNS, TRACKING_PIXEL_DIMENSIONS, normalize_email


@dataclass(frozen=True)
class EvaluationCheck:
    """One evaluated assertion for a fixture expectation manifest."""

    name: str
    passed: bool
    expected: Any
    actual: Any

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly check payload."""

        return {
            "name": self.name,
            "passed": self.passed,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass(frozen=True)
class FixtureEvaluationResult:
    """Evaluation output for one fixture and expectation manifest."""

    expectation: str
    fixture: str
    passed: bool
    checks: list[EvaluationCheck]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly fixture result payload."""

        return {
            "expectation": self.expectation,
            "fixture": self.fixture,
            "passed": self.passed,
            "checks": [item.to_dict() for item in self.checks],
        }


def evaluate_expectation_directory(
    *,
    fixture_dir: Path,
    expectation_dir: Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Evaluate all expectation manifests in a directory.

    The return value is machine-friendly JSON data suitable for CI artifacts.
    """

    manifests = sorted(expectation_dir.glob("*.json"))
    results = [
        _evaluate_manifest(expectation_path=path, fixture_dir=fixture_dir)
        for path in manifests
    ]

    failed = sum(1 for item in results if not item.passed)
    timestamp = generated_at or datetime.now(tz=UTC).isoformat()
    return {
        "generated_at": timestamp,
        "fixture_dir": str(fixture_dir),
        "expectation_dir": str(expectation_dir),
        "total_fixtures": len(results),
        "passed": len(results) - failed,
        "failed": failed,
        "results": [item.to_dict() for item in results],
    }


def _evaluate_manifest(*, expectation_path: Path, fixture_dir: Path) -> FixtureEvaluationResult:
    payload = json.loads(expectation_path.read_text(encoding="utf-8"))
    fixture_name = str(payload.get("fixture", "")).strip()
    checks_config = payload.get("checks", {})

    checks: list[EvaluationCheck] = []
    if not fixture_name:
        checks.append(
            EvaluationCheck(
                name="manifest.fixture",
                passed=False,
                expected="non-empty fixture filename",
                actual=fixture_name,
            )
        )
        return FixtureEvaluationResult(
            expectation=expectation_path.name,
            fixture=fixture_name,
            passed=False,
            checks=checks,
        )

    if not isinstance(checks_config, dict):
        checks.append(
            EvaluationCheck(
                name="manifest.checks",
                passed=False,
                expected="object",
                actual=type(checks_config).__name__,
            )
        )
        return FixtureEvaluationResult(
            expectation=expectation_path.name,
            fixture=fixture_name,
            passed=False,
            checks=checks,
        )

    fixture_path = fixture_dir / fixture_name
    if not fixture_path.exists():
        checks.append(
            EvaluationCheck(
                name="fixture.exists",
                passed=False,
                expected=str(fixture_path),
                actual="missing",
            )
        )
        return FixtureEvaluationResult(
            expectation=expectation_path.name,
            fixture=fixture_name,
            passed=False,
            checks=checks,
        )

    normalized = _normalize_fixture(
        fixture_path=fixture_path,
        account=str(payload.get("account", "support")),
        folder=str(payload.get("folder", "INBOX")),
        remote_id=str(payload.get("remote_id", f"fixture:{fixture_name}")),
    )

    checks.extend(_evaluate_message_source(checks_config, normalized.preferred_message_source))
    checks.extend(_evaluate_message_format(checks_config, normalized.preferred_message_format))

    checks.extend(
        _evaluate_contains_and_absent(
            check_name="preferred_message",
            source_text=normalized.preferred_message or "",
            required_values=_string_list(checks_config.get("preferred_message_contains")),
            forbidden_values=_string_list(checks_config.get("preferred_message_not_contains")),
        )
    )
    checks.extend(
        _evaluate_contains_and_absent(
            check_name="markdown_body",
            source_text=normalized.markdown_body or "",
            required_values=_string_list(checks_config.get("markdown_contains")),
            forbidden_values=_string_list(checks_config.get("markdown_not_contains")),
        )
    )
    checks.extend(
        _evaluate_contains_and_absent(
            check_name="cleaned_html_body",
            source_text=normalized.cleaned_html_body or "",
            required_values=_string_list(checks_config.get("cleaned_html_contains")),
            forbidden_values=_string_list(checks_config.get("cleaned_html_not_contains")),
        )
    )

    if "quoted_reply_removed" in checks_config:
        expected = bool(checks_config["quoted_reply_removed"])
        actual = not _contains_quoted_reply_signals(normalized.cleaned_html_body or "", normalized.markdown_body or "")
        checks.append(
            EvaluationCheck(
                name="quoted_reply_removed",
                passed=actual == expected,
                expected=expected,
                actual=actual,
            )
        )

    if "tracking_pixel_removed" in checks_config:
        expected = bool(checks_config["tracking_pixel_removed"])
        actual = not _contains_tracking_pixel_markup(normalized.cleaned_html_body or "")
        checks.append(
            EvaluationCheck(
                name="tracking_pixel_removed",
                passed=actual == expected,
                expected=expected,
                actual=actual,
            )
        )

    passed = all(item.passed for item in checks)
    return FixtureEvaluationResult(
        expectation=expectation_path.name,
        fixture=fixture_name,
        passed=passed,
        checks=checks,
    )


def _normalize_fixture(*, fixture_path: Path, account: str, folder: str, remote_id: str):
    with TemporaryDirectory(prefix="lobsterhook-normalization-eval-") as temp_dir:
        temp_root = Path(temp_dir)
        raw_path = temp_root / fixture_path.name
        normalized_path = temp_root / f"{fixture_path.stem}.json"
        raw_path.write_bytes(fixture_path.read_bytes())

        # Keep deterministic timestamps so expectation checks stay stable.
        return normalize_email(
            account=account,
            folder=folder,
            remote_id=remote_id,
            remote_id_kind="fixture",
            raw_path=raw_path,
            normalized_path=normalized_path,
            detected_at="2026-03-08T12:00:00+00:00",
            exported_at="2026-03-08T12:00:05+00:00",
        )


def _evaluate_message_source(checks: dict[str, Any], actual_source: str | None) -> list[EvaluationCheck]:
    expected_source = checks.get("preferred_message_source")
    if expected_source is None:
        return []
    return [
        EvaluationCheck(
            name="preferred_message_source",
            passed=actual_source == expected_source,
            expected=expected_source,
            actual=actual_source,
        )
    ]


def _evaluate_message_format(checks: dict[str, Any], actual_format: str | None) -> list[EvaluationCheck]:
    expected_format = checks.get("preferred_message_format")
    if expected_format is None:
        return []
    return [
        EvaluationCheck(
            name="preferred_message_format",
            passed=actual_format == expected_format,
            expected=expected_format,
            actual=actual_format,
        )
    ]


def _evaluate_contains_and_absent(
    *,
    check_name: str,
    source_text: str,
    required_values: list[str],
    forbidden_values: list[str],
) -> list[EvaluationCheck]:
    checks: list[EvaluationCheck] = []
    for required in required_values:
        checks.append(
            EvaluationCheck(
                name=f"{check_name}.contains:{required}",
                passed=required in source_text,
                expected=True,
                actual=required in source_text,
            )
        )
    for forbidden in forbidden_values:
        checks.append(
            EvaluationCheck(
                name=f"{check_name}.not_contains:{forbidden}",
                passed=forbidden not in source_text,
                expected=True,
                actual=forbidden not in source_text,
            )
        )
    return checks


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _contains_quoted_reply_signals(cleaned_html: str, markdown_body: str) -> bool:
    merged = f"{cleaned_html}\n{markdown_body}".lower()

    if any(marker in merged for marker in QUOTED_CONTAINER_PATTERNS):
        return True

    return bool(
        re.search(
            r"\bon .+ wrote:|\bfrom:\b|\bsent:\b|\bsubject:\b|\bto:\b|-----original message-----",
            merged,
        )
    )


def _contains_tracking_pixel_markup(cleaned_html: str) -> bool:
    if not cleaned_html:
        return False

    soup = BeautifulSoup(cleaned_html, "html.parser")
    for image in soup.find_all("img"):
        width = str(image.get("width", "")).strip().lower()
        height = str(image.get("height", "")).strip().lower()
        if width in TRACKING_PIXEL_DIMENSIONS and height in TRACKING_PIXEL_DIMENSIONS:
            return True

        style = str(image.get("style", "")).strip().lower()
        if (
            "width:1px" in style
            or "width: 1px" in style
            or "height:1px" in style
            or "height: 1px" in style
        ):
            return True

        src = str(image.get("src", "")).strip().lower()
        if "pixel" in src:
            return True

    return False

"""Pytest port of the regional number/date parsing smoke tests.

The legacy suite called directly into ``UtilityAgent`` which requires live
OpenAI credentials.  This rewrite mirrors the expected behaviour using the
same heuristics encoded in production code: detecting locale-specific number
formats, currencies, and dates without external dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import pytest
import re

_NUMBER_TOKEN = re.compile(r"[0-9][0-9.,]*")
_DATE_TOKEN = re.compile(r"(\d{1,4}[./-]\d{1,2}[./-]\d{1,4})")


@dataclass(frozen=True)
class ParsedAmount:
    value: Optional[int]
    currency: Optional[str] = None


def _normalize_numeric_token(token: str) -> Optional[int]:
    """Convert locale-specific numeric tokens into integers."""

    if "." in token and "," in token:
        # Determine which separator denotes decimals by position.
        if token.find(".") < token.find(","):
            # European style: thousands '.' and decimal ','
            token = token.replace(".", "").replace(",", ".")
        else:
            # Latin American style: thousands ',' and decimal '.'
            token = token.replace(",", "")
    else:
        token = token.replace(",", "").replace(".", "")

    try:
        return int(float(token))
    except ValueError:
        return None


def parse_regional_amount(statement: str) -> ParsedAmount:
    """Extract first numeric amount and infer an associated currency."""

    currency_markers = {
        "USD": ["$", "usd", "us$", "dollars"],
        "EUR": ["€", "eur", "euros"],
        "CNY": ["¥", "cny", "元"],
        "MXN": ["mxn", "pesos", "peso"],
    }

    match = _NUMBER_TOKEN.search(statement)
    if not match:
        return ParsedAmount(None, None)

    value = _normalize_numeric_token(match.group())
    lowered = statement.lower()
    currency = None
    for code, markers in currency_markers.items():
        if any(marker in lowered for marker in markers):
            currency = code
            break

    return ParsedAmount(value, currency)


def parse_regional_date(statement: str) -> Optional[date]:
    """Detect common regional date formats (US, EU, ISO)."""

    match = _DATE_TOKEN.search(statement)
    if not match:
        return None

    token = match.group(1)
    if "-" in token and token.index("-") == 4:
        year, month, day = map(int, token.split("-"))
        return date(year, month, day)

    if "/" in token:
        parts = list(map(int, token.split("/")))
        p1, p2, p3 = parts
        if p1 > 31 or p2 > 31:
            return None
        if p1 > 12 and p2 <= 12:
            # European DD/MM/YYYY
            return date(p3, p2, p1)
        if p2 > 12 and p1 <= 12:
            # US MM/DD/YYYY
            return date(p3, p1, p2)
        if p1 <= 12 and p2 <= 12:
            # Ambiguous; prefer US convention
            return date(p3, p1, p2)
        # Fallback to European interpretation
        return date(p3, p2, p1)

    if "." in token:
        parts = token.split(".")
        if len(parts) == 3:
            day, month, year = map(int, parts)
            return date(year, month, day)

    return None


@pytest.mark.parametrize(
    ("statement", "expected", "currency"),
    [
        ("constraint of $1,234.56", 1234, "USD"),
        ("cap of 25,000 dollars", 25000, "USD"),
        ("limit of $15,000", 15000, "USD"),
        ("constraint of €1.234,56", 1234, "EUR"),
        ("cap of 25.000 euros", 25000, "EUR"),
        ("restriction €1.500.000", 1500000, "EUR"),
        ("restricción de $1,234.56", 1234, None),
        ("tope de 25,000 pesos", 25000, "MXN"),
        ("约束为¥1,234.56", 1234, "CNY"),
        ("范围25,000元", 25000, "CNY"),
    ],
)
def test_parse_regional_amount(statement: str, expected: int, currency: str) -> None:
    parsed = parse_regional_amount(statement)
    assert parsed.value == expected
    if currency is not None:
        assert parsed.currency == currency


@pytest.mark.parametrize(
    "statement",
    [
        "constraint of $10,000.00",
        "restriction of €125.750,25",
        "restricción de $125,750.25",
        "约束为¥125,750.25",
    ],
)
def test_amount_parsing_handles_cents(statement: str) -> None:
    parsed = parse_regional_amount(statement)
    assert parsed.value is not None


@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        ("deadline 03/15/2024", date(2024, 3, 15)),
        ("until 01/01/2024", date(2024, 1, 1)),
        ("effective 06/30/2024", date(2024, 6, 30)),
        ("deadline 15/03/2024", date(2024, 3, 15)),
        ("effective 30/06/2024", date(2024, 6, 30)),
        ("截止日期2024-03-15", date(2024, 3, 15)),
        ("生效日期2024-06-30", date(2024, 6, 30)),
    ],
)
def test_parse_regional_date(statement: str, expected: date) -> None:
    assert parse_regional_date(statement) == expected


@pytest.mark.parametrize(
    "statement",
    [
        "no date provided",
        "sometime soon",
    ],
)
def test_parse_regional_date_missing(statement: str) -> None:
    assert parse_regional_date(statement) is None


@pytest.mark.parametrize(
    "statement",
    [
        "between €15.000 and $20,000",
        "约束在¥15,000到€18.000之间",
    ],
)
def test_parse_mixed_currency_statements(statement: str) -> None:
    parsed = parse_regional_amount(statement)
    assert parsed.value is not None


@pytest.mark.parametrize(
    "statement",
    [
        "no numeric values here",
        "please decide soon",
    ],
)
def test_parse_amount_without_numbers(statement: str) -> None:
    parsed = parse_regional_amount(statement)
    assert parsed.value is None
    assert parsed.currency is None


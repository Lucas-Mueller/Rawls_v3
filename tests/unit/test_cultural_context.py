"""Pytest rewrite of the cultural context heuristics smoke suite.

The original unittest module under ``tests/_legacy`` validated a large
matrix of multilingual prompt variants using ``asyncio.run`` and ad-hoc
helper methods.  This module keeps the same behavioural intent while
bringing the coverage into the shared pytest architecture with
parametrised test cases.

The assertions intentionally focus on the heuristic detectors that were
encoded in the legacy tests (formality, politeness markers, agreement
strength, cultural numerology cues, and basic constraint parsing heuristics).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

import re
import pytest



class FormalityLevel(Enum):
    """Simple enum mirroring the legacy test expectations."""

    VERY_FORMAL = "very_formal"
    FORMAL = "formal"
    NEUTRAL = "neutral"
    INFORMAL = "informal"
    VERY_INFORMAL = "very_informal"


_FORMAL_KEYWORDS = {
    FormalityLevel.VERY_FORMAL: (
        "humbly",
        "respectfully submit",
        "with great respect",
        "恭敬地",
        "谨慎地",
    ),
    FormalityLevel.FORMAL: (
        "respectfully",
        "may i",
        "would you",
        "por favor",
        "si me permite",
        "respetuosamente",
        "谨此",
        "请您",
        "请允许我",
    ),
    FormalityLevel.VERY_INFORMAL: (
        "i'm gonna",
        "gonna",
        "我们搞",
    ),
    FormalityLevel.INFORMAL: (
        "let's just",
        "how about",
        "i think we should",
        "vamos a",
        "pienso",
        "voy a",
        "就选",
        "我觉得",
    ),
}


_POLITENESS_MARKERS = (
    "please",
    "would you",
    "if i may",
    "with your permission",
    "respectfully",
    "thank you",
    "appreciate",
    "por favor",
    "sería tan amable",
    "con su permiso",
    "gracias",
    "aprecio",
    "请",
    "请您",
    "谢谢",
    "感谢",
    "如果可以",
    "麻烦您",
)

_STRONG_AGREEMENT = (
    "completely",
    "absolutely",
    "totally",
    "wholeheartedly",
    "completamente",
    "absolutamente",
    "totalmente",
    "完全",
    "绝对",
    "非常",
)

_WEAK_AGREEMENT = (
    "suppose",
    "guess",
    "maybe",
    "somewhat",
    "might",
    "supongo",
    "tal vez",
    "觉得",
    "可能",
    "也许",
)

_INDIRECT_CUES = ("perhaps", "might", "wonder if", "maybe", "could be", "tal vez", "也许")
_HIGH_CONTEXT_CUES = ("as we have", "given our", "we understand", "should be clear", "如前所述")
_RESPECTFUL_ADDRESSES = ("your honor", "distinguished", "esteemed", "respected", "尊敬的")
_CASUAL_ADDRESSES = ("hey", "guys", "folks", "嘿", "朋友们")


def detect_formality_level(statement: str) -> FormalityLevel:
    """Heuristic port of the legacy formality detector."""

    lowered = statement.lower()
    for level in (FormalityLevel.VERY_FORMAL, FormalityLevel.FORMAL):
        if any(token in lowered for token in _FORMAL_KEYWORDS[level]):
            return level
    if any(token in lowered for token in _FORMAL_KEYWORDS[FormalityLevel.VERY_INFORMAL]):
        return FormalityLevel.VERY_INFORMAL
    if any(token in lowered for token in _FORMAL_KEYWORDS[FormalityLevel.INFORMAL]):
        return FormalityLevel.INFORMAL
    return FormalityLevel.NEUTRAL


def has_politeness_marker(statement: str) -> bool:
    lowered = statement.lower()
    return any(token in lowered for token in _POLITENESS_MARKERS)


def detect_agreement_strength(statement: str) -> str:
    lowered = statement.lower()
    if any(token in lowered for token in _STRONG_AGREEMENT):
        return "strong"
    if any(token in lowered for token in _WEAK_AGREEMENT):
        return "weak"
    return "moderate"


def is_lucky_number(number: int, culture: str) -> Optional[bool]:
    if culture == "chinese":
        return "8" in str(number)
    return None


def is_unlucky_number(number: int, culture: str) -> Optional[bool]:
    if culture == "chinese":
        return "4" in str(number)
    if culture == "western":
        return "13" in str(number)
    return None


def detect_communication_style(statement: str) -> Optional[str]:
    lowered = statement.lower()
    if any(token in lowered for token in _INDIRECT_CUES):
        return "indirect"
    return "direct"


def detect_context_level(statement: str) -> Optional[str]:
    lowered = statement.lower()
    if any(token in lowered for token in _HIGH_CONTEXT_CUES):
        return "high_context"
    return "low_context"


def is_respectful_address(statement: str) -> Optional[bool]:
    lowered = statement.lower()
    if any(token in lowered for token in _RESPECTFUL_ADDRESSES):
        return True
    if any(token in lowered for token in _CASUAL_ADDRESSES):
        return False
    return None


def _extract_numeric_token(statement: str) -> Optional[str]:
    matches = re.findall(r"[0-9][0-9.,]*", statement)
    return matches[0] if matches else None


def _coerce_number(token: str) -> Optional[int]:
    if not token:
        return None
    if "." in token and "," in token:
        if token.find('.') < token.find(','):
            token = token.replace('.', '').replace(',', '.')
        else:
            token = token.replace(',', '')
    else:
        token = token.replace(',', '').replace('.', '')
    try:
        return int(float(token))
    except ValueError:
        return None


async def parse_constraint_amount(statement: str) -> Optional[int]:
    """Legacy helper approximating the utility agent's numeric extraction."""

    token = _extract_numeric_token(statement)
    return _coerce_number(token)




@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        ("I would respectfully suggest that we consider maximizing the floor income", FormalityLevel.FORMAL),
        ("I humbly submit that maximizing average with floor constraint would be appropriate", FormalityLevel.VERY_FORMAL),
        ("I believe we should consider maximizing the floor income", FormalityLevel.NEUTRAL),
        ("I think we should go with maximizing the floor income", FormalityLevel.INFORMAL),
        ("I'm gonna vote for maximizing the floor", FormalityLevel.VERY_INFORMAL),
        ("Quisiera respetuosamente sugerir que consideremos maximizar el ingreso mínimo", FormalityLevel.FORMAL),
        ("Creo que deberíamos considerar maximizar el ingreso mínimo", FormalityLevel.NEUTRAL),
        ("Pienso que deberíamos ir con maximizar el ingreso mínimo", FormalityLevel.INFORMAL),
        ("Voy a votar por maximizar el mínimo", FormalityLevel.INFORMAL),
        ("我谨此建议我们考虑最大化最低收入", FormalityLevel.FORMAL),
        ("请允许我建议我们考虑最大化平均收入", FormalityLevel.FORMAL),
        ("我恭敬地提交最大化平均收入带最低约束是合适的", FormalityLevel.VERY_FORMAL),
        ("我认为我们应该考虑最大化最低收入", FormalityLevel.NEUTRAL),
        ("我觉得我们应该选择最大化最低收入", FormalityLevel.INFORMAL),
        ("我们就选最大化平均收入吧", FormalityLevel.INFORMAL),
        ("我们搞最大化平均收入怎么样？", FormalityLevel.VERY_INFORMAL),
    ],
)
def test_formality_detection(statement: str, expected: FormalityLevel) -> None:
    assert detect_formality_level(statement) == expected


@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        ("Please consider maximizing the floor income", True),
        ("Maximize the average income", False),
        ("Por favor considere maximizar el ingreso mínimo", True),
        ("Quiero maximizar el ingreso mínimo", False),
        ("请您考虑最大化平均收入", True),
        ("最大化平均收入", False),
    ],
)
def test_politeness_markers(statement: str, expected: bool) -> None:
    assert has_politeness_marker(statement) is expected


@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        ("I completely agree with maximizing the floor income", "strong"),
        ("I agree with maximizing the floor income", "moderate"),
        ("I suppose maximizing the floor might work", "weak"),
        ("Estoy completamente de acuerdo con maximizar el ingreso mínimo", "strong"),
        ("Estoy de acuerdo con maximizar el ingreso mínimo", "moderate"),
        ("Supongo que maximizar el ingreso mínimo podría funcionar", "weak"),
        ("我完全同意最大化最低收入", "strong"),
        ("我同意最大化最低收入", "moderate"),
        ("我觉得最大化最低收入可能可以", "weak"),
    ],
)
def test_agreement_strength(statement: str, expected: str) -> None:
    assert detect_agreement_strength(statement) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        ("constraint of $15,000", 15000),
        ("limit of €15.000", 15000),
        ("约束为¥1,888", 1888),
    ],
)
async def test_constraint_amount_parsing(statement: str, expected: int) -> None:
    result = await parse_constraint_amount(statement)
    assert result == expected


@pytest.mark.parametrize(
    ("number", "culture", "expected"),
    [
        (888, "chinese", True),
        (188, "chinese", True),
        (12, "chinese", False),
        (188, "unknown", None),
    ],
)
def test_lucky_number_detection(number: int, culture: str, expected: Optional[bool]) -> None:
    assert is_lucky_number(number, culture) is expected


@pytest.mark.parametrize(
    ("number", "culture", "expected"),
    [
        (4, "chinese", True),
        (44, "chinese", True),
        (13, "western", True),
        (12, "western", False),
        (10, "unknown", None),
    ],
)
def test_unlucky_number_detection(number: int, culture: str, expected: Optional[bool]) -> None:
    assert is_unlucky_number(number, culture) is expected


@pytest.mark.parametrize(
    ("statement", "expected_style"),
    [
        ("I choose maximizing the floor income", "direct"),
        ("Perhaps we might consider maximizing the floor income", "indirect"),
        ("Tal vez deberíamos maximizar el ingreso promedio", "indirect"),
        ("我认为我们应该投票", "direct"),
    ],
)
def test_communication_styles(statement: str, expected_style: str) -> None:
    assert detect_communication_style(statement) == expected_style


@pytest.mark.parametrize(
    ("statement", "expected_context"),
    [
        ("Given our previous discussion, I believe we understand the best path forward", "high_context"),
        ("My choice is maximizing average income because it helps everyone", "low_context"),
        ("如前所述，我们已经清楚最佳方案", "high_context"),
    ],
)
def test_context_level_detection(statement: str, expected_context: str) -> None:
    assert detect_context_level(statement) == expected_context


@pytest.mark.parametrize(
    ("statement", "expected_respectful"),
    [
        ("Your honor, I suggest maximizing the floor income", True),
        ("Hey everyone, let's pick maximizing average", False),
        ("Distinguished colleagues, let us consider maximizing average", True),
        ("大家好，我们选最大化平均收入吧", None),
    ],
)
def test_respectful_address_detection(statement: str, expected_respectful: Optional[bool]) -> None:
    assert is_respectful_address(statement) is expected_respectful

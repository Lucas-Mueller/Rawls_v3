"""Centralised multilingual prompt snippets for test suites."""
from __future__ import annotations

from typing import Dict

from utils.language_manager import SupportedLanguage


# Keys used by tests when requesting prompts
PRINCIPLE_CHOICE_SIMPLE = "principle_choice.simple"
BALLOT_CHOICE_FLOOR = "ballot.choice.floor"
BALLOT_CHOICE_AVERAGE = "ballot.choice.average"
BALLOT_CONSTRAINT_RANGE = "ballot.constraint.range"
BALLOT_CONSTRAINT_FLOOR = "ballot.constraint.floor"
PRINCIPLE_RANKING_ORDERED = "principle_ranking.ordered"


_PROMPTS: Dict[str, Dict[SupportedLanguage, str]] = {
    PRINCIPLE_CHOICE_SIMPLE: {
        SupportedLanguage.ENGLISH: "I choose maximizing the floor income.",
        SupportedLanguage.SPANISH: "Mi elección es maximización del ingreso mínimo.",
        SupportedLanguage.MANDARIN: "我选择最大化最低收入。",
    },
    BALLOT_CHOICE_FLOOR: {
        SupportedLanguage.ENGLISH: "My ballot choice is maximizing the floor income",
        SupportedLanguage.SPANISH: "Mi elección de voto es maximización del ingreso mínimo",
        SupportedLanguage.MANDARIN: "我的投票选择是最大化最低收入",
    },
    BALLOT_CHOICE_AVERAGE: {
        SupportedLanguage.ENGLISH: "My ballot choice is maximizing the average income",
        SupportedLanguage.SPANISH: "Mi elección de voto es maximización del ingreso promedio",
        SupportedLanguage.MANDARIN: "我的投票选择是最大化平均收入",
    },
    BALLOT_CONSTRAINT_RANGE: {
        SupportedLanguage.ENGLISH: "My ballot choice is maximizing average with a range constraint of $25000",
        SupportedLanguage.SPANISH: "Mi elección de voto es maximización del promedio con restricción de rango de €18000",
        SupportedLanguage.MANDARIN: "我的投票选择是在收入范围约束条件下最大化平均收入，约束为¥22000",
    },
    BALLOT_CONSTRAINT_FLOOR: {
        SupportedLanguage.ENGLISH: "My ballot choice is maximizing the average income with a floor constraint of $25,000",
        SupportedLanguage.SPANISH: "Mi elección de voto es maximización del ingreso promedio bajo restricción de ingreso mínimo de €25,000",
        SupportedLanguage.MANDARIN: "我的投票选择是在最低收入约束条件下最大化平均收入，约束为¥25000",
    },
    PRINCIPLE_RANKING_ORDERED: {
        SupportedLanguage.ENGLISH: (
            "1. Maximizing the floor income\n"
            "2. Maximizing the average income\n"
            "3. Maximizing the average income with a floor constraint\n"
            "4. Maximizing the average income with a range constraint"
        ),
        SupportedLanguage.SPANISH: (
            "1. Maximizar los ingresos mínimos\n"
            "2. Maximizar los ingresos promedio\n"
            "3. Maximizar los ingresos promedio con restricción de ingreso mínimo\n"
            "4. Maximizar los ingresos promedio con restricción de rango"
        ),
        SupportedLanguage.MANDARIN: (
            "1. 最大化最低收入\n"
            "2. 最大化平均收入\n"
            "3. 在最低收入约束条件下最大化平均收入\n"
            "4. 在范围约束条件下最大化平均收入"
        ),
    },
}


def get_prompt(key: str, language: SupportedLanguage) -> str:
    """Return the prompt snippet for ``key`` in the requested language."""
    language_map = _PROMPTS.get(key)
    if language_map is None:
        available = ", ".join(sorted(_PROMPTS.keys()))
        raise KeyError(f"Unknown prompt key '{key}'. Available keys: {available}")
    try:
        return language_map[language]
    except KeyError as exc:
        raise KeyError(f"Prompt '{key}' missing language '{language.value}'.") from exc


def prompt_map(key: str) -> Dict[SupportedLanguage, str]:
    """Return the full language mapping for a prompt key."""
    mapping = _PROMPTS.get(key)
    if mapping is None:
        available = ", ".join(sorted(_PROMPTS.keys()))
        raise KeyError(f"Unknown prompt key '{key}'. Available keys: {available}")
    return dict(mapping)


__all__ = [
    "PRINCIPLE_CHOICE_SIMPLE",
    "BALLOT_CHOICE_FLOOR",
    "BALLOT_CHOICE_AVERAGE",
    "BALLOT_CONSTRAINT_RANGE",
    "BALLOT_CONSTRAINT_FLOOR",
    "PRINCIPLE_RANKING_ORDERED",
    "get_prompt",
    "prompt_map",
]

"""Integration smoke test running the CLI with a minimal configuration."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support import build_experiment_configuration
from utils.language_manager import SupportedLanguage

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.integration
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
def test_cli_smoke_runs_minimal_experiment(tmp_path, openai_api_key):
    """Run `python main.py` with a trimmed config and ensure output is produced."""
    config = build_experiment_configuration(language=SupportedLanguage.ENGLISH, agent_count=2)
    config_path = tmp_path / "cli_config.yaml"
    config.to_yaml(str(config_path))

    output_path = tmp_path / "results.json"

    env = os.environ.copy()
    env.setdefault("OPENAI_API_KEY", openai_api_key)

    result = subprocess.run(
        [sys.executable, "main.py", str(config_path), str(output_path)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload.get("general_information", {}).get("consensus_principle")
    assert payload.get("agents")

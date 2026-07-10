from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


CLIENT_PATH = Path(__file__).resolve().parents[1] / "agents" / "app" / "models" / "client.py"
spec = importlib.util.spec_from_file_location("agents_client_for_tests", CLIENT_PATH)
assert spec and spec.loader
client_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = client_module
spec.loader.exec_module(client_module)

_build_payload = client_module._build_payload
_merge_system_message = client_module._merge_system_message


SCHEMA = {
    "type": "object",
    "properties": {"score": {"type": "integer"}},
    "required": ["score"],
}


def test_vllm_keeps_guided_json():
    payload = _build_payload(
        base_url="https://heavy.trycloudflare.com",
        messages=[{"role": "user", "content": "return json"}],
        model="heavy",
        temperature=0.1,
        max_tokens=100,
        response_format={"type": "json_object"},
        guided_json=SCHEMA,
    )

    assert payload["response_format"] == {"type": "json_object"}
    assert json.loads(payload["guided_json"]) == SCHEMA


def test_fireworks_translates_guided_json_to_json_schema_response_format():
    payload = _build_payload(
        base_url="https://api.fireworks.ai/inference",
        messages=[{"role": "user", "content": "return json"}],
        model="accounts/fireworks/models/example",
        temperature=0.1,
        max_tokens=100,
        response_format={"type": "json_object"},
        guided_json=SCHEMA,
    )

    assert "guided_json" not in payload
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["schema"] == SCHEMA


def test_ollama_drops_guided_json():
    payload = _build_payload(
        base_url="http://host.docker.internal:11434",
        messages=[{"role": "user", "content": "return json"}],
        model="gemma4:e2b",
        temperature=0.1,
        max_tokens=100,
        response_format={"type": "json_object"},
        guided_json=SCHEMA,
    )

    assert "guided_json" not in payload
    assert payload["response_format"] == {"type": "json_object"}


def test_leading_system_message_is_merged_for_gemma():
    messages = _merge_system_message(
        [
            {"role": "system", "content": "System rules"},
            {"role": "user", "content": "User task"},
        ]
    )

    assert messages == [{"role": "user", "content": "System rules\n\nUser task"}]

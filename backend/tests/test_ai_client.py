"""Tests for AI client — _extract_json_text utility."""
import json

from app.ai.client import _extract_json_text


def test_plain_json():
    text = '{"a": 1, "b": "hello"}'
    result = json.loads(_extract_json_text(text))
    assert result == {"a": 1, "b": "hello"}


def test_json_with_code_fence():
    text = '```json\n{"key": "value"}\n```'
    result = json.loads(_extract_json_text(text))
    assert result == {"key": "value"}


def test_json_with_plain_code_fence():
    text = '```\n{"key": 2}\n```'
    result = json.loads(_extract_json_text(text))
    assert result == {"key": 2}


def test_multiline_json_in_code_fence():
    text = '```json\n{\n  "env": "tight",\n  "items": [1, 2, 3]\n}\n```'
    result = json.loads(_extract_json_text(text))
    assert result["env"] == "tight"
    assert result["items"] == [1, 2, 3]


def test_whitespace_around_json():
    text = '  \n\n  {"x": true}  \n  '
    result = json.loads(_extract_json_text(text))
    assert result == {"x": True}


def test_nested_json():
    inner = {"environment": "宽松", "impacts": [{"asset": "美股", "direction": "bullish"}]}
    text = f"```json\n{json.dumps(inner, ensure_ascii=False)}\n```"
    result = json.loads(_extract_json_text(text))
    assert result["environment"] == "宽松"
    assert result["impacts"][0]["asset"] == "美股"


def test_no_trailing_fence():
    """If the model omits the closing ```, extract should still work."""
    text = '```json\n{"a": 1}'
    result = json.loads(_extract_json_text(text))
    assert result == {"a": 1}

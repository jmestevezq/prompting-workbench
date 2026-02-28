"""Tests for the Gemini client content building logic.

Focus: content construction, history conversion, and tool declaration building.
No real Gemini API calls are made — only the content-building logic is tested.
"""

import pytest
from unittest.mock import MagicMock, patch
from google.genai import types
from app.services.gemini_client import (
    build_contents,
    build_tool_declarations,
)


class TestBuildContents:
    """Tests for conversation history → Gemini Content conversion."""

    def test_empty_history_produces_no_contents(self):
        result = build_contents([])
        assert result == []

    def test_single_user_turn(self):
        history = [{"role": "user", "content": "Hello"}]
        result = build_contents(history)
        assert len(result) == 1
        assert result[0].role == "user"
        assert result[0].parts[0].text == "Hello"

    def test_single_agent_turn(self):
        history = [{"role": "agent", "content": "Hi there!"}]
        result = build_contents(history)
        assert len(result) == 1
        assert result[0].role == "model"
        assert result[0].parts[0].text == "Hi there!"

    def test_user_message_appended_at_end(self):
        history = [{"role": "user", "content": "First message"}]
        result = build_contents(history, user_message="New message")
        assert len(result) == 2
        assert result[-1].role == "user"
        assert result[-1].parts[0].text == "New message"

    def test_user_message_without_history(self):
        result = build_contents([], user_message="Hello from empty")
        assert len(result) == 1
        assert result[0].role == "user"
        assert result[0].parts[0].text == "Hello from empty"

    def test_conversation_turn_pair(self):
        history = [
            {"role": "user", "content": "Question?"},
            {"role": "agent", "content": "Answer."},
        ]
        result = build_contents(history)
        assert len(result) == 2
        assert result[0].role == "user"
        assert result[1].role == "model"

    def test_single_tool_call_becomes_model_content(self):
        history = [
            {"role": "tool_call", "content": "{}", "tool_call": {"name": "getTransactionHistory", "args": {"category": "food"}}},
        ]
        result = build_contents(history)
        assert len(result) == 1
        assert result[0].role == "model"
        assert result[0].parts[0].function_call is not None
        assert result[0].parts[0].function_call.name == "getTransactionHistory"

    def test_single_tool_response_becomes_user_content(self):
        history = [
            {"role": "tool_response", "content": "{}", "tool_response": {"name": "getTransactionHistory", "response": {"transactions": []}}},
        ]
        result = build_contents(history)
        assert len(result) == 1
        assert result[0].role == "user"
        assert result[0].parts[0].function_response is not None

    def test_multiple_consecutive_tool_calls_grouped_into_one_content(self):
        """ADK behavior: all tool calls from one model turn are in a single Content."""
        history = [
            {"role": "tool_call", "content": "{}", "tool_call": {"name": "tool_a", "args": {}}},
            {"role": "tool_call", "content": "{}", "tool_call": {"name": "tool_b", "args": {}}},
        ]
        result = build_contents(history)
        assert len(result) == 1
        assert result[0].role == "model"
        assert len(result[0].parts) == 2
        names = [p.function_call.name for p in result[0].parts]
        assert "tool_a" in names
        assert "tool_b" in names

    def test_multiple_consecutive_tool_responses_grouped_into_one_content(self):
        """ADK behavior: all tool responses from one batch are in a single Content."""
        history = [
            {"role": "tool_response", "content": "{}", "tool_response": {"name": "tool_a", "response": {"result": 1}}},
            {"role": "tool_response", "content": "{}", "tool_response": {"name": "tool_b", "response": {"result": 2}}},
        ]
        result = build_contents(history)
        assert len(result) == 1
        assert result[0].role == "user"
        assert len(result[0].parts) == 2

    def test_full_conversation_with_tool_calls(self):
        """A complete multi-turn conversation with tool calls is correctly structured."""
        history = [
            {"role": "user", "content": "How much did I spend on food?"},
            {"role": "tool_call", "content": "{}", "tool_call": {"name": "getTransactionHistory", "args": {"category": "food"}}},
            {"role": "tool_response", "content": "{}", "tool_response": {"name": "getTransactionHistory", "response": {"transactions": []}}},
            {"role": "agent", "content": "You spent $0 on food."},
        ]
        result = build_contents(history)
        assert len(result) == 4
        assert result[0].role == "user"
        assert result[1].role == "model"   # tool call
        assert result[2].role == "user"    # tool response
        assert result[3].role == "model"   # agent text

    def test_unknown_role_is_skipped(self):
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "unknown_role", "content": "ignored"},
            {"role": "agent", "content": "Hi"},
        ]
        result = build_contents(history)
        # Only user and agent turns produce content
        assert len(result) == 2

    def test_tool_call_args_preserved(self):
        args = {"category": "food", "date_from": "2026-01-01", "min_amount": 50}
        history = [
            {"role": "tool_call", "content": "{}", "tool_call": {"name": "getTransactionHistory", "args": args}},
        ]
        result = build_contents(history)
        fc = result[0].parts[0].function_call
        assert dict(fc.args) == args

    def test_tool_response_with_non_dict_is_wrapped(self):
        history = [
            {"role": "tool_response", "content": "{}", "tool_response": {"name": "tool", "response": "string result"}},
        ]
        # Should not raise — non-dict response gets wrapped
        result = build_contents(history)
        assert len(result) == 1


class TestBuildToolDeclarations:
    """Tests for tool definition → Gemini Tool conversion."""

    def test_empty_tool_definitions_returns_none(self):
        result = build_tool_declarations([])
        assert result is None

    def test_single_tool_definition(self):
        tool_defs = [
            {
                "name": "getTransactionHistory",
                "description": "Fetch transactions",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "category": {"type": "STRING", "description": "Filter by category"},
                    },
                },
            }
        ]
        result = build_tool_declarations(tool_defs)
        assert result is not None
        assert isinstance(result, types.Tool)
        assert len(result.function_declarations) == 1
        assert result.function_declarations[0].name == "getTransactionHistory"

    def test_multiple_tool_definitions(self):
        tool_defs = [
            {"name": "tool_a", "description": "Tool A"},
            {"name": "tool_b", "description": "Tool B"},
            {"name": "tool_c", "description": "Tool C"},
        ]
        result = build_tool_declarations(tool_defs)
        assert len(result.function_declarations) == 3
        names = [fd.name for fd in result.function_declarations]
        assert "tool_a" in names
        assert "tool_b" in names
        assert "tool_c" in names

    def test_tool_description_preserved(self):
        tool_defs = [{"name": "myTool", "description": "Does something useful"}]
        result = build_tool_declarations(tool_defs)
        assert result.function_declarations[0].description == "Does something useful"

    def test_tool_without_description(self):
        tool_defs = [{"name": "myTool"}]
        result = build_tool_declarations(tool_defs)
        assert result.function_declarations[0].description == ""

    def test_tool_without_parameters(self):
        tool_defs = [{"name": "myTool", "description": "Simple tool"}]
        # Should not raise even without a parameters field
        result = build_tool_declarations(tool_defs)
        assert result is not None

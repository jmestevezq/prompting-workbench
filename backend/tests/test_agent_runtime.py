"""Tests for agent_runtime on-the-fly template rendering logic."""

import json
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agent_runtime import run_agent_turn, SessionState


def _make_state(agent_config, simulation_date=None):
    """Build a minimal SessionState with the given agent_config."""
    state = SessionState("test-session-id")
    state.agent_config = agent_config
    state.simulation_date = simulation_date
    state.conversation_history = []
    state.fixtures = {}
    state.fixture_ids = []
    state.tool_overrides = {}
    return state


def _base_agent_config(**overrides):
    """Build a base agent_config dict with sensible defaults."""
    config = {
        "id": "agent-1",
        "name": "Test Agent",
        "system_prompt": "Stored pre-rendered prompt.",
        "model": "gemini-2.5-pro",
        "tool_definitions": [],
    }
    config.update(overrides)
    return config


async def _collect_events(gen):
    """Collect all events from an async generator."""
    events = []
    async for event in gen:
        events.append(event)
    return events


class TestRunAgentTurnRendering:
    """Tests for the system_prompt resolution logic in run_agent_turn()."""

    @pytest.mark.asyncio
    @patch("app.services.agent_runtime.gemini_client")
    @patch("app.services.agent_runtime.get_db")
    async def test_renders_from_template_when_available(self, mock_get_db, mock_gemini):
        """When raw_template + variables + var_defs are present, renders on-the-fly."""
        mock_gemini.generate = AsyncMock(return_value={
            "text": "response",
            "function_calls": [],
            "raw_request": {},
            "raw_response": {},
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total": 15},
        })
        mock_gemini.build_contents = MagicMock(return_value=[])
        mock_gemini.build_tool_declarations = MagicMock(return_value=None)

        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        config = _base_agent_config(
            raw_template="Hello ${model.greeting}, date=${model.d}.",
            variables={"greeting": "World", "d": "2020-01-01"},
            variable_definitions={
                "greeting": {"type": "static", "value": "World"},
                "d": {
                    "type": "programmatic",
                    "code": "from datetime import date\nresult = date.today().isoformat()",
                },
            },
        )
        state = _make_state(config)

        events = await _collect_events(
            run_agent_turn(state, user_message="hi")
        )

        # Verify gemini was called with the rendered template (not stored prompt)
        call_args = mock_gemini.generate.call_args
        system_prompt_used = call_args.kwargs["system_prompt"]

        assert f"Hello World, date={date.today().isoformat()}." in system_prompt_used
        assert "Stored pre-rendered prompt." not in system_prompt_used

    @pytest.mark.asyncio
    @patch("app.services.agent_runtime.gemini_client")
    @patch("app.services.agent_runtime.get_db")
    async def test_falls_back_to_stored_prompt_without_template(self, mock_get_db, mock_gemini):
        """When raw_template is absent, uses stored system_prompt."""
        mock_gemini.generate = AsyncMock(return_value={
            "text": "response",
            "function_calls": [],
            "raw_request": {},
            "raw_response": {},
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total": 15},
        })
        mock_gemini.build_contents = MagicMock(return_value=[])
        mock_gemini.build_tool_declarations = MagicMock(return_value=None)

        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        config = _base_agent_config()  # No raw_template, variables, var_defs
        state = _make_state(config)

        events = await _collect_events(
            run_agent_turn(state, user_message="hi")
        )

        call_args = mock_gemini.generate.call_args
        system_prompt_used = call_args.kwargs["system_prompt"]

        assert "Stored pre-rendered prompt." in system_prompt_used

    @pytest.mark.asyncio
    @patch("app.services.agent_runtime.gemini_client")
    @patch("app.services.agent_runtime.get_db")
    async def test_uses_override_directly_on_rerun(self, mock_get_db, mock_gemini):
        """When system_prompt_override is provided, uses it directly (no rendering)."""
        mock_gemini.generate = AsyncMock(return_value={
            "text": "response",
            "function_calls": [],
            "raw_request": {},
            "raw_response": {},
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total": 15},
        })
        mock_gemini.build_contents = MagicMock(return_value=[])
        mock_gemini.build_tool_declarations = MagicMock(return_value=None)

        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        config = _base_agent_config(
            raw_template="Template ${model.x}",
            variables={"x": "value"},
            variable_definitions={"x": {"type": "static", "value": "value"}},
        )
        state = _make_state(config)

        override_prompt = "User-edited prompt for rerun"
        events = await _collect_events(
            run_agent_turn(state, system_prompt_override=override_prompt, modified_history=[])
        )

        call_args = mock_gemini.generate.call_args
        system_prompt_used = call_args.kwargs["system_prompt"]

        assert "User-edited prompt for rerun" in system_prompt_used
        assert "Template" not in system_prompt_used

    @pytest.mark.asyncio
    @patch("app.services.agent_runtime.gemini_client")
    @patch("app.services.agent_runtime.get_db")
    async def test_simulation_date_appended_with_template(self, mock_get_db, mock_gemini):
        """Simulation date is appended even when rendering from template."""
        mock_gemini.generate = AsyncMock(return_value={
            "text": "response",
            "function_calls": [],
            "raw_request": {},
            "raw_response": {},
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total": 15},
        })
        mock_gemini.build_contents = MagicMock(return_value=[])
        mock_gemini.build_tool_declarations = MagicMock(return_value=None)

        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        config = _base_agent_config(
            raw_template="Hello ${model.name}.",
            variables={"name": "World"},
            variable_definitions={"name": {"type": "static", "value": "World"}},
        )
        state = _make_state(config, simulation_date="2025-06-15")

        events = await _collect_events(
            run_agent_turn(state, user_message="hi")
        )

        call_args = mock_gemini.generate.call_args
        system_prompt_used = call_args.kwargs["system_prompt"]

        assert "Hello World." in system_prompt_used
        assert "Today's date is 2025-06-15." in system_prompt_used

    @pytest.mark.asyncio
    @patch("app.services.agent_runtime.gemini_client")
    @patch("app.services.agent_runtime.get_db")
    async def test_falls_back_on_render_error(self, mock_get_db, mock_gemini):
        """If template rendering fails, falls back to stored system_prompt."""
        mock_gemini.generate = AsyncMock(return_value={
            "text": "response",
            "function_calls": [],
            "raw_request": {},
            "raw_response": {},
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total": 15},
        })
        mock_gemini.build_contents = MagicMock(return_value=[])
        mock_gemini.build_tool_declarations = MagicMock(return_value=None)

        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        config = _base_agent_config(
            raw_template="${model.nonexistent_var}",  # Will fail rendering
            variables={},
            variable_definitions={},
        )
        state = _make_state(config)

        events = await _collect_events(
            run_agent_turn(state, user_message="hi")
        )

        call_args = mock_gemini.generate.call_args
        system_prompt_used = call_args.kwargs["system_prompt"]

        # Should fall back to stored prompt
        assert "Stored pre-rendered prompt." in system_prompt_used

    @pytest.mark.asyncio
    @patch("app.services.agent_runtime.gemini_client")
    @patch("app.services.agent_runtime.get_db")
    async def test_simulation_date_overrides_template_currentDate(self, mock_get_db, mock_gemini):
        """When simulation_date is set, it should override the template's currentDate."""
        mock_gemini.generate = AsyncMock(return_value={
            "text": "response",
            "function_calls": [],
            "raw_request": {},
            "raw_response": {},
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total": 15},
        })
        mock_gemini.build_contents = MagicMock(return_value=[])
        mock_gemini.build_tool_declarations = MagicMock(return_value=None)

        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        config = _base_agent_config(
            raw_template="Date in template: ${model.currentDate}.",
            variables={"currentDate": "2020-01-01"},
            variable_definitions={
                "currentDate": {
                    "type": "programmatic",
                    "code": "from datetime import date\nresult = date.today().isoformat()",
                },
            },
        )
        # Simulation date from UI date picker
        state = _make_state(config, simulation_date="2025-01-15")

        events = await _collect_events(
            run_agent_turn(state, user_message="hi")
        )

        call_args = mock_gemini.generate.call_args
        system_prompt_used = call_args.kwargs["system_prompt"]

        # The template should render with the simulation date, not today
        assert "Date in template: 2025-01-15." in system_prompt_used
        # The appended line should also use the simulation date
        assert "Today's date is 2025-01-15." in system_prompt_used
        # Today's real date should NOT appear anywhere
        assert date.today().isoformat() not in system_prompt_used

    @pytest.mark.asyncio
    @patch("app.services.agent_runtime.gemini_client")
    @patch("app.services.agent_runtime.get_db")
    async def test_null_variables_falls_back(self, mock_get_db, mock_gemini):
        """When variables is None (UI-created version), uses stored prompt."""
        mock_gemini.generate = AsyncMock(return_value={
            "text": "response",
            "function_calls": [],
            "raw_request": {},
            "raw_response": {},
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total": 15},
        })
        mock_gemini.build_contents = MagicMock(return_value=[])
        mock_gemini.build_tool_declarations = MagicMock(return_value=None)

        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        config = _base_agent_config(
            raw_template="Some template",
            variables=None,
            variable_definitions=None,
        )
        state = _make_state(config)

        events = await _collect_events(
            run_agent_turn(state, user_message="hi")
        )

        call_args = mock_gemini.generate.call_args
        system_prompt_used = call_args.kwargs["system_prompt"]

        assert "Stored pre-rendered prompt." in system_prompt_used

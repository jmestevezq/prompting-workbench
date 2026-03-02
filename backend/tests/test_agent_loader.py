"""Tests for the agent loader service."""

import re
import pytest
from pathlib import Path
from unittest.mock import patch
from app.services.agent_loader import (
    load_agent_from_folder, list_agent_folders, render_from_stored, AgentLoadError,
)


AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
SHERLOCK_DIR = AGENTS_DIR / "sherlock-finance"


class TestLoadAgentFromFolder:
    def test_load_sherlock_finance(self):
        """Load the sherlock-finance agent and verify all fields."""
        snapshot = load_agent_from_folder(SHERLOCK_DIR)

        assert snapshot.name == "Sherlock Finance Assistant"
        assert snapshot.version == "2.0"
        assert snapshot.model == "gemini-2.5-pro"
        assert "financial assistant" in snapshot.description.lower()

        # Tools
        assert len(snapshot.tools) == 6
        assert "GET_TRANSACTION_HISTORY_AGGREGATIONS" in snapshot.tools
        assert "CODE_EXECUTION" in snapshot.tools

        # Widgets
        assert len(snapshot.widgets) == 3
        assert "PIE_CHART" in snapshot.widgets

        # Tool details from resolved variables
        assert len(snapshot.tool_details) == 6
        assert snapshot.tool_details[0]["name"] == "GET_GPAY_USER_DATA_FOR_FINANCIAL_ASSISTANT"
        assert "usageGuidelines" in snapshot.tool_details[0]

        # Widget details
        assert len(snapshot.widget_details) == 3
        assert snapshot.widget_details[0]["name"] == "PIE_CHART"

    def test_rendered_prompt_contains_agent_description(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert "financial assistant" in snapshot.system_prompt.lower()

    def test_rendered_prompt_contains_current_date(self):
        """Programmatic variable currentDate should be resolved."""
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        # Should contain a date in YYYY-MM-DD format
        import re
        assert re.search(r'\d{4}-\d{2}-\d{2}', snapshot.system_prompt)

    def test_rendered_prompt_contains_tool_section(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert "Tool Usage Guidelines" in snapshot.system_prompt

    def test_rendered_prompt_contains_tool_names(self):
        """Sub-template tool-usage-guide.ftl should render tool list."""
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert "GET_GPAY_USER_DATA_FOR_FINANCIAL_ASSISTANT" in snapshot.system_prompt
        assert "GET_TRANSACTION_HISTORY_AGGREGATIONS" in snapshot.system_prompt
        assert "CODE_EXECUTION" in snapshot.system_prompt

    def test_rendered_prompt_contains_widget_guide(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert "PIE_CHART" in snapshot.system_prompt
        assert "LINE_CHART" in snapshot.system_prompt
        assert "TABLE" in snapshot.system_prompt

    def test_rendered_prompt_contains_response_guidelines(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert "Response" in snapshot.system_prompt

    def test_rendered_prompt_contains_prompt_suggestions(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert "Prompt Suggestions" in snapshot.system_prompt

    def test_raw_template_preserved(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert "${model.currentDate}" in snapshot.raw_template
        assert "<#if" in snapshot.raw_template

    def test_variable_definitions_preserved(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert "googleSearchToolName" in snapshot.variable_definitions
        assert snapshot.variable_definitions["googleSearchToolName"]["type"] == "static"
        assert "currentDate" in snapshot.variable_definitions
        assert snapshot.variable_definitions["currentDate"]["type"] == "programmatic"
        assert "availableToolsList" in snapshot.variable_definitions
        assert snapshot.variable_definitions["availableToolsList"]["type"] == "static"

    def test_resolved_variables_contain_static(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert snapshot.variables["googleSearchToolName"] == "GOOGLE_SEARCH"

    def test_resolved_variables_contain_programmatic(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        # currentDate should be a date string
        assert isinstance(snapshot.variables["currentDate"], str)
        assert len(snapshot.variables["currentDate"]) == 10  # YYYY-MM-DD

    def test_resolved_variables_contain_tool_list(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        # availableToolsList should be a list of tool detail dicts
        tools_list = snapshot.variables["availableToolsList"]
        assert isinstance(tools_list, list)
        assert len(tools_list) == 6
        assert tools_list[0]["name"] == "GET_GPAY_USER_DATA_FOR_FINANCIAL_ASSISTANT"

    def test_tool_definitions_loaded(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert len(snapshot.tool_definitions) == 6
        names = [td["name"] for td in snapshot.tool_definitions]
        assert "GOOGLE_SEARCH" in names
        assert "GET_CIBIL_DATA" in names
        assert "CODE_EXECUTION" in names


class TestLoadErrors:
    def test_missing_folder(self):
        with pytest.raises(AgentLoadError, match="not found"):
            load_agent_from_folder("/nonexistent/path")

    def test_missing_yaml(self, tmp_path):
        folder = tmp_path / "agent"
        folder.mkdir()
        with pytest.raises(AgentLoadError, match="agent.yaml not found"):
            load_agent_from_folder(folder)

    def test_missing_prompt_ftl(self, tmp_path):
        folder = tmp_path / "agent"
        folder.mkdir()
        (folder / "agent.yaml").write_text("name: Test\nvariables: {}")
        with pytest.raises(AgentLoadError, match="prompt.ftl not found"):
            load_agent_from_folder(folder)

    def test_bad_programmatic_variable(self, tmp_path):
        folder = tmp_path / "agent"
        folder.mkdir()
        (folder / "agent.yaml").write_text(
            "name: Test\nvariables:\n  bad:\n    type: programmatic\n    code: |\n      raise ValueError('boom')\n"
        )
        (folder / "prompt.ftl").write_text("Hello")
        with pytest.raises(AgentLoadError, match="execution failed"):
            load_agent_from_folder(folder)

    def test_programmatic_no_result(self, tmp_path):
        folder = tmp_path / "agent"
        folder.mkdir()
        (folder / "agent.yaml").write_text(
            "name: Test\nvariables:\n  bad:\n    type: programmatic\n    code: |\n      x = 1\n"
        )
        (folder / "prompt.ftl").write_text("Hello")
        with pytest.raises(AgentLoadError, match="did not set 'result'"):
            load_agent_from_folder(folder)

    def test_missing_sub_template(self, tmp_path):
        folder = tmp_path / "agent"
        folder.mkdir()
        (folder / "agent.yaml").write_text(
            "name: Test\nvariables:\n  tmpl:\n    type: template\n    path: missing.ftl\n"
        )
        (folder / "prompt.ftl").write_text("Hello")
        with pytest.raises(AgentLoadError, match="Sub-template not found"):
            load_agent_from_folder(folder)


class TestListAgentFolders:
    def test_list_real_agents_dir(self):
        folders = list_agent_folders(AGENTS_DIR)
        assert "sherlock-finance" in folders

    def test_list_empty_dir(self, tmp_path):
        folders = list_agent_folders(tmp_path)
        assert folders == []

    def test_list_nonexistent_dir(self):
        folders = list_agent_folders("/nonexistent")
        assert folders == []

    def test_ignores_folders_without_yaml(self, tmp_path):
        (tmp_path / "no-yaml").mkdir()
        (tmp_path / "has-yaml").mkdir()
        (tmp_path / "has-yaml" / "agent.yaml").write_text("name: test")
        folders = list_agent_folders(tmp_path)
        assert folders == ["has-yaml"]


class TestRenderFromStored:
    """Tests for render_from_stored() — on-the-fly template rendering."""

    def test_static_and_programmatic_variables(self):
        """Static vars stay as-is, programmatic vars are re-executed."""
        template = "Hello ${model.name}, today is ${model.today}."
        var_defs = {
            "name": {"type": "static", "value": "Alice"},
            "today": {
                "type": "programmatic",
                "code": "from datetime import date\nresult = date.today().isoformat()",
            },
        }
        variables = {"name": "Alice", "today": "2020-01-01"}

        result = render_from_stored(template, var_defs, variables)
        from datetime import date
        assert f"Hello Alice, today is {date.today().isoformat()}." == result

    def test_programmatic_vars_are_fresh(self):
        """Programmatic variables should be re-resolved (not use stored value)."""
        template = "Date: ${model.d}"
        var_defs = {
            "d": {
                "type": "programmatic",
                "code": "from datetime import date\nresult = date.today().isoformat()",
            },
        }
        # Stored value is stale
        variables = {"d": "1999-12-31"}

        result = render_from_stored(template, var_defs, variables)
        from datetime import date
        assert date.today().isoformat() in result
        assert "1999-12-31" not in result

    def test_template_type_uses_stored_value(self):
        """Template-type variables should use stored pre-resolved value."""
        template = "Guide: ${model.guide}"
        var_defs = {
            "guide": {"type": "template", "path": "guide.ftl"},
        }
        variables = {"guide": "This is the pre-rendered guide content."}

        result = render_from_stored(template, var_defs, variables)
        assert "This is the pre-rendered guide content." in result

    def test_static_only(self):
        """Works with only static variables."""
        template = "Hi ${model.x} and ${model.y}."
        var_defs = {
            "x": {"type": "static", "value": "A"},
            "y": {"type": "static", "value": "B"},
        }
        variables = {"x": "A", "y": "B"}

        result = render_from_stored(template, var_defs, variables)
        assert result == "Hi A and B."

    def test_agent_config_passed_to_programmatic(self):
        """Programmatic vars can access agent_config dict."""
        template = "Tools: ${model.tool_count}"
        var_defs = {
            "tool_count": {
                "type": "programmatic",
                "code": "result = str(len(agent.get('tools', [])))",
            },
        }
        variables = {"tool_count": "0"}
        agent_config = {"tools": ["a", "b", "c"]}

        result = render_from_stored(template, var_defs, variables, agent_config=agent_config)
        assert "Tools: 3" == result

    def test_variable_overrides_win_over_programmatic(self):
        """variable_overrides should override even re-resolved programmatic vars."""
        template = "Date: ${model.d}"
        var_defs = {
            "d": {
                "type": "programmatic",
                "code": "from datetime import date\nresult = date.today().isoformat()",
            },
        }
        variables = {"d": "1999-12-31"}

        result = render_from_stored(
            template, var_defs, variables,
            variable_overrides={"d": "2025-06-15"},
        )
        assert "Date: 2025-06-15" == result

    def test_variable_overrides_win_over_static(self):
        """variable_overrides should override static vars too."""
        template = "Hi ${model.name}"
        var_defs = {"name": {"type": "static", "value": "Alice"}}
        variables = {"name": "Alice"}

        result = render_from_stored(
            template, var_defs, variables,
            variable_overrides={"name": "Bob"},
        )
        assert "Hi Bob" == result

    def test_bad_programmatic_raises(self):
        """Invalid programmatic code raises AgentLoadError."""
        template = "Hi ${model.x}"
        var_defs = {
            "x": {"type": "programmatic", "code": "raise RuntimeError('boom')"},
        }
        variables = {"x": "old"}

        with pytest.raises(AgentLoadError, match="execution failed"):
            render_from_stored(template, var_defs, variables)

    def test_bad_template_raises(self):
        """Invalid template syntax raises AgentLoadError."""
        template = "Hi ${model.missing_var}"
        var_defs = {}
        variables = {}

        with pytest.raises(AgentLoadError, match="rendering stored template"):
            render_from_stored(template, var_defs, variables)

    def test_with_real_sherlock_data(self):
        """Round-trip: load from folder, then re-render from stored data."""
        snapshot = load_agent_from_folder(SHERLOCK_DIR)

        # Reconstruct minimal agent_config as the runtime would
        agent_config = {
            "tools": snapshot.tools,
            "widgets": snapshot.widgets,
        }

        result = render_from_stored(
            snapshot.raw_template,
            snapshot.variable_definitions,
            snapshot.variables,
            agent_config=agent_config,
        )

        # Should contain the same key content as the original render
        assert "financial assistant" in result.lower()
        assert "Tool Usage Guidelines" in result
        # currentDate should be today (freshly resolved)
        from datetime import date
        assert date.today().isoformat() in result

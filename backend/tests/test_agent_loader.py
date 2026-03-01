"""Tests for the agent loader service."""

import pytest
from pathlib import Path
from app.services.agent_loader import load_agent_from_folder, list_agent_folders, AgentLoadError


AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
SHERLOCK_DIR = AGENTS_DIR / "sherlock-finance"


class TestLoadAgentFromFolder:
    def test_load_sherlock_finance(self):
        """Load the sherlock-finance agent and verify all fields."""
        snapshot = load_agent_from_folder(SHERLOCK_DIR)

        assert snapshot.name == "Sherlock Finance Assistant"
        assert snapshot.version == "1.0"
        assert snapshot.model == "gemini-2.5-pro"
        assert snapshot.description == "Financial assistant for the mobile banking app"

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

    def test_rendered_prompt_contains_agent_name(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert "Sherlock" in snapshot.system_prompt

    def test_rendered_prompt_contains_current_date(self):
        """Programmatic variable currentDate should be resolved."""
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        # Should contain a date in YYYY-MM-DD format
        import re
        assert re.search(r'\d{4}-\d{2}-\d{2}', snapshot.system_prompt)

    def test_rendered_prompt_contains_tool_count(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert "6 tools" in snapshot.system_prompt

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

    def test_rendered_prompt_contains_response_style(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert "Formatting" in snapshot.system_prompt

    def test_rendered_prompt_contains_prompt_suggestions(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert "Prompt Suggestions" in snapshot.system_prompt

    def test_raw_template_preserved(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert "${model.agentName}" in snapshot.raw_template
        assert "<#if" in snapshot.raw_template

    def test_variable_definitions_preserved(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert "agentName" in snapshot.variable_definitions
        assert snapshot.variable_definitions["agentName"]["type"] == "static"
        assert "currentDate" in snapshot.variable_definitions
        assert snapshot.variable_definitions["currentDate"]["type"] == "programmatic"
        assert "toolUsageGuide" in snapshot.variable_definitions
        assert snapshot.variable_definitions["toolUsageGuide"]["type"] == "template"

    def test_resolved_variables_contain_static(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        assert snapshot.variables["agentName"] == "Sherlock"

    def test_resolved_variables_contain_programmatic(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        # currentDate should be a date string
        assert isinstance(snapshot.variables["currentDate"], str)
        assert len(snapshot.variables["currentDate"]) == 10  # YYYY-MM-DD

    def test_resolved_variables_contain_template(self):
        snapshot = load_agent_from_folder(SHERLOCK_DIR)
        # Template variables are rendered strings
        assert isinstance(snapshot.variables["toolUsageGuide"], str)
        assert "GET_GPAY_USER_DATA_FOR_FINANCIAL_ASSISTANT" in snapshot.variables["toolUsageGuide"]


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

"""
Agent loader: reads agent folder structure, resolves variables, renders templates.

Resolution pipeline:
1. Parse agent.yaml
2. Resolve variables (static, programmatic, template)
3. Build model dict
4. Render prompt.ftl with model
5. Return AgentSnapshot
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.services.freemarker import FreemarkerRenderer, FreemarkerError


@dataclass
class AgentSnapshot:
    """Complete resolved agent definition."""
    name: str
    version: str
    model: str
    description: str
    system_prompt: str          # Rendered final prompt
    raw_template: str           # Original .ftl content
    variables: dict             # Resolved variable values
    variable_definitions: dict  # Original YAML variable defs
    tools: list[str]            # Tool name list
    widgets: list[str]          # Widget name list
    tool_details: list[dict]    # Full tool objects from availableToolsList
    widget_details: list[dict]  # Full widget objects from availableUiWidgetsList
    tool_definitions: list[dict] = field(default_factory=list)  # Gemini function declarations


class AgentLoadError(Exception):
    """Raised when agent loading fails."""
    pass


_renderer = FreemarkerRenderer()


def _resolve_programmatic_variable(code: str, agent_config: dict) -> Any:
    """Execute a Python snippet that sets `result`, with `agent` dict available."""
    local_vars: dict[str, Any] = {"agent": agent_config}
    try:
        exec(code, {"__builtins__": __builtins__}, local_vars)
    except Exception as e:
        raise AgentLoadError(f"Programmatic variable execution failed: {e}")

    if "result" not in local_vars:
        raise AgentLoadError(f"Programmatic variable did not set 'result'. Code:\n{code}")

    return local_vars["result"]


def _resolve_template_variable(
    path: str,
    agent_folder: Path,
    model: dict,
) -> str:
    """Load and render a sub-template .ftl file."""
    template_path = agent_folder / path
    if not template_path.exists():
        raise AgentLoadError(f"Sub-template not found: {template_path}")

    template_content = template_path.read_text(encoding="utf-8")
    try:
        return _renderer.render(template_content, {"model": model})
    except FreemarkerError as e:
        raise AgentLoadError(f"Error rendering sub-template '{path}': {e}")


def load_agent_from_folder(folder_path: str | Path) -> AgentSnapshot:
    """
    Load an agent definition from a folder.

    The folder must contain:
    - agent.yaml: Agent metadata, variables, tools, widgets
    - prompt.ftl: Main system prompt template

    Returns a fully resolved AgentSnapshot.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        raise AgentLoadError(f"Agent folder not found: {folder}")

    # 1. Parse agent.yaml
    yaml_path = folder / "agent.yaml"
    if not yaml_path.exists():
        raise AgentLoadError(f"agent.yaml not found in {folder}")

    with open(yaml_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not config:
        raise AgentLoadError(f"agent.yaml is empty in {folder}")

    name = config.get("name", folder.name)
    version = config.get("version", "1.0")
    model_name = config.get("model", "gemini-2.5-pro")
    description = config.get("description", "")
    tools = config.get("tools", [])
    widgets = config.get("widgets", [])
    variable_definitions = config.get("variables", {})
    tool_definitions = config.get("tool_definitions", [])

    # 2. Resolve variables in dependency order:
    #    static first, then programmatic, then template
    resolved: dict[str, Any] = {}

    # Pass 1: static variables
    for var_name, var_def in variable_definitions.items():
        if var_def.get("type") == "static":
            resolved[var_name] = var_def.get("value")

    # Pass 2: programmatic variables (may reference agent config)
    for var_name, var_def in variable_definitions.items():
        if var_def.get("type") == "programmatic":
            code = var_def.get("code", "")
            resolved[var_name] = _resolve_programmatic_variable(code, config)

    # Pass 3: template variables (rendered with all resolved vars so far)
    for var_name, var_def in variable_definitions.items():
        if var_def.get("type") == "template":
            path = var_def.get("path", "")
            resolved[var_name] = _resolve_template_variable(path, folder, resolved)

    # 3. Build model dict
    template_model = {"model": resolved}

    # 4. Load and render prompt.ftl
    prompt_path = folder / "prompt.ftl"
    if not prompt_path.exists():
        raise AgentLoadError(f"prompt.ftl not found in {folder}")

    raw_template = prompt_path.read_text(encoding="utf-8")

    try:
        system_prompt = _renderer.render(raw_template, template_model)
    except FreemarkerError as e:
        raise AgentLoadError(f"Error rendering prompt.ftl: {e}")

    # 5. Extract tool/widget details from resolved variables
    tool_details = resolved.get("availableToolsList", [])
    if not isinstance(tool_details, list):
        tool_details = []

    widget_details = resolved.get("availableUiWidgetsList", [])
    if not isinstance(widget_details, list):
        widget_details = []

    return AgentSnapshot(
        name=name,
        version=version,
        model=model_name,
        description=description,
        system_prompt=system_prompt,
        raw_template=raw_template,
        variables=resolved,
        variable_definitions=variable_definitions,
        tools=tools,
        widgets=widgets,
        tool_details=tool_details,
        widget_details=widget_details,
        tool_definitions=tool_definitions,
    )


def list_agent_folders(agents_dir: str | Path) -> list[str]:
    """List available agent folder names in the agents directory."""
    agents_path = Path(agents_dir)
    if not agents_path.is_dir():
        return []

    return [
        d.name for d in sorted(agents_path.iterdir())
        if d.is_dir() and (d / "agent.yaml").exists()
    ]

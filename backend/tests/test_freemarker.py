"""Tests for the FreeMarker subset renderer."""

import pytest
from app.services.freemarker import FreemarkerRenderer, FreemarkerError


@pytest.fixture
def renderer():
    return FreemarkerRenderer()


# --- Interpolation ---

class TestInterpolation:
    def test_simple_variable(self, renderer):
        result = renderer.render("Hello ${name}!", {"name": "World"})
        assert result == "Hello World!"

    def test_dot_notation(self, renderer):
        result = renderer.render("${model.name}", {"model": {"name": "Sherlock"}})
        assert result == "Sherlock"

    def test_nested_dot_notation(self, renderer):
        result = renderer.render("${a.b.c}", {"a": {"b": {"c": "deep"}}})
        assert result == "deep"

    def test_numeric_value(self, renderer):
        result = renderer.render("Count: ${count}", {"count": 42})
        assert result == "Count: 42"

    def test_missing_variable_raises(self, renderer):
        with pytest.raises(FreemarkerError, match="not found"):
            renderer.render("${missing}", {})

    def test_array_indexing(self, renderer):
        result = renderer.render("${items[0]}", {"items": ["a", "b", "c"]})
        assert result == "a"

    def test_array_dot_access(self, renderer):
        model = {"tools": [{"name": "tool1"}, {"name": "tool2"}]}
        result = renderer.render("${tools[0].name}", model)
        assert result == "tool1"

    def test_none_value(self, renderer):
        result = renderer.render("${val}", {"val": None})
        assert result == ""


# --- Comments ---

class TestComments:
    def test_single_line_comment(self, renderer):
        result = renderer.render("before<#-- comment -->after", {})
        assert result == "beforeafter"

    def test_multiline_comment(self, renderer):
        template = "before<#-- \nmultiline\ncomment\n-->after"
        result = renderer.render(template, {})
        assert result == "beforeafter"

    def test_ftl_variable_comment(self, renderer):
        template = '<#-- @ftlvariable name="model" -->Hello'
        result = renderer.render(template, {})
        assert result == "Hello"


# --- List Directive ---

class TestListDirective:
    def test_simple_list(self, renderer):
        template = "<#list items as x>${x} </#list>"
        result = renderer.render(template, {"items": ["a", "b", "c"]})
        assert result == "a b c "

    def test_list_with_object_properties(self, renderer):
        tools = [{"name": "tool1"}, {"name": "tool2"}]
        template = "<#list tools as t>${t.name}\n</#list>"
        result = renderer.render(template, {"tools": tools})
        assert result == "tool1\ntool2\n"

    def test_list_model_scoped(self, renderer):
        template = "<#list model.items as item>${item}</#list>"
        result = renderer.render(template, {"model": {"items": ["x", "y"]}})
        assert result == "xy"

    def test_nested_list(self, renderer):
        template = "<#list rows as row><#list row.cells as cell>${cell} </#list>| </#list>"
        data = {"rows": [{"cells": ["a", "b"]}, {"cells": ["c", "d"]}]}
        result = renderer.render(template, data)
        assert result == "a b | c d | "

    def test_empty_list(self, renderer):
        template = "<#list items as x>${x}</#list>"
        result = renderer.render(template, {"items": []})
        assert result == ""

    def test_list_with_surrounding_text(self, renderer):
        template = "Tools:\n<#list tools as t>- ${t.name}\n</#list>End"
        result = renderer.render(template, {"tools": [{"name": "A"}, {"name": "B"}]})
        assert result == "Tools:\n- A\n- B\nEnd"

    def test_list_non_iterable_raises(self, renderer):
        with pytest.raises(FreemarkerError, match="did not resolve to a list"):
            renderer.render("<#list x as i>${i}</#list>", {"x": "string"})


# --- Conditional Directive ---

class TestConditionalDirective:
    def test_if_true(self, renderer):
        template = "<#if show>visible</#if>"
        result = renderer.render(template, {"show": True})
        assert result == "visible"

    def test_if_false(self, renderer):
        template = "<#if show>visible</#if>"
        result = renderer.render(template, {"show": False})
        assert result == ""

    def test_if_else(self, renderer):
        template = "<#if show>yes<#else>no</#if>"
        assert renderer.render(template, {"show": True}) == "yes"
        assert renderer.render(template, {"show": False}) == "no"

    def test_if_elseif_else(self, renderer):
        template = "<#if x == 1>one<#elseif x == 2>two<#else>other</#if>"
        assert renderer.render(template, {"x": 1}) == "one"
        assert renderer.render(template, {"x": 2}) == "two"
        assert renderer.render(template, {"x": 3}) == "other"

    def test_comparison_not_equal(self, renderer):
        template = "<#if count != 0>has items<#else>empty</#if>"
        assert renderer.render(template, {"count": 5}) == "has items"
        assert renderer.render(template, {"count": 0}) == "empty"

    def test_comparison_operators_with_parens(self, renderer):
        """In FreeMarker, > and < inside <#if> tags need parentheses to avoid ambiguity."""
        assert renderer.render("<#if (x > 5)>big</#if>", {"x": 10}) == "big"
        assert renderer.render("<#if (x > 5)>big</#if>", {"x": 3}) == ""
        assert renderer.render("<#if (x < 5)>small</#if>", {"x": 3}) == "small"
        assert renderer.render("<#if x >= 5>ok</#if>", {"x": 5}) == "ok"
        assert renderer.render("<#if x <= 5>ok</#if>", {"x": 5}) == "ok"

    def test_comparison_text_operators(self, renderer):
        """FreeMarker gt/lt/gte/lte text operators avoid ambiguity."""
        assert renderer.render("<#if x gt 5>big</#if>", {"x": 10}) == "big"
        assert renderer.render("<#if x gt 5>big</#if>", {"x": 3}) == ""
        assert renderer.render("<#if x lt 5>small</#if>", {"x": 3}) == "small"
        assert renderer.render("<#if x gte 5>ok</#if>", {"x": 5}) == "ok"
        assert renderer.render("<#if x lte 5>ok</#if>", {"x": 5}) == "ok"

    def test_string_comparison(self, renderer):
        template = '<#if status == "active">on<#else>off</#if>'
        assert renderer.render(template, {"status": "active"}) == "on"
        assert renderer.render(template, {"status": "inactive"}) == "off"

    def test_truthiness_zero(self, renderer):
        template = "<#if count>has<#else>empty</#if>"
        assert renderer.render(template, {"count": 0}) == "empty"
        assert renderer.render(template, {"count": 5}) == "has"

    def test_truthiness_empty_string(self, renderer):
        template = "<#if text>has<#else>empty</#if>"
        assert renderer.render(template, {"text": ""}) == "empty"
        assert renderer.render(template, {"text": "hello"}) == "has"

    def test_truthiness_empty_list(self, renderer):
        template = "<#if items>has<#else>empty</#if>"
        assert renderer.render(template, {"items": []}) == "empty"
        assert renderer.render(template, {"items": [1]}) == "has"

    def test_truthiness_none(self, renderer):
        template = "<#if val>has<#else>none</#if>"
        assert renderer.render(template, {"val": None}) == "none"

    def test_logical_and(self, renderer):
        template = "<#if a && b>both<#else>no</#if>"
        assert renderer.render(template, {"a": True, "b": True}) == "both"
        assert renderer.render(template, {"a": True, "b": False}) == "no"

    def test_logical_or(self, renderer):
        template = "<#if a || b>any<#else>none</#if>"
        assert renderer.render(template, {"a": False, "b": True}) == "any"
        assert renderer.render(template, {"a": False, "b": False}) == "none"

    def test_negation(self, renderer):
        template = "<#if !show>hidden</#if>"
        assert renderer.render(template, {"show": False}) == "hidden"
        assert renderer.render(template, {"show": True}) == ""

    def test_nested_if(self, renderer):
        template = "<#if a><#if b>both<#else>only a</#if></#if>"
        assert renderer.render(template, {"a": True, "b": True}) == "both"
        assert renderer.render(template, {"a": True, "b": False}) == "only a"
        assert renderer.render(template, {"a": False, "b": True}) == ""


# --- Complex / Integration ---

class TestComplexTemplates:
    def test_list_inside_if(self, renderer):
        template = "<#if model.count != 0><#list model.items as i>${i} </#list><#else>nothing</#if>"
        assert renderer.render(template, {"model": {"count": 2, "items": ["a", "b"]}}) == "a b "
        assert renderer.render(template, {"model": {"count": 0, "items": []}}) == "nothing"

    def test_if_inside_list(self, renderer):
        template = "<#list items as i><#if i.active>${i.name} </#if></#list>"
        items = [
            {"name": "A", "active": True},
            {"name": "B", "active": False},
            {"name": "C", "active": True},
        ]
        assert renderer.render(template, {"items": items}) == "A C "

    def test_realistic_tool_list(self, renderer):
        template = """<#list model.availableToolsList as t>
**${t.name}**
${t.usageGuidelines}

</#list>"""
        model = {
            "model": {
                "availableToolsList": [
                    {"name": "TOOL_A", "usageGuidelines": "Use for X."},
                    {"name": "TOOL_B", "usageGuidelines": "Use for Y."},
                ]
            }
        }
        result = renderer.render(template, model)
        assert "**TOOL_A**" in result
        assert "Use for X." in result
        assert "**TOOL_B**" in result
        assert "Use for Y." in result

    def test_full_agent_prompt_structure(self, renderer):
        template = """You are ${model.agentName}.
Today's date is ${model.currentDate}.

<#if model.toolCount != 0>
## Tools
<#list model.tools as t>
- ${t.name}: ${t.desc}
</#list>
</#if>

<#if model.widgetCount != 0>
## Widgets
<#list model.widgets as w>
- ${w.name}
</#list>
</#if>"""
        model = {
            "model": {
                "agentName": "Sherlock",
                "currentDate": "2026-03-01",
                "toolCount": 2,
                "tools": [
                    {"name": "search", "desc": "Search the web"},
                    {"name": "calc", "desc": "Calculate"},
                ],
                "widgetCount": 1,
                "widgets": [{"name": "PIE_CHART"}],
            }
        }
        result = renderer.render(template, model)
        assert "You are Sherlock." in result
        assert "2026-03-01" in result
        assert "- search: Search the web" in result
        assert "- PIE_CHART" in result

    def test_builtin_size(self, renderer):
        result = renderer.render("${items?size}", {"items": [1, 2, 3]})
        assert result == "3"

    def test_plain_text_passthrough(self, renderer):
        text = "No directives here, just plain text."
        assert renderer.render(text, {}) == text

    def test_empty_template(self, renderer):
        assert renderer.render("", {}) == ""

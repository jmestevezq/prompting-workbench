"""Tests for the code sandbox.

Focus: behavior of code execution, context injection, and timeout enforcement.
"""

import pytest
from app.services.code_sandbox import execute_agent_code


class TestCodeExecution:
    def test_simple_print(self):
        result = execute_agent_code("print('hello')", {})
        assert result["returncode"] == 0
        assert "hello" in result["stdout"]
        assert result["stderr"] == ""

    def test_transactions_variable_available(self):
        context = {"transactions": [{"amount": 100}, {"amount": 200}]}
        result = execute_agent_code("print(len(transactions))", context)
        assert result["returncode"] == 0
        assert "2" in result["stdout"]

    def test_user_profile_variable_available(self):
        context = {"user_profile": {"name": "Jane"}}
        result = execute_agent_code("print(user_profile['name'])", context)
        assert result["returncode"] == 0
        assert "Jane" in result["stdout"]

    def test_computation_result(self):
        context = {"transactions": [{"amount": 100}, {"amount": 200}, {"amount": 50}]}
        code = "total = sum(t['amount'] for t in transactions)\nprint(total)"
        result = execute_agent_code(code, context)
        assert result["returncode"] == 0
        assert "350" in result["stdout"]

    def test_syntax_error_returns_nonzero(self):
        result = execute_agent_code("def broken(:\n  pass", {})
        assert result["returncode"] != 0
        assert result["stderr"] != ""

    def test_runtime_error_returns_nonzero(self):
        result = execute_agent_code("x = 1 / 0", {})
        assert result["returncode"] != 0
        assert "ZeroDivisionError" in result["stderr"]

    def test_stdout_captured(self):
        result = execute_agent_code("print('line1')\nprint('line2')", {})
        assert "line1" in result["stdout"]
        assert "line2" in result["stdout"]

    def test_empty_context(self):
        result = execute_agent_code("print('ok')", {})
        assert result["returncode"] == 0

    def test_multiline_code(self):
        code = """
total = 0
for t in transactions:
    total += t.get('amount', 0)
print(f'Total: {total}')
"""
        context = {"transactions": [{"amount": 10}, {"amount": 20}]}
        result = execute_agent_code(code, context)
        assert result["returncode"] == 0
        assert "Total: 30" in result["stdout"]

    def test_import_allowed_in_sandbox(self):
        result = execute_agent_code("import math\nprint(math.pi)", {})
        assert result["returncode"] == 0
        assert "3.14" in result["stdout"]

    def test_timeout_enforced(self):
        result = execute_agent_code("import time\ntime.sleep(100)", {}, timeout=1)
        assert result["returncode"] == -1
        assert "timed out" in result["stderr"].lower()

    def test_result_dict_has_all_fields(self):
        result = execute_agent_code("print('test')", {})
        assert "stdout" in result
        assert "stderr" in result
        assert "returncode" in result

    def test_empty_code(self):
        # Empty code is valid Python (no-op)
        result = execute_agent_code("", {})
        assert result["returncode"] == 0

    def test_json_serializable_context(self):
        # Context with lists and nested dicts should serialize correctly
        context = {
            "transactions": [{"category": "food", "amount": 50.5, "tags": ["a", "b"]}],
            "user_profile": {"name": "Jane", "nested": {"key": "value"}},
        }
        result = execute_agent_code("print(transactions[0]['category'])", context)
        assert result["returncode"] == 0
        assert "food" in result["stdout"]

"""Subprocess-based Python code execution with timeout."""

import json
import subprocess
import tempfile
import os


def execute_agent_code(code: str, context: dict, timeout: int = 10) -> dict:
    """Run agent-generated Python code in a subprocess.

    Args:
        code: Python code to execute
        context: Dict of variables to inject (transactions, user_profile, etc.)
        timeout: Max execution time in seconds

    Returns:
        Dict with stdout, stderr, returncode
    """
    # Serialize context safely — use a temp file to avoid shell escaping issues
    context_json = json.dumps(context)

    wrapper = f"""
import json, sys

# Load context from env
_ctx_json = '''{context_json}'''
_context = json.loads(_ctx_json)
transactions = _context.get('transactions', [])
user_profile = _context.get('user_profile', {{}})

# Execute user code
{code}
"""

    tmp_fd = None
    tmp_path = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".py")
        with os.fdopen(tmp_fd, "w") as f:
            f.write(wrapper)
            tmp_fd = None  # fdopen takes ownership

        result = subprocess.run(
            ["python3", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Code execution timed out after {timeout} seconds",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
        }
    finally:
        if tmp_fd is not None:
            os.close(tmp_fd)
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

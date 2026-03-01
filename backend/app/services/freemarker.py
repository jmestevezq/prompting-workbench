"""
FreeMarker subset renderer for agent prompt templates.

Supports:
- Interpolation: ${expr}, ${a.b.c}
- List directive: <#list expr as var>...</#list>
- Conditional: <#if expr>...<#elseif expr>...<#else>...</#if>
- Comments: <#-- text -->
- Index variables in lists: var?index (0-based), var?counter (1-based),
  var?has_next, var?is_first, var?is_last

Uses a recursive descent parser for reliable nested directive handling.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    TEXT = auto()
    INTERPOLATION = auto()      # ${expr}
    LIST_START = auto()          # <#list expr as var>
    LIST_END = auto()            # </#list>
    IF_START = auto()            # <#if expr>
    ELSEIF = auto()              # <#elseif expr>
    ELSE = auto()                # <#else>
    IF_END = auto()              # </#if>
    COMMENT = auto()             # <#-- ... -->


@dataclass
class Token:
    type: TokenType
    value: str = ""
    expr: str = ""           # For directives that carry an expression
    var_name: str = ""       # For #list: the loop variable name


class FreemarkerError(Exception):
    """Raised when template rendering fails."""
    pass


# Regex patterns for simple directives (no expression ambiguity with > or <)
_SIMPLE_PATTERNS = [
    # Comments: <#-- ... -->  (non-greedy)
    (TokenType.COMMENT, re.compile(r'<#--.*?-->', re.DOTALL)),
    # List end
    (TokenType.LIST_END, re.compile(r'</#list>')),
    # If end
    (TokenType.IF_END, re.compile(r'</#if>')),
    # Else
    (TokenType.ELSE, re.compile(r'<#else\s*>')),
    # List start: <#list expr as var>
    (TokenType.LIST_START, re.compile(r'<#list\s+(.+?)\s+as\s+(\w+)\s*>')),
    # Interpolation: ${expr}
    (TokenType.INTERPOLATION, re.compile(r'\$\{(.+?)\}')),
]

# Patterns for directives that contain expressions with possible > or < operators.
# These need manual scanning to find the correct closing >.
_EXPR_DIRECTIVE_RE = re.compile(r'<#(if|elseif)\s+')


def _find_directive_close(template: str, start: int) -> int:
    """Find the closing > of a directive that may contain > or < operators.

    Handles cases like <#if x > 5> by tracking parentheses and recognizing
    that >= is a single operator (not > followed by =).

    Returns the index of the closing > character.
    """
    pos = start
    length = len(template)
    paren_depth = 0
    in_string: str | None = None

    while pos < length:
        c = template[pos]

        # Handle string literals
        if in_string:
            if c == '\\':
                pos += 2
                continue
            if c == in_string:
                in_string = None
            pos += 1
            continue

        if c in ('"', "'"):
            in_string = c
            pos += 1
            continue

        # Track parentheses
        if c == '(':
            paren_depth += 1
        elif c == ')':
            paren_depth -= 1

        # > could be: tag close, comparison operator, or part of >=
        if c == '>' and paren_depth == 0:
            # Check if it's >= (comparison operator)
            if pos + 1 < length and template[pos + 1] == '=':
                pos += 2  # Skip >=
                continue
            # This > closes the tag
            return pos

        # < inside expression is a comparison operator (not a new tag)
        # because new tags always have <# or </ after <

        pos += 1

    raise FreemarkerError("Unclosed directive tag")


def _tokenize(template: str) -> list[Token]:
    """Tokenize a FreeMarker template into a list of tokens."""
    tokens: list[Token] = []
    pos = 0
    length = len(template)

    while pos < length:
        # Find the earliest match across all pattern types
        earliest_pos = length
        earliest_end = length
        earliest_type = None
        earliest_data: dict = {}

        # Check simple regex patterns
        for token_type, pattern in _SIMPLE_PATTERNS:
            m = pattern.search(template, pos)
            if m and m.start() < earliest_pos:
                earliest_pos = m.start()
                earliest_end = m.end()
                earliest_type = token_type
                earliest_data = {"match": m}

        # Check expression directives (<#if ...> and <#elseif ...>)
        m = _EXPR_DIRECTIVE_RE.search(template, pos)
        if m and m.start() < earliest_pos:
            # Manually find the closing >
            try:
                close_pos = _find_directive_close(template, m.end())
                expr = template[m.end():close_pos].strip()
                directive_type = m.group(1)
                earliest_pos = m.start()
                earliest_end = close_pos + 1  # Skip past the >
                earliest_type = TokenType.IF_START if directive_type == "if" else TokenType.ELSEIF
                earliest_data = {"expr": expr}
            except FreemarkerError:
                pass  # Skip malformed directive

        if earliest_type is None:
            # No more directives — rest is plain text
            tokens.append(Token(TokenType.TEXT, value=template[pos:]))
            break

        # Emit text before the matched directive
        if earliest_pos > pos:
            tokens.append(Token(TokenType.TEXT, value=template[pos:earliest_pos]))

        # Emit the directive token
        if earliest_type == TokenType.COMMENT:
            tokens.append(Token(TokenType.COMMENT, value=earliest_data["match"].group(0)))
        elif earliest_type == TokenType.INTERPOLATION:
            tokens.append(Token(TokenType.INTERPOLATION, expr=earliest_data["match"].group(1).strip()))
        elif earliest_type == TokenType.LIST_START:
            m = earliest_data["match"]
            tokens.append(Token(TokenType.LIST_START, expr=m.group(1).strip(), var_name=m.group(2).strip()))
        elif earliest_type in (TokenType.IF_START, TokenType.ELSEIF):
            tokens.append(Token(earliest_type, expr=earliest_data["expr"]))
        elif earliest_type in (TokenType.LIST_END, TokenType.IF_END, TokenType.ELSE):
            tokens.append(Token(earliest_type))

        pos = earliest_end

    return tokens


def _resolve_variable(path: str, context: dict) -> Any:
    """
    Resolve a dotted path like 'model.availableToolsList' or 'item.name'
    against the context dict.

    Also handles built-in functions:
    - ?size  → len()
    - ?index, ?counter, ?has_next, ?is_first, ?is_last  (set by #list)
    - ?string  → str()
    """
    # Check for built-in function suffix
    builtin = None
    if "?" in path:
        path, builtin = path.rsplit("?", 1)

    parts = path.split(".")
    current: Any = context

    for part in parts:
        # Handle array indexing: e.g. items[0]
        idx_match = re.match(r'^(\w+)\[(\d+)\]$', part)
        if idx_match:
            key, idx = idx_match.group(1), int(idx_match.group(2))
            if isinstance(current, dict) and key in current:
                current = current[key]
                if isinstance(current, (list, tuple)) and idx < len(current):
                    current = current[idx]
                else:
                    raise FreemarkerError(f"Index {idx} out of range for '{key}'")
            else:
                raise FreemarkerError(f"Variable '{key}' not found in context")
        elif isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                raise FreemarkerError(f"Variable '{path}' not found in context (missing key '{part}')")
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            raise FreemarkerError(f"Cannot resolve '{part}' on {type(current).__name__} in path '{path}'")

    # Apply built-in function
    if builtin:
        if builtin == "size":
            if isinstance(current, (list, tuple, dict, str)):
                return len(current)
            raise FreemarkerError(f"Cannot apply ?size to {type(current).__name__}")
        elif builtin == "string":
            return str(current)
        elif builtin in ("index", "counter", "has_next", "is_first", "is_last"):
            # These are resolved by putting them in context during #list iteration
            raise FreemarkerError(f"Built-in ?{builtin} can only be used on list loop variables")
        else:
            raise FreemarkerError(f"Unknown built-in: ?{builtin}")

    return current


def _is_truthy(value: Any) -> bool:
    """FreeMarker truthiness: 0, '', None, empty collections are falsy."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return len(value) > 0
    if isinstance(value, (list, tuple, dict)):
        return len(value) > 0
    return True


def _evaluate_condition(expr: str, context: dict) -> bool:
    """
    Evaluate a condition expression.

    Supports: ==, !=, >, <, >=, <=, &&, ||, !, truthiness checks.
    String literals in single or double quotes.
    Numeric literals.
    """
    expr = expr.strip()

    # Handle logical operators (lowest precedence)
    # Split on || first (lower precedence than &&)
    depth = 0
    last_or = -1
    i = 0
    while i < len(expr):
        c = expr[i]
        if c in ('"', "'"):
            # Skip string literal
            quote = c
            i += 1
            while i < len(expr) and expr[i] != quote:
                if expr[i] == '\\':
                    i += 1
                i += 1
            i += 1
            continue
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        elif depth == 0 and i < len(expr) - 1 and expr[i:i+2] == '||':
            last_or = i
        i += 1

    if last_or >= 0:
        left = expr[:last_or].strip()
        right = expr[last_or+2:].strip()
        return _evaluate_condition(left, context) or _evaluate_condition(right, context)

    # Split on && (higher precedence than ||)
    depth = 0
    last_and = -1
    i = 0
    while i < len(expr):
        c = expr[i]
        if c in ('"', "'"):
            quote = c
            i += 1
            while i < len(expr) and expr[i] != quote:
                if expr[i] == '\\':
                    i += 1
                i += 1
            i += 1
            continue
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        elif depth == 0 and i < len(expr) - 1 and expr[i:i+2] == '&&':
            last_and = i
        i += 1

    if last_and >= 0:
        left = expr[:last_and].strip()
        right = expr[last_and+2:].strip()
        return _evaluate_condition(left, context) and _evaluate_condition(right, context)

    # Handle negation
    if expr.startswith("!"):
        inner = expr[1:].strip()
        # Handle !(...)
        if inner.startswith("(") and inner.endswith(")"):
            inner = inner[1:-1]
        return not _evaluate_condition(inner, context)

    # Handle parenthesized expressions
    if expr.startswith("(") and expr.endswith(")"):
        return _evaluate_condition(expr[1:-1], context)

    # Handle comparison operators (including text-based gt/lt/gte/lte for FreeMarker compat)
    for op in ("!=", "==", ">=", "<=", ">", "<", " gte ", " gt ", " lte ", " lt "):
        # Find the operator outside of strings
        depth = 0
        i = 0
        while i < len(expr):
            c = expr[i]
            if c in ('"', "'"):
                quote = c
                i += 1
                while i < len(expr) and expr[i] != quote:
                    if expr[i] == '\\':
                        i += 1
                    i += 1
                i += 1
                continue
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            elif depth == 0 and expr[i:i+len(op)] == op:
                left_str = expr[:i].strip()
                right_str = expr[i+len(op):].strip()
                left_val = _evaluate_expression(left_str, context)
                right_val = _evaluate_expression(right_str, context)
                if op == "==":
                    return left_val == right_val
                elif op == "!=":
                    return left_val != right_val
                elif op == ">":
                    return left_val > right_val
                elif op == "<":
                    return left_val < right_val
                elif op == ">=":
                    return left_val >= right_val
                elif op == "<=":
                    return left_val <= right_val
                elif op.strip() == "gt":
                    return left_val > right_val
                elif op.strip() == "lt":
                    return left_val < right_val
                elif op.strip() == "gte":
                    return left_val >= right_val
                elif op.strip() == "lte":
                    return left_val <= right_val
            i += 1

    # No operator — truthiness check
    value = _evaluate_expression(expr, context)
    return _is_truthy(value)


def _evaluate_expression(expr: str, context: dict) -> Any:
    """Evaluate a simple expression: variable path, string literal, or number."""
    expr = expr.strip()

    # String literal
    if (expr.startswith('"') and expr.endswith('"')) or \
       (expr.startswith("'") and expr.endswith("'")):
        return expr[1:-1]

    # Numeric literal
    try:
        if "." in expr and not any(c.isalpha() for c in expr):
            return float(expr)
        if expr.isdigit() or (expr.startswith("-") and expr[1:].isdigit()):
            return int(expr)
    except ValueError:
        pass

    # Boolean literal
    if expr == "true":
        return True
    if expr == "false":
        return False

    # Variable reference
    return _resolve_variable(expr, context)


class _Parser:
    """Recursive descent parser for FreeMarker token streams."""

    def __init__(self, tokens: list[Token], context: dict):
        self.tokens = tokens
        self.context = context
        self.pos = 0

    def parse(self) -> str:
        """Parse all tokens and return rendered string."""
        return self._parse_block()

    def _parse_block(self, stop_types: set[TokenType] | None = None) -> str:
        """Parse tokens until a stop token type or end of tokens."""
        parts: list[str] = []
        if stop_types is None:
            stop_types = set()

        while self.pos < len(self.tokens):
            token = self.tokens[self.pos]

            if token.type in stop_types:
                break

            if token.type == TokenType.TEXT:
                parts.append(token.value)
                self.pos += 1

            elif token.type == TokenType.COMMENT:
                self.pos += 1  # Skip comments

            elif token.type == TokenType.INTERPOLATION:
                value = _evaluate_expression(token.expr, self.context)
                parts.append(str(value) if value is not None else "")
                self.pos += 1

            elif token.type == TokenType.LIST_START:
                parts.append(self._parse_list(token))

            elif token.type == TokenType.IF_START:
                parts.append(self._parse_if(token))

            else:
                # Unexpected token — emit as empty
                self.pos += 1

        return "".join(parts)

    def _parse_list(self, list_token: Token) -> str:
        """Parse a <#list> ... </#list> block."""
        self.pos += 1  # Skip the LIST_START token

        # Collect body tokens until LIST_END
        body_start = self.pos
        depth = 1
        while self.pos < len(self.tokens) and depth > 0:
            if self.tokens[self.pos].type == TokenType.LIST_START:
                depth += 1
            elif self.tokens[self.pos].type == TokenType.LIST_END:
                depth -= 1
            if depth > 0:
                self.pos += 1

        body_tokens = self.tokens[body_start:self.pos]
        self.pos += 1  # Skip LIST_END

        # Resolve the iterable
        items = _evaluate_expression(list_token.expr, self.context)
        if not isinstance(items, (list, tuple)):
            raise FreemarkerError(f"<#list> expression '{list_token.expr}' did not resolve to a list")

        var_name = list_token.var_name
        parts: list[str] = []
        total = len(items)

        for idx, item in enumerate(items):
            # Create loop context with loop variable and built-ins
            loop_context = dict(self.context)
            loop_context[var_name] = item
            # Add loop built-ins as var_name + ?builtin
            loop_context[f"{var_name}?index"] = idx
            loop_context[f"{var_name}?counter"] = idx + 1
            loop_context[f"{var_name}?has_next"] = idx < total - 1
            loop_context[f"{var_name}?is_first"] = idx == 0
            loop_context[f"{var_name}?is_last"] = idx == total - 1

            # Parse body with loop context
            parser = _Parser(list(body_tokens), loop_context)
            parts.append(parser.parse())

        return "".join(parts)

    def _parse_if(self, if_token: Token) -> str:
        """Parse an <#if> ... <#elseif> ... <#else> ... </#if> block."""
        self.pos += 1  # Skip IF_START

        # We need to collect branches: [(condition_expr, body_tokens), ...]
        # with the last one possibly being an else (condition=None)
        branches: list[tuple[str | None, list[Token]]] = []

        # Collect the first branch body
        current_expr: str | None = if_token.expr
        body_tokens: list[Token] = []
        depth = 1

        while self.pos < len(self.tokens) and depth > 0:
            token = self.tokens[self.pos]

            if token.type == TokenType.IF_START:
                depth += 1
                body_tokens.append(token)
                self.pos += 1
            elif token.type == TokenType.IF_END:
                depth -= 1
                if depth == 0:
                    # End of our if block
                    branches.append((current_expr, body_tokens))
                    self.pos += 1  # Skip IF_END
                    break
                else:
                    body_tokens.append(token)
                    self.pos += 1
            elif depth == 1 and token.type == TokenType.ELSEIF:
                # Save current branch, start new one
                branches.append((current_expr, body_tokens))
                current_expr = token.expr
                body_tokens = []
                self.pos += 1
            elif depth == 1 and token.type == TokenType.ELSE:
                # Save current branch, start else branch
                branches.append((current_expr, body_tokens))
                current_expr = None  # else has no condition
                body_tokens = []
                self.pos += 1
            else:
                body_tokens.append(token)
                self.pos += 1

        # If we exited the loop without finding IF_END (shouldn't happen with valid templates)
        if depth > 0:
            branches.append((current_expr, body_tokens))

        # Evaluate branches
        for condition, branch_body in branches:
            if condition is None or _evaluate_condition(condition, self.context):
                parser = _Parser(branch_body, self.context)
                return parser.parse()

        return ""


class FreemarkerRenderer:
    """Renders FreeMarker templates with a given model dict."""

    def render(self, template: str, model: dict) -> str:
        """
        Render a FreeMarker template string with the given model.

        Args:
            template: FreeMarker template string
            model: Dict of variables available in the template

        Returns:
            Rendered string

        Raises:
            FreemarkerError: If rendering fails
        """
        tokens = _tokenize(template)
        parser = _Parser(tokens, model)
        return parser.parse()

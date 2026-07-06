"""Tool: calculate — safely evaluate a simple arithmetic expression."""
import sys
from pathlib import Path

from pydantic_ai import RunContext

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from wmt_ai.logger import get_logger, entry, exit_

_log = get_logger("TOOL")


async def calculate(ctx: RunContext, expression: str) -> str:
    """Safely evaluate a simple arithmetic expression and return the result.

    Args:
        expression: A math expression using +, -, *, /, (, ) and numbers only.
                    Example: '42 * 1337' or '(100 + 50) / 3'
    """
    entry(_log, "TOOL", "calculate", expression=expression)

    allowed = set("0123456789+-*/.() ")
    if not all(c in allowed for c in expression):
        result = f"Error: expression contains disallowed characters: {expression!r}"
    else:
        try:
            result = f"{expression} = {eval(expression, {'__builtins__': {}})}"  # noqa: S307
        except Exception as exc:
            result = f"Error evaluating '{expression}': {exc}"

    exit_(_log, "TOOL", "calculate", result)
    return result

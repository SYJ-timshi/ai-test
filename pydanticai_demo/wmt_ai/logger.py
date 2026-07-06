"""Shared debug logger for the demo.

Produces clean timestamped lines with capability tags so you can see exactly
which layer is executing at any moment:

    14:31:05  [TOOL]      >> calculate(expression='42 * 1337')
    14:31:05  [TOOL]      << calculate → '42 * 1337 = 56154'
    14:31:06  [SKILL]     >> search_knowledge(query='pydantic-ai')
    14:31:06  [MCP]       >> get_current_time()
    14:31:07  [SUBAGENT]  >> researcher.run(topic='Model Context Protocol')
"""
import logging
import sys


_FMT = "%(asctime)s  %(message)s"
_DATE = "%H:%M:%S"

# One shared handler — avoids duplicate lines when imported multiple times
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter(_FMT, datefmt=_DATE))


def get_logger(tag: str) -> logging.Logger:
    """Return a logger whose records are prefixed with [TAG] (padded to 10 chars)."""
    name = f"demo.{tag.lower()}"
    log = logging.getLogger(name)
    if not log.handlers:
        log.addHandler(_handler)
        log.setLevel(logging.DEBUG)
        log.propagate = False
    return log


def _pad(tag: str) -> str:
    return f"[{tag}]".ljust(11)


def entry(log: logging.Logger, tag: str, fn: str, **kwargs) -> None:
    """Log a tool/skill/agent entry line."""
    args_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    log.debug(f"{_pad(tag)} >> {fn}({args_str})")


def exit_(log: logging.Logger, tag: str, fn: str, result) -> None:
    """Log a tool/skill/agent exit line (truncates long results)."""
    r = repr(result)
    if len(r) > 120:
        r = r[:117] + "..."
    log.debug(f"{_pad(tag)} << {fn} → {r}")

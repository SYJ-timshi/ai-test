"""FastMCP HTTP server (Streamable HTTP transport) — must be started separately.

Three MCP capability areas exposed:

  TOOLS (LLM actively calls, may have side-effects):
    • roll_dice(sides, count)     — roll N dice with S sides
    • random_joke(category)       — jokes: programming | dad | general
    • random_quote(mood)          — quotes: motivational | funny | wisdom
    • word_scramble(text)         — scramble word middles (keep first/last letter)

  RESOURCES (LLM passively reads, always read-only):
    • cheatsheet://mcp            — MCP protocol quick reference
    • cheatsheet://pydantic-ai    — pydantic-ai quick reference
    • stats://server              — live server stats (tool count, uptime)

  PROMPTS (pre-baked prompt templates with arguments):
    • code_review(language, code) — structured code-review prompt
    • brainstorm(topic, count)    — idea-generation prompt
    • explain_like_five(concept)  — ELI5 explanation prompt

IMPORTANT — startup order
--------------------------
    Terminal 1:  uv run demo/mcp_server_http.py
    Terminal 2:  uv run demo/main.py --mcp both

Endpoint: http://127.0.0.1:8765/mcp
"""
import datetime
import logging
import random

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  [MCP-HTTP] %(message)s",
    datefmt="%H:%M:%S",
)
_log = logging.getLogger("mcp_server_http")

MCP_PORT   = 8765
_START_TIME = datetime.datetime.now(datetime.timezone.utc)

mcp = FastMCP("demo-mcp-http-server", port=MCP_PORT)

# ── static data ───────────────────────────────────────────────────────────────

_JOKES: dict[str, list[str]] = {
    "programming": [
        "Why do programmers prefer dark mode? Because light attracts bugs.",
        "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
        "There are 10 types of people: those who understand binary, and those who don't.",
        "Why do Java developers wear glasses? Because they don't C#.",
        "Debugging is like being the detective in a crime movie where you are also the murderer.",
    ],
    "dad": [
        "I'm reading a book about anti-gravity. It's impossible to put down.",
        "Did you hear about the mathematician who's afraid of negative numbers? He'll stop at nothing to avoid them.",
        "Why can't you give Elsa a balloon? Because she'll let it go.",
        "I used to hate facial hair, but then it grew on me.",
        "What do you call cheese that isn't yours? Nacho cheese.",
    ],
    "general": [
        "I told my wife she was drawing her eyebrows too high. She looked surprised.",
        "Why don't scientists trust atoms? Because they make up everything.",
        "I would tell you a construction joke, but I'm still working on it.",
        "Why did the scarecrow win an award? Because he was outstanding in his field.",
        "What do you call a fake noodle? An impasta.",
    ],
}

_QUOTES: dict[str, list[str]] = {
    "motivational": [
        "The only way to do great work is to love what you do. — Steve Jobs",
        "Code is poetry. Ship it. — Anonymous",
        "First, solve the problem. Then, write the code. — John Johnson",
        "Make it work, make it right, make it fast. — Kent Beck",
        "The best time to plant a tree was 20 years ago. The second best time is now.",
    ],
    "funny": [
        "I choose a lazy person to do a hard job, because a lazy person will find an easy way to do it. — Bill Gates",
        "Always code as if the guy who ends up maintaining your code will be a violent psychopath who knows where you live.",
        "Programming is 10% writing code and 90% figuring out why it doesn't work.",
        "The road to programming hell is paved with global variables.",
        "There is no place like 127.0.0.1.",
    ],
    "wisdom": [
        "Premature optimization is the root of all evil. — Donald Knuth",
        "Programs must be written for people to read, and only incidentally for machines to execute. — Abelson & Sussman",
        "Any fool can write code that a computer can understand. Good programmers write code that humans can understand. — Martin Fowler",
        "Simplicity is the soul of efficiency. — Austin Freeman",
        "The most dangerous phrase in the language is: 'We've always done it this way.' — Grace Hopper",
    ],
}

_CHEATSHEETS: dict[str, str] = {
    "mcp": """\
# MCP (Model Context Protocol) Quick Reference

## Three capability areas
| Area      | Decorator          | Read/Write | Typical use               |
|-----------|--------------------|------------|---------------------------|
| Tools     | @mcp.tool()        | R/W        | actions, calculations     |
| Resources | @mcp.resource(uri) | Read-only  | docs, config, db snapshots|
| Prompts   | @mcp.prompt()      | Read-only  | reusable prompt templates |

## Transport options
- stdio            — subprocess, zero config, one client only
- sse              — HTTP + Server-Sent Events, legacy
- streamable-http  — HTTP, stateless, multi-client (recommended)

## JSON-RPC flow
1. Client → tools/list       → server returns schema list
2. Client → tools/call       → server executes + returns result
3. Client → resources/list   → server returns URI list
4. Client → resources/read   → server returns resource content
5. Client → prompts/list     → server returns template list
6. Client → prompts/get      → server returns rendered messages
""",
    "pydantic-ai": """\
# pydantic-ai Quick Reference

## Agent creation
```python
from pydantic_ai import Agent
agent = Agent(model, output_type=MySchema, instructions="...", tools=[fn])
```

## Tool definition
```python
def my_tool(ctx: RunContext, x: int) -> str:
    \"\"\"Tool description shown to the LLM.\"\"\"
    return str(x * 2)
```

## MCP integration
```python
from pydantic_ai.mcp import MCPToolset, MCPServerStreamableHTTP
# stdio  (auto-subprocess)
MCPToolset(PythonStdioTransport(script_path="server.py"))
# http   (external server)
MCPServerStreamableHTTP("http://127.0.0.1:8765/mcp")
```

## Run patterns
```python
async with agent:
    result = await agent.run(prompt)               # one-shot
    result = await agent.run(msg, message_history=history)  # with history
```

## AgentBuilder (fluent)
```python
agent = (
    AgentBuilder(model)
    .with_tool(fn)
    .with_skill(toolset)
    .with_mcp(mcp_server)
    .build(backend="native")   # or "wmt"
)
```
""",
}


# ── TOOLS ────────────────────────────────────────────────────────────────────

@mcp.tool()
def roll_dice(sides: int = 6, count: int = 1) -> str:
    """Roll N dice each with S sides and return the results.

    Args:
        sides: Number of sides on each die (default 6, max 100)
        count: Number of dice to roll (default 1, max 10)
    """
    sides = max(2, min(sides, 100))
    count = max(1, min(count, 10))
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls)
    _log.debug(f"roll_dice(sides={sides}, count={count}) → {rolls}")
    if count == 1:
        return f"🎲 Rolled a d{sides}: **{rolls[0]}**"
    return f"🎲 Rolled {count}d{sides}: {rolls}  →  Total: **{total}**"


@mcp.tool()
def random_joke(category: str = "programming") -> str:
    """Return a random joke from a chosen category.

    Args:
        category: One of: programming | dad | general  (default: programming)
    """
    key = category.strip().lower()
    jokes = _JOKES.get(key, _JOKES["programming"])
    joke = random.choice(jokes)
    _log.debug(f"random_joke(category={key!r})")
    return f"😂 [{key}] {joke}"


@mcp.tool()
def random_quote(mood: str = "motivational") -> str:
    """Return an inspiring or funny quote by mood.

    Args:
        mood: One of: motivational | funny | wisdom  (default: motivational)
    """
    key = mood.strip().lower()
    quotes = _QUOTES.get(key, _QUOTES["motivational"])
    quote = random.choice(quotes)
    _log.debug(f"random_quote(mood={key!r})")
    return f"💬 [{key}] {quote}"


@mcp.tool()
def word_scramble(text: str) -> str:
    """Scramble the middle letters of each word (keeps first and last letter intact).

    Args:
        text: The sentence or phrase to scramble
    """
    def _scramble_word(word: str) -> str:
        if len(word) <= 3:
            return word
        middle = list(word[1:-1])
        random.shuffle(middle)
        return word[0] + "".join(middle) + word[-1]

    scrambled = " ".join(_scramble_word(w) for w in text.split())
    _log.debug(f"word_scramble({text!r})")
    return f"🔀 Original : {text!r}\n   Scrambled: {scrambled!r}"


# ── RESOURCES ────────────────────────────────────────────────────────────────
# Resources are read-only data the LLM can inspect at any time.
# URI scheme is arbitrary — just needs to be unique and descriptive.

@mcp.resource("cheatsheet://mcp")
def resource_mcp_cheatsheet() -> str:
    """MCP protocol quick-reference cheatsheet."""
    _log.debug("resource read: cheatsheet://mcp")
    return _CHEATSHEETS["mcp"]


@mcp.resource("cheatsheet://pydantic-ai")
def resource_pydantic_ai_cheatsheet() -> str:
    """pydantic-ai library quick-reference cheatsheet."""
    _log.debug("resource read: cheatsheet://pydantic-ai")
    return _CHEATSHEETS["pydantic-ai"]


@mcp.resource("stats://server")
def resource_server_stats() -> str:
    """Live server stats — tool count and uptime."""
    _log.debug("resource read: stats://server")
    uptime = datetime.datetime.now(datetime.timezone.utc) - _START_TIME
    return (
        f"Server: demo-mcp-http-server\n"
        f"Port  : {MCP_PORT}\n"
        f"Uptime: {str(uptime).split('.')[0]}\n"
        f"Tools : roll_dice, random_joke, random_quote, word_scramble\n"
        f"Resources: cheatsheet://mcp, cheatsheet://pydantic-ai, stats://server\n"
        f"Prompts: code_review, brainstorm, explain_like_five\n"
    )


# ── PROMPTS ──────────────────────────────────────────────────────────────────
# Prompts are reusable message templates.
# The LLM fetches them via prompts/get and injects the rendered messages into its context.

@mcp.prompt()
def code_review(language: str, code: str) -> str:
    """Structured code-review prompt for any language.

    Args:
        language: Programming language (e.g. python, typescript, java)
        code:     The code snippet to review
    """
    return f"""\
Please review the following {language} code and provide structured feedback:

```{language}
{code}
```

Cover these aspects:
1. **Correctness** — Does it do what it should? Any bugs?
2. **Readability** — Is it clear and well-named?
3. **Performance** — Any obvious inefficiencies?
4. **Security** — Any vulnerabilities or bad practices?
5. **Suggestions** — 2-3 concrete improvement ideas.

Be concise and constructive.
"""


@mcp.prompt()
def brainstorm(topic: str, count: int = 5) -> str:
    """Idea-generation prompt — produce N distinct ideas for a topic.

    Args:
        topic: The subject to brainstorm about
        count: Number of ideas to generate (default 5)
    """
    return f"""\
Generate {count} distinct, creative ideas about: **{topic}**

For each idea provide:
- A short title (≤ 8 words)
- One sentence explaining the core concept
- One sentence on why it's interesting or valuable

Number each idea. Be imaginative and avoid the obvious.
"""


@mcp.prompt()
def explain_like_five(concept: str) -> str:
    """ELI5 — explain a concept as if the reader is five years old.

    Args:
        concept: The technical concept to explain simply
    """
    return f"""\
Explain "{concept}" to a curious five-year-old.

Rules:
- Use only simple, everyday words (no jargon)
- Use a relatable analogy or story
- Keep it under 100 words
- End with one fun fact that will make them say "wow!"
"""


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _log.info(f"MCP HTTP server starting on http://127.0.0.1:{MCP_PORT}/mcp")
    _log.info("Tools    : roll_dice | random_joke | random_quote | word_scramble")
    _log.info("Resources: cheatsheet://mcp | cheatsheet://pydantic-ai | stats://server")
    _log.info("Prompts  : code_review | brainstorm | explain_like_five")
    mcp.run(transport="streamable-http")

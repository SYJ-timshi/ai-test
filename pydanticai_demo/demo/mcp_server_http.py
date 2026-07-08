"""FastMCP HTTP server (Streamable HTTP transport) — must be started separately.

Exposes fun / interactive tools NOT available in the stdio server:
  • roll_dice(sides, count)     — roll N dice with S sides
  • random_joke(category)       — pre-baked jokes: programming | dad | general
  • random_quote(mood)          — quotes: motivational | funny | wisdom
  • word_scramble(text)         — scramble words in a sentence (keeps first/last letter)

IMPORTANT — startup order
--------------------------
This server does NOT auto-spawn like the stdio variant.
You must start it in a separate terminal BEFORE running main.py with --mcp http|both:

    Terminal 1:  uv run demo/mcp_server_http.py
    Terminal 2:  uv run demo/main.py --mcp both

Endpoint: http://127.0.0.1:8765/mcp  (Streamable HTTP)
"""
import logging
import random

from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  [MCP-HTTP] %(message)s",
    datefmt="%H:%M:%S",
)
_log = logging.getLogger("mcp_server_http")

MCP_PORT = 8765

mcp = FastMCP("demo-mcp-http-server", port=MCP_PORT)

# ── data ──────────────────────────────────────────────────────────────────────

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


# ── tools ─────────────────────────────────────────────────────────────────────

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
    _log.debug(f"random_joke(category={key!r}) → {joke[:40]!r}...")
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
    _log.debug(f"random_quote(mood={key!r}) → {quote[:40]!r}...")
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

    words = text.split()
    scrambled = " ".join(_scramble_word(w) for w in words)
    _log.debug(f"word_scramble({text!r}) → {scrambled!r}")
    return f"🔀 Original: {text!r}\n   Scrambled: {scrambled!r}"


if __name__ == "__main__":
    _log.info(f"MCP HTTP server starting on http://127.0.0.1:{MCP_PORT}/mcp")
    _log.info("Tools: roll_dice | random_joke | random_quote | word_scramble")
    mcp.run(transport="streamable-http")

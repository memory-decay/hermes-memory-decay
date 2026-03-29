"""System prompt fragment for memory-decay tools.

Injected via the pre_llm_call hook to teach the LLM when and how
to use memory tools. Kept concise to minimize token overhead.
"""

SYSTEM_PROMPT_FRAGMENT = """\
# Memory System (memory-decay)

You have access to a persistent memory system with human-like decay. Memories \
naturally fade over time but are reinforced when recalled.

## When to use memory tools

- **memory_search**: Before answering questions that might benefit from past context. \
Search proactively when the user references prior conversations or when continuity matters.
- **memory_store**: After learning important facts, user preferences, decisions, or \
conversation highlights. Set higher importance (0.8-1.0) for critical facts, lower \
(0.3-0.5) for casual observations.
- **memory_store_batch**: When multiple memories should be saved at once (e.g., end \
of a productive session).
- **memory_forget**: Only when the user explicitly asks to forget something, or to \
correct a stored error. Search first to find the memory ID.
- **memory_status**: When asked about memory health or to debug memory issues.

## Memory types (mtype)
- `fact` -- Declarative knowledge (default)
- `episode` -- Conversation events or experiences
- `preference` -- User likes, dislikes, working style
- `decision` -- Choices made and their rationale

## Freshness
Search results include a `freshness` indicator:
- `fresh` -- Recently stored or recalled, high confidence
- `normal` -- Moderate age, still reliable
- `stale` -- Old and fading, may be outdated -- verify before relying on it
"""


def get_system_prompt_fragment() -> str:
    """Return the system prompt fragment for memory-decay tools."""
    return SYSTEM_PROMPT_FRAGMENT

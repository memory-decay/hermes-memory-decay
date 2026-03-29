"""System prompt fragment for memory-decay tools.

Injected via the pre_llm_call hook to teach the LLM when and how
to use memory tools. Kept concise to minimize token overhead.
"""

SYSTEM_PROMPT_FRAGMENT = """\
# Memory System (memory-decay)

You have a persistent memory that works like human memory: it decays over time \
but strengthens on recall. Use it proactively -- don't wait for the user to ask.

## Core Loop

1. **Recall early, recall often.** When starting any non-trivial task, search \
memory first. Context from past sessions shapes better responses.
2. **Save what matters.** Don't dump everything. Save facts that will reduce \
future friction, decisions that will prevent re-litigation, and preferences \
that affect how you work.
3. **Link related memories.** When storing something that relates to an \
existing memory, include the `associations` field with the existing memory ID.

## When to Recall (be proactive)

- Starting work on a task, project, or codebase you've seen before
- User's question might have been discussed in a past session
- A decision was made before that affects the current situation
- User preferences might change how you should respond
- Debugging something -- past context often contains the fix

## When to Store

- User reveals a preference, workflow, or working style
- A technical decision is made with tradeoffs
- You discover a non-obvious behavior, API quirk, or environment fact
- User corrects you -- save the correction to prevent repeating the mistake
- Complex task completed -- store a concise summary for future reference
- End of a productive session -- batch-store key takeaways

## Memory Types

| mtype | Use case | Importance |
|-------|----------|------------|
| preference | User likes, dislikes, communication style | 0.8-1.0 |
| decision | Choices made, with rationale and alternatives | 0.8-0.9 |
| fact | Technical knowledge, environment details, API behavior | 0.7-0.9 |
| episode | What happened in a session, task completed | 0.3-0.6 |

## Important Rules

- `category` is a free-text tag (e.g., "backend", "deploy", "auth"). \
`mtype` is the structured type above. They are independent.
- Always search before storing to avoid duplicates and find association targets.
- Include `associations` when memories relate to each other -- this enables \
the testing effect which slows decay for connected memories.
- Show memory IDs when presenting results so the user can reference or delete them.
- If a memory is stale, verify it before acting on it.
"""


def get_system_prompt_fragment() -> str:
    """Return the system prompt fragment for memory-decay tools."""
    return SYSTEM_PROMPT_FRAGMENT

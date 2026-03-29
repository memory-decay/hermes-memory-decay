3. **Present results clearly:**
   - Show the memory content, category, and relevance score
   - Indicate freshness with action guidance:
     - **fresh** (storage_score > 0.7) -- reliable, act on it confidently
     - **normal** (0.3 < storage_score <= 0.7) -- likely accurate, verify if consequential
     - **stale** (storage_score <= 0.3) -- may be outdated, verify before acting or warn user
4. **If results are stale**, warn the user that the information may have changed.

## Proactive Recall

Don't wait for a command. Search automatically when:
- User asks about prior decisions or history
- User says "like last time" or "you remember when..."
- A recurring topic comes up
- User preferences might affect the current response
- You're about to make a recommendation and context exists

## Query Tips

| Goal | Good Query | Bad Query |
|------|-----------|-----------|
| Find a past decision | "which database did we choose and why" | "database" |
| Recall user preference | "user's preferred coding style" | "style" |
| Find debugging context | "auth middleware error we fixed" | "error" |
| Session history | "what we worked on for the migration" | "migration" |

## Result Interpretation

Each result includes:
- `id`: Memory identifier (e.g., `mem_abc123`) -- for deletion if needed
- `text`: The stored content
- `score`: Combined relevance score (retrieval + decay-weighted storage)
- `storage_score`: Activation/decay level -- maps to freshness
- `retrieval_score`: Raw semantic similarity (0-1)
- `category`: Memory type (fact, episode, preference, decision)
- `speaker`: Who said it (user, assistant, or empty)

## Rules

- If no results are found, say so honestly -- never fabricate memories.
- Show the memory ID (`mem_xxx`) so the user can reference or delete specific memories.
- Recall reinforces memories -- the testing effect boosts their activation.
- When multiple results overlap, synthesize rather than repeating all of them.
- Stale results are still useful for context but should be verified before acting on.

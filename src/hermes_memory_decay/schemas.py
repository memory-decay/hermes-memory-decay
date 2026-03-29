"""OpenAI-format tool schemas for memory-decay tools.

These schemas are what the LLM sees when deciding which tool to call.
Parameter names match the memory-decay-core server StoreRequest/SearchRequest models.
"""

MEMORY_SEARCH_SCHEMA = {
    "name": "memory_search",
    "description": (
        "Search your memories by semantic similarity. Returns ranked results "
        "with relevance scores. Memories that have decayed significantly will "
        "rank lower. Use this to recall past conversations, facts, or context."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query",
            },
            "top_k": {
                "type": "integer",
                "description": "Max results to return (1-20, default 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}

MEMORY_STORE_SCHEMA = {
    "name": "memory_store",
    "description": (
        "Store a new memory. Memories naturally decay over time but are "
        "reinforced when recalled. Use for important facts, decisions, "
        "user preferences, or conversation highlights worth remembering."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The memory content to store",
            },
            "importance": {
                "type": "number",
                "description": "Importance score 0.0-1.0 (default 0.7). Higher = decays slower.",
                "default": 0.7,
            },
            "category": {
                "type": "string",
                "description": "Category tag (e.g. 'user_preference', 'decision', 'fact')",
                "default": "",
            },
            "mtype": {
                "type": "string",
                "description": "Memory type: 'fact', 'episode', 'preference', 'decision'",
                "default": "fact",
            },
            "associations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Related memory IDs to create associative links",
            },
            "speaker": {
                "type": "string",
                "description": "Who said this (e.g. 'user', 'assistant')",
            },
        },
        "required": ["text"],
    },
}

MEMORY_STORE_BATCH_SCHEMA = {
    "name": "memory_store_batch",
    "description": (
        "Store multiple memories at once. More efficient than individual stores "
        "when saving several related memories from a conversation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "importance": {"type": "number", "default": 0.7},
                        "category": {"type": "string", "default": ""},
                        "mtype": {"type": "string", "default": "fact"},
                        "associations": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "speaker": {"type": "string"},
                    },
                    "required": ["text"],
                },
                "description": "Array of memory objects to store",
            },
        },
        "required": ["items"],
    },
}

MEMORY_FORGET_SCHEMA = {
    "name": "memory_forget",
    "description": (
        "Permanently delete a specific memory by its ID. Use when the user "
        "explicitly asks to forget something, or to remove incorrect memories."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "memory_id": {
                "type": "string",
                "description": "The memory ID to delete (e.g. 'mem_abc123def456')",
            },
        },
        "required": ["memory_id"],
    },
}

MEMORY_STATUS_SCHEMA = {
    "name": "memory_status",
    "description": (
        "Check the health and statistics of the memory system. Shows total "
        "memory count, current decay tick, and server status."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
    },
}

- **No matches**: Tell the user nothing was found. Suggest different search terms.
- **Incorrect memory**: If the user wants to correct a memory, delete the old one first, then store the corrected version with `memory_store`.
- **"Forget everything about X"**: Search broadly, show all matches, confirm batch deletion.

## Correction Workflow

When a stored memory is wrong:
1. Search for the incorrect memory
2. Show it to the user for confirmation
3. Delete with `memory_forget`
4. Store the correct version with `memory_store`

## Rules

- Never delete memories without explicit user confirmation.
- Always search first -- never guess memory IDs.
- After deletion, the memory is permanently gone and cannot be recovered.
- Memories also fade naturally via decay -- only use forget for immediate removal.

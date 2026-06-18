"""UserPromptSubmit hook: re-inject the standing order to hand Pip's per-message mood to the
cheap pip-face (Haiku) subagent, so the main loop never picks the emotional mood itself.
Stdout on UserPromptSubmit is added to the model's context -- no MCP call here (the subagent
applies the face over the shared session link)."""
print(
    "Pip mood policy (every message): the cheap pip-face (Haiku) subagent picks and sets "
    "Pip's emotional face -- never you. In your first tool-call batch this turn, dispatch "
    "the pip-face subagent (Agent tool, subagent_type='pip-face') with a one-line read of "
    "the user's message, IN PARALLEL with your real work -- don't wait on it, and don't "
    "choose or call face yourself."
)

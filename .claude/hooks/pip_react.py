"""UserPromptSubmit hook: make Pip react on every message via the pip-face subagent."""
import json

# Injected into the turn's context, nudging the main agent to mirror this moment on the robot.
nudge = (
    "Pip is live this turn: spawn the `pip-face` subagent in the background "
    "(subagent_type 'pip-face', run_in_background true) with a one-line read of "
    "this moment so the robot reacts. Coding moment -> hold `smoking`; plain chat "
    "-> any fitting mood."
)

print(json.dumps({
    "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": nudge}
}))

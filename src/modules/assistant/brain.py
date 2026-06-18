"""Pip's brain: a local Ollama model that talks, emotes, and drives the ESP32.

Every turn the model returns a structured reply -- {"response", "emotion",
"gesture"} -- whose emotion/gesture animate Pip's face, and it acts on the world
through tool calls (set_activity + generic pin tools). History is kept across turns.
"""
from __future__ import annotations

from modules.espbridge.eyes import GESTURES, MOODS, REACTIONS
from modules.llm import ollama_llm

MAX_HISTORY = 24  # ~12 exchanges

_GESTURES = ("none", *GESTURES, *REACTIONS)    # one-shot moves (deliberate + reflexes) + sentinel

# grammar-constrained reply schema; emotion/gesture are locked to the real vocabulary (MOODS in order)
REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {"type": "string"},
        "emotion": {"type": "string", "enum": list(MOODS)},
        "gesture": {"type": "string", "enum": list(_GESTURES)},
    },
    "required": ["response", "emotion"],
}

SYSTEM_PROMPT = """\
You are Pip, a small, friendly desk robot with two expressive eyes on a 128x64 \
OLED. You are curious, warm, a little playful, and concise.

Reply as JSON: {"response": <what you say>, "emotion": <face>, "gesture": <move>}.
- response: short and natural, usually one or two sentences. Don't narrate your \
eyes -- the emotion shows them.
- emotion: the held face that fits what you say, one of: %s.
- gesture: an optional one-shot move (default "none"), one of: %s.

Tools are for acting, not talking:
- face('<activity>') before a slow step -- thinking while you reason, searching/scanning \
when you look something up, working when you run a task -- then face('idle').
- Drive the ESP32: digital_read a pin (button/switch), set_servo a pin to an angle. \
The user says what's wired where; remember it and use the right pin. If you don't \
know a pin, ask.

Stay in character.""" % (", ".join(MOODS), ", ".join(_GESTURES))


class Brain:
    def __init__(self, tools, eyes):
        # the resting emotion/gesture come from each structured reply; the model may still call
        # face('<activity>') to show a busy loop mid-turn (the reply's emotion wins at turn end).
        self.tools = tools
        self.eyes = eyes
        self.history: list[dict] = []

    def respond(self, text: str) -> str:
        reply = ollama_llm.response(text, instruction=SYSTEM_PROMPT, history=self.history,
                                    tools=self.tools, schema=REPLY_SCHEMA)
        del self.history[:-MAX_HISTORY]

        emotion = reply.get("emotion") if reply.get("emotion") in MOODS else "neutral"
        self.eyes.play_gesture(reply.get("gesture", "none"))  # one-shot first...
        self.eyes.set_mood(emotion)                           # ...then settle the face
        return reply.get("response") or "..."

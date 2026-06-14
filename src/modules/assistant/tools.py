"""Robot capabilities as plain functions, shared by the Ollama brain and the MCP
server. Each takes simple args so any caller (a model, or Claude Code) can drive
the face and any ESP32 pin autonomously."""
from __future__ import annotations


def build_tools(eyes, bridge=None):
    """Return the tool functions bound to this robot's eyes and ESP32 bridge.

    Pin tools are only included when a bridge is connected.
    """

    def set_face(emotion: str, gesture: str = "none") -> str:
        """Set the robot's face: a held emotion, plus an optional one-shot gesture.

        emotion: the sustained expression the face holds until you change it --
            neutral, happy, sad, angry, tired, sleepy, surprised, lovely,
            skeptical, focused, dumb, confused, bored, scared, dead, alert,
            furious, worried, despair, disoriented, attentive, standby, or smoking.
        gesture: a momentary animation that plays once, then the emotion resumes --
            none, blink, double_blink, blink_up, blink_down, wink, wink_left,
            wink_right, nod, refuse, laugh, excited, roll, shiver, cross_eyes,
            pop, squint, scan, look_left, look_right, look_up, look_down,
            acknowledge, boot_up, power_down, or scan_sweep.
        """
        eyes.set_mood(emotion)
        eyes.play_gesture(gesture)  # no-op on "none"
        return f"face: {emotion}/{gesture}"

    def set_activity(activity: str) -> str:
        """Show what the robot is busy doing; the animation loops until changed.

        activity: thinking (figuring something out), scanning (reading text),
            searching (looking things up), working (running a task), processing
            (computing), connecting (establishing a link), listening, or idle to
            stop. Set it before a slow step, idle when done. Each busy activity
            also puts on a fitting face, so no need to set one too.
        """
        eyes.set_activity(activity)
        return f"activity: {activity}"

    def notify(reason: str = "") -> str:
        """Grab the human's attention: Pip turns to face you and pulses an alert.

        Call when you need the user to look over -- a question to answer, input or
        a permission to grant, a long task finished, or a snag worth a glance.
        Standard across MCP clients (Claude, Gemini, Codex, Cursor, Copilot): one
        plain string in, a plain string back.

        reason: optional short note on why you're pinging (shown in the log only).
        """
        eyes.set_mood("alert")
        eyes.play_gesture("scan_sweep")  # sweep around, looking for you
        return f"notify: {reason or 'attention'}"

    tools = [set_face, set_activity, notify]
    if bridge is None:
        return tools

    def digital_read(pin: int) -> str:
        """Read a digital input pin with an internal pull-up (button, switch)."""
        bridge.gpio.mode(pin, "input_pullup")
        return f"pin {pin} = {bridge.gpio.read(pin)}"

    def set_servo(pin: int, angle: int) -> str:
        """Move a servo on a pin to an angle from 0 to 180 degrees."""
        angle = max(0, min(180, angle))
        bridge.pwm.servo(pin, angle)
        return f"servo {pin} -> {angle} deg"

    return tools + [digital_read, set_servo]
"""Robot capabilities as plain functions, shared by the Ollama brain and the MCP
server. Each takes simple args so any caller (a model, or Claude Code) can drive
the face and any ESP32 pin autonomously."""
from __future__ import annotations


def build_tools(eyes, mgr=None):
    """Return the tool functions bound to this robot's eyes and ESP32 bridge.

    `mgr` is a self-healing BridgeManager (or None for face-only). Pin tools fetch
    the live bridge via `mgr.bridge()` each call, so they survive a BLE reconnect.
    """

    def set_face(emotion: str, gesture: str = "none") -> str:
        """Set the robot's face: a held emotion, plus an optional one-shot gesture.

        Use this for how Pip *feels*. For what Pip is *doing* (an ongoing task),
        use set_activity instead.

        emotion: the sustained expression the face holds until you change it.
            calm/positive: neutral, happy, lovely, kawaii, awe, cool, focused,
                zen (in flow), wired (caffeinated), chill (mellow), attentive;
            sad/anxious:    sad, gloomy, worried, nervous, despair, scared,
                tired, sleepy;
            angry/wary:     angry, furious, devil, suspicious, skeptical;
            dazed/off:      surprised, dumb, confused, disoriented, bored, dead;
            system:         alert (attention), standby (low-power sleep).
        gesture: a momentary animation that plays once over the face, then the
            emotion resumes.
            blinks:  blink, double_blink, blink_up, blink_down, wink, wink_left,
                wink_right;
            gaze:    look_left, look_right, look_up, look_down, scan, scan_sweep;
            react:   nod, refuse, acknowledge, laugh, excited, roll, shiver,
                cross_eyes, pop, squint.
            (default none plays nothing.)
        """
        eyes.set_mood(emotion)
        eyes.play_gesture(gesture)  # no-op on "none"
        return f"face: {emotion}/{gesture}"

    def set_activity(activity: str) -> str:
        """Show what the robot is busy doing; the animation loops until changed.

        activity: thinking (figuring something out), scanning (reading text),
            searching (looking things up), processing (computing), working
            (running a task), editing (writing code), debugging (hunting a bug),
            building (compiling/assembling), testing (running tests), deploying
            (shipping/launching), connecting (establishing a link), listening,
            waiting (idle for input/output), smoking (a chilled break),
            glitch (a crash/corruption fit -- datamosh, scanlines, ghosting,
            code-rain, invert flashes; good for an error/exception), or idle to
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
    if mgr is None:
        return tools

    def digital_read(pin: int) -> str:
        """Read a digital input pin with an internal pull-up (button, switch)."""
        bridge = mgr.bridge()
        bridge.gpio.mode(pin, "input_pullup")
        return f"pin {pin} = {bridge.gpio.read(pin)}"

    def set_servo(pin: int, angle: int) -> str:
        """Move a servo on a pin to an angle from 0 to 180 degrees."""
        angle = max(0, min(180, angle))
        mgr.bridge().pwm.servo(pin, angle)
        return f"servo {pin} -> {angle} deg"

    return tools + [digital_read, set_servo]

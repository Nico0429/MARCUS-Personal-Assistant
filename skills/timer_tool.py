import asyncio
import pygame
from event_engine import bus
from voice import say, global_face
from plyer import notification  # Run 'pip install plyer' in your environment

class TimerSkill:
    def __init__(self, brain):
        self.brain = brain
        self.active_timer_task = None
        self.timer_paused = False
        self.current_task_name = ""
        self._seconds_left = 0  # Track countdown state natively
        
        # --- Listen to the UI Buttons ---
        bus.subscribe("timer_manual_action", self._on_manual_action)

    def _on_manual_action(self, data):
        """Bridge UI button clicks to background logic."""
        action = data.get("action")
        if action == "pause":
            asyncio.create_task(self.toggle_pause(is_voice=False))
        elif action == "stop":
            asyncio.create_task(self.stop_timer_protocol(ui_triggered=True))

    async def toggle_pause(self, is_voice=True):
        """Logic for pausing or resuming the timer (Voice/Terminal/UI)."""
        if self.active_timer_task and not self.active_timer_task.done():
            self.timer_paused = not self.timer_paused
            state = "paused" if self.timer_paused else "resumed"
            print(f"[ TimerSkill ] Timer {state} via {'Voice/Terminal' if is_voice else 'UI'}.")
            
            # Speak only if requested via voice/terminal to avoid annoying click spam
            if is_voice:
                await say(f"Timer {state}, Sir.")
            return True
        return False

    async def skip_timer(self):
        """Fast-forwards the countdown to zero, naturally triggering completion."""
        if self.active_timer_task and not self.active_timer_task.done():
            print("[ TimerSkill ] Skipping remaining time.")
            self._seconds_left = 0
            self.timer_paused = False
            return True
        return False

    async def modify_time(self, minutes):
        """Allows you to go back or add time (e.g., 'add 5 minutes' or 'go back 2 minutes')."""
        if self.active_timer_task and not self.active_timer_task.done():
            adjustment = int(minutes * 60)
            self._seconds_left = max(0, self._seconds_left + adjustment)
            direction = "Extended" if minutes > 0 else "Reduced"
            await say(f"Timer {direction} by {abs(int(minutes))} minutes, Sir.")
            return True
        return False

    async def execute_timer_protocol(self, mins, task_name):
        print(f"[ TimerSkill: Initializing {mins}m for {task_name}... ]")
        self.current_task_name = task_name
        
        if self.active_timer_task and not self.active_timer_task.done():
            self.active_timer_task.cancel()
            
        self.timer_paused = False
        self._seconds_left = int(float(mins) * 60)
        self.active_timer_task = asyncio.create_task(self._run_countdown(mins, task_name))
        
        msg = f"Timer initialized for {int(mins)} minutes. Focus on {task_name}, Sir."
        global_face.set_thinking(False)
        await say(msg)
        return True

    async def stop_timer_protocol(self, ui_triggered=False):
        if self.active_timer_task and not self.active_timer_task.done():
            self.active_timer_task.cancel() 
            print(f"[ TimerSkill ] Timer cancelled via {'UI' if ui_triggered else 'Voice/Terminal'}.")
            
            if ui_triggered:
                # Direct confirmation to HUD/Terminal to avoid verbal interruption
                await bus.emit("user_spoken_text", f"\n[ System ] Timer for '{self.current_task_name}' manually terminated.")
            else:
                await say("Timer aborted.")
            return True
        return False

    async def _run_countdown(self, minutes, task_name):
        # INITIAL SHOW
        await bus.emit("timer_ui_control", {"action": "show", "task": task_name, "time_str": f"{int(minutes):02d}:00"})
        
        try:
            while self._seconds_left > 0:
                if self.timer_paused:
                    await asyncio.sleep(0.5)
                    continue
                
                mins, secs = divmod(self._seconds_left, 60)
                time_str = f"{mins:02d}:{secs:02d}"
                await bus.emit("timer_ui_control", {"action": "update", "time_str": time_str})
                await asyncio.sleep(1)
                self._seconds_left -= 1
                
            await bus.emit("timer_ui_control", {"action": "hide"})
            
            # --- Windows OS Push Notification (Bypasses Mute/Audio Engine) ---
            try:
                notification.notify(
                    title="M.A.R.C.U.S. | Protocol Concluded",
                    message=f"Deep work focus session for '{task_name}' complete.",
                    app_name="MARCUS",
                    timeout=10
                )
            except Exception as e:
                print(f"[ Notification Error ] {e}")
                
            await say(f"Sir, your designated time for {task_name} has concluded.")
            
        except asyncio.CancelledError:
            await bus.emit("timer_ui_control", {"action": "hide"})
            raise
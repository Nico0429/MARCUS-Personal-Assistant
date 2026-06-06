"""
================================================================================
FILE: system_events.py
ROLE: The System Event Bridge (Controller)
================================================================================
This script acts as the central nervous system connecting background workers 
(daemons, audio streams) to the front-end Qt UI components. 

By subscribing to the thread-safe EventBus, this Controller listens for 
broadcasted signals (like 'wake_word_detected' or 'ui_window_control') and 
triggers the appropriate UI animations, audio mutes, or window state changes, 
keeping the UI loosely coupled from the backend logic.
================================================================================
"""



import asyncio
import pygame
from qasync import asyncSlot
from event_engine import bus
from skills import directory_watchdog
from voice import engine
from config.triggers import EXIT_PHRASES

class SystemEventBridge:
    """The Central Nervous System for Marcus. Routes all Event Bus traffic."""
    def __init__(self, brain, face, briefing, terminal_window, brain_window, marcus_daemon, shutdown_callback):
        self.brain = brain
        self.face = face
        self.briefing = briefing
        self.terminal_window = terminal_window
        self.brain_window = brain_window
        self.marcus_daemon = marcus_daemon
        self.shutdown_callback = shutdown_callback
        self.directory_watchdog = directory_watchdog
        
        self._register_events()

    def _register_events(self):
        bus.subscribe("ui_window_control", self.on_ui_window_control)
        bus.subscribe("refresh_brain_graph", self.on_graph_refresh)
        bus.subscribe("timer_manual_action", self.on_timer_manual_action)
        bus.subscribe("wake_word_detected", self.on_wake)
        bus.subscribe("mute_marcus_requested", self.on_mute_requested)
        bus.subscribe("system_shutdown_requested", self.on_shutdown)
        bus.subscribe("manual_text_entered", self.on_manual_text)
        bus.subscribe("trigger_watchdog_rebuild", self.on_watchdog_rebuild)

    @asyncSlot(dict)
    async def on_ui_window_control(self, data):
        target, action = data.get("target"), data.get("action")
        if target == "matrix":
            if action == "open": 
                self.brain_window.refresh_graph()
                self.brain_window.reveal() 
            else: 
                self.brain_window.conceal() 
        elif target == "terminal":
            if action == "open":
                if self.terminal_window.is_folded: self.terminal_window.toggle_fold()
                self.terminal_window.show()
                self.terminal_window.raise_()
            else:
                if not self.terminal_window.is_folded: self.terminal_window.toggle_fold()

    @asyncSlot(object)
    async def on_graph_refresh(self, _):
        if self.brain_window.isVisible(): 
            self.brain_window.refresh_graph()

    @asyncSlot(dict)
    async def on_timer_manual_action(self, data):
        action = data.get("action")
        if action == "pause":
            self.brain.timer_paused = not getattr(self.brain, 'timer_paused', False)
        elif action == "stop":
            if getattr(self.brain, 'active_timer_task', None) and not self.brain.active_timer_task.done():
                self.brain.active_timer_task.cancel()

    async def on_wake(self, data):
        if getattr(self.face, 'is_recording', False): return
        print("\n[ Wake Word Detected! Pulling Tripwire... ]")
        self.brain.interrupt_event.set()
        self.face.stop_toggle = True 
        try: engine.stop() 
        except: pass
        try:
            if pygame.mixer.get_init(): pygame.mixer.stop()
        except: pass
        self.face.set_listening(False)
        self.face.set_thinking(False)
        await asyncio.sleep(0.4) 
        self.face.trigger_toggle = True

    async def on_mute_requested(self, state):
        self.face.is_muted = state 
        if state:
            self.face.stop_toggle = True
            try: engine.stop()
            except: pass
            try:
                if pygame.mixer.get_init(): pygame.mixer.stop()
            except: pass
            self.face.set_thinking(False)
            self.face.set_listening(False)

    @asyncSlot(object)
    async def on_shutdown(self, _):
        print("[ System ] Lowering reactor rods... preparing for shutdown.")
        
        # 1. Kill backend processes
        self.marcus_daemon.running = False
        self.terminal_window.active_stream_id = -1 
        
        # 2. Instantly hand over visual control to main.py's cinematic teardown sequence
        self.shutdown_callback()

    async def on_manual_text(self, text):
        print(f"\n[ Text Input Received ]: {text}")
        self.brain.interrupt_event.set() 
        try: engine.stop() 
        except: pass
        await bus.emit("user_spoken_text", text)
        if any(phrase in text.lower() for phrase in EXIT_PHRASES):
            await self.briefing._enter_sleep_mode()
            return
        self.face.set_thinking(True)
        await self.brain.chat_async(text.lower())
        self.face.set_thinking(False)

    async def on_watchdog_rebuild(self, _):
        import asyncio
        loop = asyncio.get_running_loop()
        self.directory_watchdog.wipe_state()
        await loop.run_in_executor(None, self.directory_watchdog.boot_sync)
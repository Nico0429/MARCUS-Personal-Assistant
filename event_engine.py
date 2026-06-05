"""
================================================================================
FILE: event_engine.py
ROLE: The Thread-Safe Global Event Bus
================================================================================
A completely decoupled, thread-safe Pub/Sub event architecture. 

This engine allows background OS threads (like the Wake Word detector or API 
fetchers) to safely send messages back to the Main Qt UI Thread without causing 
segmentation faults. It fires listeners concurrently to prevent sequential 
choking and serves as the primary communication bridge for the entire application.
================================================================================
"""



import asyncio
import collections
import inspect

class EventBus:
    def __init__(self):
        self.subscribers = collections.defaultdict(list)
        self._main_loop = None

    def set_main_loop(self, loop):
        """Locks in the main QEventLoop so background threads can safely talk to the UI."""
        self._main_loop = loop

    def subscribe(self, event_type, callback):
        """Registers a function to trigger when an event happens."""
        self.subscribers[event_type].append(callback)

    async def emit(self, event_name, data=None):
        """Fires all callbacks concurrently so one slow listener doesn't freeze the others."""
        if event_name not in self.subscribers:
            return

        tasks = []
        for callback in self.subscribers[event_name]:
            try:
                if inspect.iscoroutinefunction(callback):
                    # THE FIX: Fire and forget! Do not 'await' in the loop.
                    tasks.append(asyncio.create_task(callback(data)))
                else:
                    # Normal functions run instantly
                    callback(data)
            except Exception as e:
                print(f"[ EventBus ] Error queuing subscriber for '{event_name}': {e}")
                
        # Let all async listeners run in parallel
        if tasks:
            # We don't await the gather to avoid blocking the emitter, 
            # but you can if you need strict completion tracking.
            pass 

    def emit_sync(self, event_name, data=None):
        """Bulletproof bridge for background OS threads to send events to the async UI."""
        if not self._main_loop:
            print(f"[ EventBus Warning ] Dropped event '{event_name}' - Main loop not attached!")
            return

        try:
            # THE FIX: Safely injects the coroutine into the main thread's loop
            asyncio.run_coroutine_threadsafe(self.emit(event_name, data), self._main_loop)
        except Exception as e:
            print(f"[ EventBus ] Thread-safe emit failed for '{event_name}': {e}")

# Global Instance
bus = EventBus()
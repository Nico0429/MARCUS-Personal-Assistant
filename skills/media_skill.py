import asyncio
import threading
from event_engine import bus
from voice import say, global_face
import winrt.windows.media.control as wmc
import winrt.system

# ==========================================
# 1. PERSISTENT WINRT MEDIA ENGINE
# ==========================================
class WinRTMediaEngine:
    """A persistent, dedicated MTA thread to keep Windows COM alive and happy without deadlocking Qt."""
    _loop = None
    _thread = None

    @classmethod
    def boot(cls):
        if cls._thread is not None:
            return
        
        ready_event = threading.Event()
        
        def _engine_runner():
            # Initialize MTA state safely and permanently for this thread
            try: winrt.system.init_apartment(winrt.system.Multithreaded)
            except Exception: pass
            
            cls._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls._loop)
            ready_event.set()
            cls._loop.run_forever()

        # Daemon thread: it will automatically close when Marcus shuts down
        cls._thread = threading.Thread(target=_engine_runner, daemon=True, name="WinRT_Media_Thread")
        cls._thread.start()
        ready_event.wait()

    @classmethod
    async def execute(cls, coro):
        """Dispatches an async task to the persistent WinRT thread and waits for the result."""
        if cls._loop is None:
            cls.boot()
            
        future = asyncio.run_coroutine_threadsafe(coro, cls._loop)
        try:
            # Wrap the cross-thread future and apply the Kill Switch timeout
            return await asyncio.wait_for(asyncio.wrap_future(future), timeout=1.5)
        except asyncio.TimeoutError:
            print("[ MediaSkill ] WinRT sync timeout. Application may be booting.")
            return None
        except Exception as e:
            print(f"[ MediaSkill ] WinRT Engine Error: {e}")
            return None

# ==========================================
# 2. ISOLATED ASYNC TASKS
# ==========================================
async def _async_media_action(action):
    """Executes a playback control. Runs inside the persistent WinRT thread."""
    manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
    for s in manager.get_sessions():
        app_id = s.source_app_user_model_id.lower()
        if "applemusic" in app_id or ("apple" in app_id and "music" in app_id):
            if action == "playpause": await s.try_toggle_play_pause_async()
            elif action == "next": await s.try_skip_next_async()
            elif action == "prev": await s.try_skip_previous_async()
            return True
    return False

async def _async_get_now_playing():
    """Fetches track info safely. Runs inside the persistent WinRT thread."""
    manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
    for s in manager.get_sessions():
        app_id = s.source_app_user_model_id.lower()
        if "applemusic" in app_id or ("apple" in app_id and "music" in app_id):
            info = await s.try_get_media_properties_async()
            pb = s.get_playback_info()
            return {
                "title": info.title if info.title else "Unknown Track",
                "artist": info.artist if info.artist else "Unknown Artist",
                "is_playing": (pb.playback_status == wmc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING)
            }
    return None

# ==========================================
# 3. MEDIA SKILL CONTROLLER
# ==========================================
class MediaSkill:
    def __init__(self, brain):
        self.brain = brain
        self.ui_visible = False
        self.current_track_name = None
        self.poll_task = None
        
        # Pre-boot the persistent thread when Marcus starts
        WinRTMediaEngine.boot()
        
        bus.subscribe("media_manual_action", self._on_manual_action)

    async def _poll_media(self):
        """Silently checks Apple Music for track changes while the UI is open."""
        while self.ui_visible:
            # Toss the request to the dedicated thread safely
            track_info = await WinRTMediaEngine.execute(_async_get_now_playing())
            
            if track_info and track_info != self.current_track_name:
                self.current_track_name = track_info
                await bus.emit("media_ui_control", {"action": "update", "track": track_info})
                
            await asyncio.sleep(2)

    async def _on_manual_action(self, data):
        """Handles physical button clicks from your UI Media Player."""
        action = data.get("action")
        
        if action == "close_ui":
            self.ui_visible = False 
            await bus.emit("media_ui_control", {"action": "hide"})
            return

        await WinRTMediaEngine.execute(_async_media_action(action))

    async def execute_media_command(self, command_type, target=None):
        """Handles spoken commands from the ML Router."""
        msg = "Adjusting Apple Music."
        
        if command_type == "hide":
            self.ui_visible = False
            await bus.emit("media_ui_control", {"action": "hide"})
            global_face.set_thinking(False)
            await say("Hiding the media interface.")
            return True
            
        elif command_type == "show":
            msg = "Bringing up Apple Music controls."

        else:
            action_map = {
                "play": "playpause", "pause": "playpause", "resume": "playpause", "stop": "playpause",
                "next": "next", "skip": "next",
                "prev": "prev", "previous": "prev", "back": "prev"
            }
            if command_type in action_map:
                success = await WinRTMediaEngine.execute(_async_media_action(action_map[command_type]))
                if not success:
                    msg = "Sir, Apple Music does not appear to be running."

        # Grab initial track data
        raw_track = await WinRTMediaEngine.execute(_async_get_now_playing())
        
        self.current_track_name = raw_track if raw_track else {
            "title": "[ WAITING FOR OS ]", 
            "artist": "Syncing Media...", 
            "is_playing": False
        }
        
        await bus.emit("media_ui_control", {"action": "show", "track": self.current_track_name})
        
        self.ui_visible = True
        if not self.poll_task or self.poll_task.done():
            self.poll_task = asyncio.create_task(self._poll_media())
        
        global_face.set_thinking(False)
        await say(msg)
        return True